//! One syntax emitter supplies both cached expansion sizes and iterative rendering.
use super::selector::{Matcher, Selector};
use super::{comparison, identifier, quote, quote_len, Expr, Kind, Mode, Result, Type};
use std::fmt::{self, Write};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Complexity {
    /// Expanded occurrences, including matchers. This is not unique node count.
    pub expanded_nodes: usize,
    /// Exact UTF-8 output size, saturating at usize::MAX on overflow.
    pub output_bytes: usize,
}

#[derive(Clone, Copy, Debug)]
pub struct BuildLimits {
    pub max_output_bytes: usize,
    pub max_expanded_nodes: usize,
}

impl Default for BuildLimits {
    fn default() -> Self {
        Self {
            max_output_bytes: 1024 * 1024,
            max_expanded_nodes: 100_000,
        }
    }
}

#[derive(Clone, Copy, Debug, Default)]
pub struct BuildOptions {
    pub limits: BuildLimits,
    /// The caller's Prometheus server must enable promql-experimental-functions.
    pub experimental_functions: bool,
    /// Feature bits 1: duration expressions, 2: extended ranges, 3: binary fill.
    pub syntax_features: u32,
}

pub(super) enum Part<'a> {
    Text(&'a str),
    Quoted(&'a str),
    Label(&'a str),
    Number(f64),
    Child(&'a Expr),
    DurationChild(&'a Expr),
    Bindings(&'a [(String, Expr)]),
    Parameters(&'a [String]),
    EndScope,
    Selector(&'a Selector),
    SelectorBody(&'a Selector),
    SelectorInside(&'a Expr),
    SelectorFilter(&'a super::Extra),
    EndSelectorFilter,
    SelectorValue(&'a Expr),
    RestoreSelectorFilters(Vec<&'a super::Extra>),
    Matcher(&'a Matcher),
}

fn labels<'a>(values: &'a [String], emit: &mut impl FnMut(Part<'a>)) {
    for (i, value) in values.iter().enumerate() {
        if i != 0 {
            emit(Part::Text(", "));
        }
        emit(Part::Label(value));
    }
}

fn escape_label_prefix(s: &str) -> bool {
    s.chars()
        .next()
        .is_some_and(|c| !c.is_alphabetic() && c != '_' && c != ':')
}

fn label_size(s: &str) -> usize {
    if identifier(s, false) {
        s.len()
    } else if escape_label_prefix(s) {
        let first = s.chars().next().unwrap();
        quote_len(&s[first.len_utf8()..]) + if (first as u32) <= 0xffff { 6 } else { 10 }
    } else {
        quote_len(s)
    }
}

fn write_label(s: &str, out: &mut String) {
    if identifier(s, false) {
        out.push_str(s);
    } else if escape_label_prefix(s) {
        // Both parsers understand Unicode escapes. MetricsQL's quoted grouping
        // parser still requires the first encoded character to look like an ident.
        let first = s.chars().next().unwrap();
        let start = out.len();
        quote(&s[first.len_utf8()..], out);
        let escaped = if (first as u32) <= 0xffff {
            format!("\\u{:04x}", first as u32)
        } else {
            format!("\\U{:08x}", first as u32)
        };
        out.insert_str(start + 1, &escaped);
    } else {
        quote(s, out);
    }
}

fn arguments<'a>(values: &'a [Expr], emit: &mut impl FnMut(Part<'a>)) {
    for (i, value) in values.iter().enumerate() {
        if i != 0 {
            emit(Part::Text(", "));
        }
        emit(Part::Child(value));
    }
}

fn parts<'a>(kind: &'a Kind, mode: Mode, mut emit: impl FnMut(Part<'a>)) {
    use Part::*;
    match kind {
        Kind::Template(template) => template.parts(&mut emit),
        Kind::Extra(extra) => extra.parts(&mut emit),
        Kind::Selector(selector) => emit(Selector(selector)),
        Kind::Number(number) => emit(Number(*number)),
        Kind::String(value) => emit(Quoted(value)),
        Kind::Tuple(values) => {
            emit(Text("("));
            arguments(values, &mut emit);
            emit(Text(")"));
        }
        Kind::Parenthesized(child) => {
            emit(Text("("));
            emit(Child(child));
            emit(Text(")"));
        }
        Kind::Range(child, window) => {
            emit(Child(child));
            emit(Text("["));
            emit(Text(window));
            emit(Text("]"));
        }
        Kind::Call(name, args) => {
            emit(Text(name));
            emit(Text("("));
            if name == "histogram_quantiles" && mode == Mode::PromQl && args[0].0.ty == Type::String
            {
                emit(Child(args.last().unwrap()));
                emit(Text(", "));
                arguments(&args[..args.len() - 1], &mut emit);
            } else {
                arguments(args, &mut emit);
            }
            emit(Text(")"));
        }
        Kind::Aggregate(name, args, grouped, without) => {
            emit(Text(name));
            if let Some(grouped) = grouped {
                emit(Text(if *without { " without (" } else { " by (" }));
                labels(grouped, &mut emit);
                emit(Text(")"));
            }
            emit(Text(" ("));
            arguments(args, &mut emit);
            emit(Text(")"));
        }
        Kind::Binary(binary) => {
            if binary.lhs.0.ty == Type::String {
                emit(Child(&binary.lhs));
                emit(Text(" + "));
                emit(Child(&binary.rhs));
                return;
            }
            emit(Text("("));
            emit(Child(&binary.lhs));
            emit(Text(" "));
            emit(Text(&binary.op));
            if binary.return_bool {
                emit(Text(" bool"));
            }
            for (name, values) in [binary.matching.as_deref(), binary.grouping.as_deref()]
                .into_iter()
                .flatten()
            {
                emit(Text(" "));
                emit(Text(name));
                emit(Text(" ("));
                if name.starts_with("group_") && binary.extra.as_ref().is_some_and(|x| x.copy_all) {
                    emit(Text("*"));
                } else {
                    labels(values, &mut emit);
                }
                emit(Text(")"));
            }
            if let Some(extra) = &binary.extra {
                if let Some(prefix) = &extra.prefix {
                    emit(Text(" prefix "));
                    emit(Quoted(prefix));
                }
                for (name, value) in [
                    ("fill_left", extra.fill_left),
                    ("fill_right", extra.fill_right),
                ] {
                    if let Some(value) = value {
                        emit(Text(" "));
                        emit(Text(name));
                        emit(Text("("));
                        emit(Number(value));
                        emit(Text(")"));
                    }
                }
            }
            emit(Text(" "));
            emit(Child(&binary.rhs));
            emit(Text(")"));
        }
        Kind::KeepNames(child) => {
            emit(Child(child));
            emit(Text(" keep_metric_names"));
        }
        Kind::Unary(sign, child) => {
            emit(Text(sign));
            emit(Text("("));
            emit(Child(child));
            emit(Text(")"));
        }
        Kind::Subquery(child, window, step) => {
            emit(Text("("));
            emit(Child(child));
            emit(Text(")["));
            emit(Text(window));
            emit(Text(":"));
            emit(Text(step));
            emit(Text("]"));
        }
        Kind::Offset(child, window) => {
            emit(Child(child));
            emit(Text(" offset "));
            emit(Text(window));
        }
        Kind::At(child, value) => {
            emit(Child(child));
            emit(Text(" @ "));
            emit(Text(value));
        }
    }
}

struct Count(usize);
impl Write for Count {
    fn write_str(&mut self, s: &str) -> fmt::Result {
        self.0 = self.0.saturating_add(s.len());
        Ok(())
    }
}

pub(super) fn complexity(kind: &Kind) -> Complexity {
    let mut cost = Complexity {
        output_bytes: 0,
        expanded_nodes: 1,
    };
    parts(kind, Mode::MetricsQl, |part| {
        let (bytes, nodes) = match part {
            Part::Bindings(_) | Part::Parameters(_) | Part::EndScope | Part::EndSelectorFilter => {
                (0, 0)
            }
            Part::SelectorFilter(super::Extra::Matcher(source, label, op, value, count)) => {
                let (_, empty) = super::syntax::selector_counts(source).unwrap();
                let label_bytes = if identifier(label, false) {
                    label.len()
                } else {
                    quote_len(label)
                };
                let bytes = label_bytes
                    .saturating_add(op.len())
                    .saturating_add(value.0.complexity.output_bytes);
                (
                    bytes
                        .saturating_mul(*count)
                        .saturating_add(count.saturating_sub(empty)),
                    value.0.complexity.expanded_nodes.saturating_mul(*count),
                )
            }
            Part::SelectorFilter(_) => unreachable!(),
            Part::Text(s) => (s.len(), 0),
            Part::Quoted(s) => (quote_len(s), 0),
            Part::Label(s) => (label_size(s), 0),
            Part::Number(n) => {
                let mut count = Count(0);
                write!(count, "{n}").unwrap();
                (count.0, 0)
            }
            Part::Child(child) | Part::DurationChild(child) | Part::SelectorValue(child) => (
                child.0.complexity.output_bytes,
                child.0.complexity.expanded_nodes,
            ),
            Part::SelectorInside(expr) => match &expr.0.kind {
                Kind::Selector(s) => (
                    s.body_bytes(),
                    s.matchers.as_ref().map_or(0, |m| m.count).saturating_add(1),
                ),
                _ => (
                    expr.0.complexity.output_bytes.saturating_sub(2),
                    expr.0.complexity.expanded_nodes,
                ),
            },
            Part::SelectorBody(selector) => (
                selector.body_bytes(),
                selector
                    .matchers
                    .as_ref()
                    .map_or(0, |m| m.count)
                    .saturating_add(1),
            ),
            Part::Selector(selector) => (
                selector.output_bytes(),
                selector.matchers.as_ref().map_or(0, |m| m.count),
            ),
            Part::Matcher(_) => unreachable!("matcher frames are emitted only by the renderer"),
            Part::RestoreSelectorFilters(_) => {
                unreachable!("filter frames are emitted only by the renderer")
            }
        };
        cost.output_bytes = cost.output_bytes.saturating_add(bytes);
        cost.expanded_nodes = cost.expanded_nodes.saturating_add(nodes);
    });
    cost
}

pub(super) fn build(root: &Expr, mode: Mode, options: BuildOptions) -> Result<String> {
    build_observed(root, mode, options, |_, _| Ok(()))
}

pub(super) fn build_observed(
    root: &Expr,
    mode: Mode,
    options: BuildOptions,
    mut observe: impl FnMut(&Expr, usize) -> Result<()>,
) -> Result<String> {
    let limits = options.limits;
    let cost = root.complexity();
    if cost.output_bytes > limits.max_output_bytes {
        return Err(format!(
            "query output exceeds max_output_bytes ({})",
            limits.max_output_bytes
        ));
    }
    if cost.expanded_nodes > limits.max_expanded_nodes {
        return Err(format!(
            "query expansion exceeds max_expanded_nodes ({})",
            limits.max_expanded_nodes
        ));
    }
    let mut out = String::new();
    out.try_reserve_exact(cost.output_bytes)
        .map_err(|_| "unable to reserve query output")?;
    let mut pending = vec![Part::Child(root)];
    let mut scopes = Vec::new();
    let mut selector_filters = Vec::new();
    while let Some(part) = pending.pop() {
        match part {
            Part::SelectorFilter(filter) => selector_filters.push(filter),
            Part::EndSelectorFilter => {
                selector_filters.pop();
            }
            Part::SelectorValue(value) => {
                // A string expression may itself contain WITH bindings whose
                // selectors must not inherit the enclosing selector's filters.
                if !matches!(value.0.kind, Kind::String(_)) {
                    pending.push(Part::RestoreSelectorFilters(std::mem::take(
                        &mut selector_filters,
                    )));
                }
                pending.push(Part::Child(value));
            }
            Part::RestoreSelectorFilters(filters) => selector_filters = filters,
            Part::Bindings(bindings) => scopes.push(super::templates::Scope::Bindings(bindings)),
            Part::Parameters(params) => scopes.push(super::templates::Scope::Parameters(params)),
            Part::EndScope => {
                scopes.pop();
            }
            Part::Text(s) => out.push_str(s),
            Part::Quoted(s) => quote(s, &mut out),
            Part::Label(s) => write_label(s, &mut out),
            Part::Number(n) => write!(out, "{n}").unwrap(),
            Part::Selector(selector) => {
                if mode == Mode::PromQl && !selector.prom_valid() {
                    return Err(
                        "PromQL selectors require a metric or a matcher that excludes empty values"
                            .into(),
                    );
                }
                let bare = !selector.name.is_empty() && identifier(&selector.name, true);
                if bare {
                    out.push_str(&selector.name);
                } else {
                    out.push('{');
                    if !selector.name.is_empty() {
                        out.push_str("__name__=");
                        quote(&selector.name, &mut out);
                        if selector.matchers.is_some() {
                            out.push(',');
                        }
                    }
                }
                if let Some(last) = &selector.matchers {
                    if bare {
                        out.push('{');
                    }
                    pending.push(Part::Text("}"));
                    let mut current = Some(last.as_ref());
                    while let Some(matcher) = current {
                        pending.push(Part::Matcher(matcher));
                        current = matcher.previous.as_deref();
                        if current.is_some() {
                            pending.push(Part::Text(","));
                        }
                    }
                } else if !bare {
                    out.push('}');
                }
            }
            Part::SelectorInside(expr) => match &expr.0.kind {
                Kind::Selector(s) => {
                    let start = pending.len();
                    pending.push(Part::SelectorBody(s));
                    let mut nonempty = !s.name.is_empty() || s.matchers.is_some();
                    for filter in selector_filters.iter().rev() {
                        if nonempty {
                            pending.push(Part::Text(","));
                        }
                        filter.filter_parts(&mut |p| pending.push(p));
                        nonempty = true;
                    }
                    pending[start..].reverse();
                }
                Kind::Extra(extra) => {
                    let start = pending.len();
                    extra.matcher_parts(&mut |p| pending.push(p));
                    pending[start..].reverse();
                }
                _ => unreachable!(),
            },
            Part::SelectorBody(selector) => {
                if !selector.name.is_empty() {
                    out.push_str("__name__=");
                    quote(&selector.name, &mut out);
                    if selector.matchers.is_some() {
                        out.push(',');
                    }
                }
                let mut current = selector.matchers.as_deref();
                while let Some(matcher) = current {
                    pending.push(Part::Matcher(matcher));
                    current = matcher.previous.as_deref();
                    if current.is_some() {
                        pending.push(Part::Text(","));
                    }
                }
            }
            Part::Matcher(matcher) => {
                if identifier(&matcher.label, false) {
                    out.push_str(&matcher.label);
                } else {
                    quote(&matcher.label, &mut out);
                }
                out.push_str(matcher.op);
                quote(&matcher.value, &mut out);
            }
            Part::Child(expr) | Part::DurationChild(expr) => {
                let in_duration = matches!(part, Part::DurationChild(_));
                if in_duration {
                    super::literals::validate_duration_node(expr)?;
                }
                observe(expr, out.len())?;
                if let Kind::Template(template) = &expr.0.kind {
                    template.check(expr.0.ty, &scopes)?;
                }
                if mode == Mode::PromQl {
                    if let Kind::Extra(extra) = &expr.0.kind {
                        if extra.feature() & options.syntax_features != extra.feature() {
                            return Err(format!(
                                "{} requires its matching Prometheus experimental feature",
                                extra.name()
                            ));
                        }
                    }
                }
                if mode == Mode::PromQl && !in_duration && !options.experimental_functions {
                    if let Kind::Call(name, _) | Kind::Aggregate(name, _, _, _) = &expr.0.kind {
                        if super::functions::experimental(name) {
                            return Err(format!("{name} requires experimental_functions=True and server --enable-feature=promql-experimental-functions"));
                        }
                    }
                }
                if let Some(required) = expr.0.required_mode {
                    if required != mode {
                        return Err(match required {
                            Mode::MetricsQl => {
                                "MetricsQL-only operation cannot be built in PromQL mode"
                            }
                            Mode::PromQl => {
                                "PromQL-only operation cannot be built in MetricsQL mode"
                            }
                        }
                        .into());
                    }
                }
                if let Kind::Binary(binary) = &expr.0.kind {
                    if mode == Mode::PromQl
                        && binary
                            .extra
                            .as_ref()
                            .is_some_and(|x| x.fill_left.is_some() || x.fill_right.is_some())
                        && options.syntax_features & 8 == 0
                    {
                        return Err("fill requires features=('promql-binop-fill-modifiers',) and its server flag".into());
                    }
                    if mode == Mode::PromQl
                        && comparison(&binary.op)
                        && binary.lhs.0.ty == Type::Scalar
                        && binary.rhs.0.ty == Type::Scalar
                        && !binary.return_bool
                    {
                        return Err("scalar comparisons require bool in PromQL".into());
                    }
                }
                let start = pending.len();
                parts(&expr.0.kind, mode, |part| {
                    pending.push(if in_duration {
                        if let Part::Child(c) = part {
                            Part::DurationChild(c)
                        } else {
                            part
                        }
                    } else {
                        part
                    })
                });
                pending[start..].reverse();
            }
        }
    }
    debug_assert_eq!(out.len(), cost.output_bytes);
    Ok(out)
}
