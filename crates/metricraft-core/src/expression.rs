//! Immutable PromQL/MetricsQL expressions. No transport, handles or Python state.
use std::{
    fmt::{self, Write},
    sync::Arc,
};
mod aggregation;
mod diagnostics;
mod functions;
mod literals;
mod operators;
mod render;
mod selector;
mod syntax;
mod templates;
pub use render::{BuildLimits, BuildOptions, Complexity};
use selector::Selector;
use syntax::Extra;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Mode {
    PromQl,
    MetricsQl,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Type {
    Scalar,
    String,
    Instant,
    Range,
    Tuple,
}
#[derive(Clone)]
pub struct Expr(Arc<Node>);
#[derive(Debug)]
struct Node {
    kind: Kind,
    ty: Type,
    required_mode: Option<Mode>,
    complexity: Complexity,
}
#[derive(Debug)]
enum Kind {
    Selector(Selector),
    Number(f64),
    String(String),
    Tuple(Vec<Expr>),
    Extra(Extra),
    Template(templates::Template),
    Range(Expr, String),
    Call(String, Vec<Expr>),
    Aggregate(String, Vec<Expr>, Option<Vec<String>>, bool),
    Binary(Binary),
    Unary(String, Expr),
    Parenthesized(Expr),
    KeepNames(Expr),
    Subquery(Expr, String, String),
    Offset(Expr, String),
    At(Expr, String),
}

#[derive(Clone, Debug)]
struct Binary {
    op: String,
    lhs: Expr,
    rhs: Expr,
    return_bool: bool,
    matching: Option<Arc<(String, Vec<String>)>>,
    grouping: Option<Arc<(String, Vec<String>)>>,
    extra: Option<Arc<BinaryExtra>>,
}
#[derive(Clone, Debug, Default)]
struct BinaryExtra {
    copy_all: bool,
    prefix: Option<String>,
    fill_left: Option<f64>,
    fill_right: Option<f64>,
}
fn comparison(op: &str) -> bool {
    matches!(op, "==" | "!=" | ">" | "<" | ">=" | "<=")
}
fn set_operator(op: &str) -> bool {
    matches!(op, "and" | "or" | "unless")
}

fn labels(args: &[Expr]) -> Result<Vec<String>> {
    let mut result = Vec::new();
    for arg in args {
        let Kind::String(label) = &arg.0.kind else {
            return Err("label must be a string literal".into());
        };
        if !valid_name(label) || result.contains(label) {
            return Err("invalid or duplicate label".into());
        }
        result.push(label.clone());
    }
    Ok(result)
}
type Result<T> = std::result::Result<T, String>;

fn valid_name(s: &str) -> bool {
    !s.is_empty() && !s.chars().any(char::is_control)
}

fn identifier(s: &str, metric: bool) -> bool {
    if metric
        && (matches!(s, "bool" | "on" | "ignoring" | "group_left" | "group_right")
            || ["with", "inf", "nan"]
                .iter()
                .any(|word| s.eq_ignore_ascii_case(word)))
    {
        return false;
    }
    let mut chars = s.chars();
    let start = |c: char| c.is_ascii_alphabetic() || c == '_' || (metric && c == ':');
    chars.next().is_some_and(start) && chars.all(|c| start(c) || c.is_ascii_digit())
}
fn classic_duration(s: &str) -> bool {
    let bytes = s.as_bytes();
    let mut i = 0;
    let mut previous = 8;
    let mut positive = false;
    while i < bytes.len() {
        let begin = i;
        while i < bytes.len() && bytes[i].is_ascii_digit() {
            positive |= bytes[i] != b'0';
            i += 1;
        }
        if begin == i || i == bytes.len() {
            return false;
        }
        let rank = match bytes[i] {
            b'y' => 7,
            b'w' => 6,
            b'd' => 5,
            b'h' => 4,
            b'm' if bytes.get(i + 1) == Some(&b's') => {
                i += 1;
                1
            }
            b'm' => 3,
            b's' => 2,
            _ => return false,
        };
        if rank >= previous {
            return false;
        }
        previous = rank;
        i += 1;
    }
    positive
}
fn quote(s: &str, out: &mut String) {
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if c.is_control() => {
                write!(out, "\\u{:04x}", c as u32).unwrap();
            }
            c => out.push(c),
        }
    }
    out.push('"');
}

fn quote_len(s: &str) -> usize {
    s.chars().fold(2usize, |n, c| {
        n.saturating_add(match c {
            '"' | '\\' | '\n' | '\r' | '\t' => 2,
            c if c.is_control() => 6,
            c => c.len_utf8(),
        })
    })
}
impl Expr {
    fn new(kind: Kind, ty: Type, required_mode: Option<Mode>) -> Self {
        let complexity = render::complexity(&kind);
        Self(Arc::new(Node {
            complexity,
            kind,
            ty,
            required_mode,
        }))
    }
    /// Validated operation boundary shared by native language bindings.
    /// `a` and `b` are data fields, never raw query fragments.
    pub fn apply(op: &str, a: &str, b: &str, args: &[Expr]) -> Result<Self> {
        let arity = |n| {
            if args.len() == n {
                Ok(())
            } else {
                Err(format!("{op} expects {n} expressions"))
            }
        };
        match op {
            "histogram_quantiles_auto" => {
                if !args.first().is_some_and(|arg| arg.0.ty == Type::String) {
                    return Err("histogram_quantiles requires a label first".into());
                }
                functions::variadic::quantiles("histogram_quantiles", args)?;
                let common = args.len() <= 12
                    && args.last().is_some_and(|a| a.0.ty == Type::Instant)
                    && args[1..args.len() - 1]
                        .iter()
                        .all(|a| a.0.ty == Type::Scalar);
                Ok(Self::new(
                    Kind::Call("histogram_quantiles".into(), args.to_vec()),
                    Type::Instant,
                    if common { None } else { Some(Mode::MetricsQl) },
                ))
            }
            "match_expr" => syntax::matcher(a, b, args),
            "reference" | "template_call" | "template" | "with" => templates::apply(op, a, b, args),
            "duration_literal" if args.is_empty() => literals::duration_expr(a),
            "numeric_literal" if args.is_empty() => literals::numeric(a),
            "range_expr" | "subquery_expr" | "offset_expr" | "at_expr" | "anchored"
            | "selector_or" | "smoothed" | "aggregate_limit" => syntax::apply(op, args),
            "selector" => {
                if !args.len().is_multiple_of(2) {
                    return Err("from_labels requires label/value pairs".into());
                }
                let mut selector = Selector::new("");
                for pair in args.chunks_exact(2) {
                    let (Kind::String(label), Kind::String(value)) =
                        (&pair[0].0.kind, &pair[1].0.kind)
                    else {
                        return Err("selector labels and values must be strings".into());
                    };
                    if !valid_name(label) {
                        return Err("invalid label name".into());
                    }
                    selector = selector.with_matcher(label, "=", value)?;
                }
                Ok(Self::new(Kind::Selector(selector), Type::Instant, None))
            }
            "metric" => {
                arity(0)?;
                if !valid_name(a) {
                    return Err(format!("invalid metric name: {a:?}"));
                }
                Ok(Self::new(
                    Kind::Selector(Selector::new(a)),
                    Type::Instant,
                    None,
                ))
            }
            "number" => {
                arity(0)?;
                let n: f64 = a.parse().map_err(|_| "invalid number")?;
                Ok(Self::new(Kind::Number(n), Type::Scalar, None))
            }
            "string" => {
                arity(0)?;
                Ok(Self::new(Kind::String(a.into()), Type::String, None))
            }
            "tuple" => {
                if args.is_empty()
                    || !matches!(args[0].0.ty, Type::String | Type::Scalar)
                    || args.iter().any(|arg| arg.0.ty != args[0].0.ty)
                {
                    return Err(
                        "tuple requires nonempty, uniformly string or scalar expressions".into(),
                    );
                }
                Ok(Self::new(
                    Kind::Tuple(args.to_vec()),
                    Type::Tuple,
                    Some(Mode::MetricsQl),
                ))
            }
            "=" | "!=" | "=~" | "!~" if args.len() == 1 => {
                arity(1)?;
                if !valid_name(a) {
                    return Err("invalid label name".into());
                }
                if matches!(
                    args[0].0.kind,
                    Kind::Extra(Extra::Matcher(..) | Extra::Selectors(..))
                ) {
                    return syntax::matcher(
                        a,
                        op,
                        &[args[0].clone(), Self::apply("string", b, "", &[])?],
                    );
                }
                let Kind::Selector(selector) = &args[0].0.kind else {
                    return Err("matchers require a metric selector".into());
                };
                Ok(Self::new(
                    Kind::Selector(selector.with_matcher(a, op, b)?),
                    Type::Instant,
                    None,
                ))
            }
            "range" => {
                arity(1)?;
                let mut mode = literals::mode(a, false)?;
                if !matches!(args[0].0.ty, Type::Instant | Type::Scalar) {
                    return Err(
                        "range requires a metric selector; use subquery() for expressions".into(),
                    );
                }
                if !matches!(args[0].0.kind, Kind::Selector(_)) {
                    mode = Some(Mode::MetricsQl);
                }
                Ok(Self::new(
                    Kind::Range(args[0].clone(), a.into()),
                    Type::Range,
                    mode,
                ))
            }
            _ if aggregation::is_name(op) => aggregation::construct(op, args),
            "by" | "without" => {
                if args.is_empty() {
                    return Err("grouping requires an aggregation".into());
                }
                let Kind::Aggregate(name, child, grouping, _) = &args[0].0.kind else {
                    return Err("grouping requires an aggregation".into());
                };
                if grouping.is_some() {
                    return Err("aggregation already has grouping; derive by/without from the ungrouped expression".into());
                }
                let labels = labels(&args[1..])?;
                Ok(Self::new(
                    Kind::Aggregate(name.clone(), child.clone(), Some(labels), op == "without"),
                    Type::Instant,
                    args[0].0.required_mode,
                ))
            }
            _ if operators::is_name(op) => operators::apply(op, a, args),
            "subquery" => {
                arity(1)?;
                if !matches!(args[0].0.ty, Type::Instant | Type::Scalar) {
                    return Err("subquery requires an instant vector and positive durations".into());
                }
                let mode = (if a.is_empty() || args[0].0.ty == Type::Scalar {
                    if !a.is_empty() {
                        literals::mode(a, false)?;
                    }
                    Some(Mode::MetricsQl)
                } else {
                    literals::mode(a, false)?
                })
                .or(if b.is_empty() {
                    None
                } else {
                    literals::mode(b, false)?
                });
                Ok(Self::new(
                    Kind::Subquery(args[0].clone(), a.into(), b.into()),
                    Type::Range,
                    mode,
                ))
            }
            "offset" | "at" => {
                arity(1)?;
                if !matches!(args[0].0.ty, Type::Instant | Type::Range) {
                    return Err("time modifiers require a vector".into());
                }
                let mut mode = if args[0].time_target() {
                    None
                } else {
                    Some(Mode::MetricsQl)
                };
                if args[0].has_time_modifier(op) {
                    return Err(format!("{op} is already set"));
                }
                let kind = if op == "offset" {
                    mode = mode.or(literals::mode(a.strip_prefix('-').unwrap_or(a), true)?);
                    Kind::Offset(args[0].clone(), a.into())
                } else {
                    let value = match a {
                        "start" => "start()".into(),
                        "end" => "end()".into(),
                        _ => {
                            let n: f64 = a.parse().map_err(|_| "invalid timestamp")?;
                            if !n.is_finite() {
                                return Err("timestamp must be finite".into());
                            }
                            n.to_string()
                        }
                    };
                    Kind::At(args[0].clone(), value)
                };
                Ok(Self::new(kind, args[0].0.ty, mode))
            }
            "keep_metric_names" => {
                arity(1)?;
                if !matches!(args[0].0.kind, Kind::Call(..) | Kind::Binary(..))
                    || args[0].0.ty != Type::Instant
                {
                    return Err(
                        "keep_metric_names requires a vector function or binary operation".into(),
                    );
                }
                Ok(Self::new(
                    Kind::KeepNames(args[0].clone()),
                    Type::Instant,
                    Some(Mode::MetricsQl),
                ))
            }
            "call" => Self::call(a, args),
            _ => Self::call(op, args),
        }
    }
    fn call(name: &str, args: &[Expr]) -> Result<Self> {
        let (ty, required_mode) = functions::validate(name, args)?;
        Ok(Self::new(
            Kind::Call(name.into(), args.to_vec()),
            ty,
            required_mode,
        ))
    }
    fn time_target(&self) -> bool {
        match &self.0.kind {
            Kind::Extra(Extra::Range(..) | Extra::Subquery(..) | Extra::Selectors(..)) => true,
            Kind::Extra(Extra::Offset(base, _) | Extra::Suffix(base, _)) => base.time_target(),
            Kind::Selector(_) | Kind::Range(..) | Kind::Subquery(..) => true,
            Kind::Offset(base, _) | Kind::At(base, _) => base.time_target(),
            _ => false,
        }
    }
    fn has_time_modifier(&self, op: &str) -> bool {
        match &self.0.kind {
            Kind::Offset(base, _) => op == "offset" || base.has_time_modifier(op),
            Kind::At(base, _) => op == "at" || base.has_time_modifier(op),
            Kind::Extra(Extra::Offset(base, _)) => op == "offset" || base.has_time_modifier(op),
            Kind::Extra(Extra::At(base, _)) => op == "at" || base.has_time_modifier(op),
            Kind::Extra(Extra::Suffix(base, _)) => base.has_time_modifier(op),
            _ => false,
        }
    }
    /// Render with bounded expansion. Limits apply to query text, not unique DAG nodes.
    pub fn build(&self, mode: Mode) -> Result<String> {
        self.build_with_limits(mode, BuildLimits::default())
    }

    pub fn build_with_limits(&self, mode: Mode, limits: BuildLimits) -> Result<String> {
        self.build_with_options(
            mode,
            BuildOptions {
                limits,
                ..BuildOptions::default()
            },
        )
    }

    pub fn build_with_options(&self, mode: Mode, options: BuildOptions) -> Result<String> {
        render::build(self, mode, options)
    }

    /// Inspect unique nodes and matcher links, without expanding a shared DAG.
    /// The work budget counts the root, child edges and unique matcher links.
    pub fn inspect(
        &self,
        analysis_only: bool,
        max_bytes: usize,
        max_items: usize,
    ) -> Result<String> {
        diagnostics::inspect(self, analysis_only, max_bytes, max_items)
    }

    /// Render byte spans for expression occurrences with the ordinary build checks.
    pub fn positions(&self, mode: Mode, options: BuildOptions) -> Result<String> {
        diagnostics::positions(self, mode, options)
    }

    /// Saturating size estimates cached without retaining rendered strings.
    pub fn complexity(&self) -> Complexity {
        self.0.complexity
    }
}

impl fmt::Debug for Expr {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Expr")
            .field("type", &self.0.ty)
            .field("complexity", &self.0.complexity)
            .finish_non_exhaustive()
    }
}

impl Kind {
    fn detach_children(&mut self, pending: &mut Vec<Expr>) {
        match std::mem::replace(self, Kind::Number(0.0)) {
            Kind::Template(template) => template.detach(pending),
            Kind::Extra(extra) => extra.detach(pending),
            Kind::Range(child, _)
            | Kind::Parenthesized(child)
            | Kind::Unary(_, child)
            | Kind::KeepNames(child)
            | Kind::Subquery(child, ..)
            | Kind::Offset(child, _)
            | Kind::At(child, _) => pending.push(child),
            Kind::Call(_, children) | Kind::Aggregate(_, children, ..) | Kind::Tuple(children) => {
                pending.extend(children)
            }
            Kind::Binary(binary) => {
                pending.push(binary.lhs);
                pending.push(binary.rhs);
            }
            _ => {}
        }
    }
}

impl Drop for Node {
    fn drop(&mut self) {
        let mut pending = Vec::new();
        self.kind.detach_children(&mut pending);
        while let Some(expr) = pending.pop() {
            if let Some(mut node) = Arc::into_inner(expr.0) {
                node.kind.detach_children(&mut pending);
            }
        }
    }
}

#[cfg(test)]
mod tests;
