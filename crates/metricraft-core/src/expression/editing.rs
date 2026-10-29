//! Occurrence-based edits: clone handles on the ancestor path, never whole trees.
use super::{templates::Template, BuildOptions, Expr, Extra, Kind, Mode, Result};
use std::sync::Arc;

impl Expr {
    pub fn node_kind(&self) -> &'static str {
        super::diagnostics::name(&self.0.kind)
    }

    pub fn value_type(&self) -> &'static str {
        match self.0.ty {
            super::Type::Scalar => "scalar",
            super::Type::String => "string",
            super::Type::Instant => "instant",
            super::Type::Range => "range",
            super::Type::Tuple => "tuple",
        }
    }

    /// Ordered expression children, sharing their existing Arc allocations.
    /// Selectors and literals are leaves. Metadata (labels/durations) is not a child.
    /// WITH children are binding values in declaration order, followed by its body.
    pub fn children(&self) -> Vec<Self> {
        match &self.0.kind {
            Kind::Template(t) => t.children().into_iter().cloned().collect(),
            Kind::Extra(e) => e.children().into_iter().cloned().collect(),
            Kind::Call(_, c) | Kind::Aggregate(_, c, ..) | Kind::Tuple(c) => c.clone(),
            Kind::Binary(b) => vec![b.lhs.clone(), b.rhs.clone()],
            Kind::Range(c, _)
            | Kind::Unary(_, c)
            | Kind::Parenthesized(c)
            | Kind::KeepNames(c)
            | Kind::Subquery(c, ..)
            | Kind::Offset(c, _)
            | Kind::At(c, _) => vec![c.clone()],
            _ => Vec::new(),
        }
    }

    /// Read one occurrence. An empty path returns this expression's shared handle.
    pub fn at_path(&self, path: &[usize]) -> Result<Self> {
        if path.len() > 1024 {
            return Err("AST path exceeds 1024 steps".into());
        }
        let mut node = self.clone();
        for &index in path {
            node = node
                .children()
                .get(index)
                .ok_or("AST child index out of range")?
                .clone();
        }
        Ok(node)
    }

    /// Pointer identity, useful for checking persistent sharing (not semantic equality).
    pub fn shares_node(&self, other: &Self) -> bool {
        Arc::ptr_eq(&self.0, &other.0)
    }

    /// Replace exactly one occurrence and validate the resulting root in `mode`.
    /// Non-root replacements preserve value type. No-op edits retain root identity.
    /// Construction rechecks ancestors; final rendering rechecks scopes and dialect.
    pub fn replace_at(
        &self,
        path: &[usize],
        replacement: &Self,
        mode: Mode,
        options: BuildOptions,
    ) -> Result<Self> {
        if path.len() > 1024 {
            return Err("AST path exceeds 1024 steps".into());
        }
        let mut parents = Vec::with_capacity(path.len());
        let mut current = self.clone();
        for &index in path {
            let child = current
                .children()
                .get(index)
                .ok_or("AST child index out of range")?
                .clone();
            parents.push((current, index));
            current = child;
        }
        if !path.is_empty() && current.0.ty != replacement.0.ty {
            return Err("replacement must preserve the selected node's value type".into());
        }
        let mut result = replacement.clone();
        if current.shares_node(replacement) {
            result = self.clone();
        } else {
            for (parent, index) in parents.into_iter().rev() {
                result = parent.rebuild_child(index, result)?;
            }
        }
        result.build_with_options(mode, options)?;
        Ok(result)
    }

    fn rebuild_child(&self, index: usize, replacement: Self) -> Result<Self> {
        let mut children = self.children();
        *children
            .get_mut(index)
            .ok_or("AST child index out of range")? = replacement;
        let apply = |op, a, b| Self::apply(op, a, b, &children);
        let unary = |op, a, b| Self::apply(op, a, b, &children[..1]);
        match &self.0.kind {
            // The portable constructor stores VM's argument order internally,
            // with no VM-only requirement. Revalidate through that constructor.
            Kind::Call(name, _)
                if name == "histogram_quantiles" && self.0.required_mode.is_none() =>
            {
                apply("histogram_quantiles_auto", "", "")
            }
            Kind::Call(name, _) => apply("call", name, ""),
            Kind::Tuple(_) => apply("tuple", "", ""),
            Kind::Aggregate(name, _, grouping, without) => {
                let mut expr = apply(name, "", "")?;
                if let Some(labels) = grouping {
                    let mut args = vec![expr];
                    for label in labels {
                        args.push(Self::apply("string", label, "", &[])?);
                    }
                    expr = Self::apply(if *without { "without" } else { "by" }, "", "", &args)?;
                }
                Ok(expr)
            }
            Kind::Binary(binary) => {
                let mut expr = apply(&binary.op, "", "")?;
                if binary.return_bool {
                    expr = Self::apply("bool", "", "", &[expr])?;
                }
                for (name, labels) in [binary.matching.as_deref(), binary.grouping.as_deref()]
                    .into_iter()
                    .flatten()
                {
                    let all = name.starts_with("group_")
                        && binary.extra.as_ref().is_some_and(|e| e.copy_all);
                    let mut args = vec![expr];
                    if !all {
                        for label in labels {
                            args.push(Self::apply("string", label, "", &[])?);
                        }
                    }
                    let op = if all {
                        format!("{name}_all")
                    } else {
                        name.clone()
                    };
                    let prefix = binary
                        .extra
                        .as_ref()
                        .and_then(|e| e.prefix.as_deref())
                        .unwrap_or("");
                    expr = Self::apply(&op, prefix, "", &args)?;
                }
                if let Some(extra) = &binary.extra {
                    for (op, value) in [
                        ("fill_left", extra.fill_left),
                        ("fill_right", extra.fill_right),
                    ] {
                        if let Some(value) = value {
                            expr = Self::apply(
                                op,
                                "",
                                "",
                                &[expr, Self::apply("number", &value.to_string(), "", &[])?],
                            )?;
                        }
                    }
                }
                Ok(expr)
            }
            Kind::Range(_, window) => unary("range", window, ""),
            Kind::Subquery(_, window, step) => unary("subquery", window, step),
            Kind::Offset(_, offset) => unary("offset", offset, ""),
            Kind::At(_, time) => unary("at", time.strip_suffix("()").unwrap_or(time), ""),
            Kind::Parenthesized(_) => unary("parenthesize", "", ""),
            Kind::Unary(sign, _) => unary(if sign == "-" { "negate" } else { "positive" }, "", ""),
            Kind::KeepNames(_) => unary("keep_metric_names", "", ""),
            Kind::Extra(extra) => match extra {
                Extra::Selectors(..) => apply("selector_or", "", ""),
                Extra::Matcher(_, label, op, ..) => apply("match_expr", label, op),
                Extra::Range(..) => apply("range_expr", "", ""),
                Extra::Subquery(..) => apply("subquery_expr", "", ""),
                Extra::Offset(..) => apply("offset_expr", "", ""),
                Extra::At(..) => apply("at_expr", "", ""),
                Extra::Suffix(_, name) => unary(name, "", ""),
                Extra::Limit(_, limit) => Self::apply(
                    "aggregate_limit",
                    "",
                    "",
                    &[
                        children[0].clone(),
                        Self::apply("number", &limit.to_string(), "", &[])?,
                    ],
                ),
            },
            Kind::Template(template) => match template {
                Template::Reference(name, _, called) => apply(
                    if *called {
                        "template_call"
                    } else {
                        "reference"
                    },
                    name,
                    self.value_type(),
                ),
                Template::Definition(parameters, _) => {
                    let mut args = Vec::new();
                    for name in parameters {
                        args.push(Self::apply("string", name, "", &[])?);
                    }
                    args.push(children[0].clone());
                    Self::apply("template", "", "", &args)
                }
                Template::With(bindings, _) => {
                    let mut args = vec![children.last().unwrap().clone()];
                    for ((name, _), value) in bindings.iter().zip(&children) {
                        args.push(Self::apply("string", name, "", &[])?);
                        args.push(value.clone());
                    }
                    Self::apply("with", "", "", &args)
                }
            },
            _ => Err("leaf nodes have no expression children".into()),
        }
    }
}
