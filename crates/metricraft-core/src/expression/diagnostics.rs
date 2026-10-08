//! Bounded, read-only diagnostics over unique nodes, without expanding shared DAGs.
use super::{comparison, quote, quote_len, Expr, Kind, Result};
use std::collections::{BTreeSet, HashMap};
use std::fmt::{self, Write};
use std::sync::Arc;

pub(super) fn name(kind: &Kind) -> &'static str {
    match kind {
        Kind::Template(_) => "template",
        Kind::Extra(extra) => extra.name(),
        Kind::Selector(_) => "selector",
        Kind::Number(_) => "number",
        Kind::String(_) => "string",
        Kind::Tuple(_) => "tuple",
        Kind::Range(..) => "range",
        Kind::Call(..) => "function",
        Kind::Aggregate(..) => "aggregate",
        Kind::Binary(_) => "binary",
        Kind::Unary(..) => "unary",
        Kind::Parenthesized(_) => "parentheses",
        Kind::KeepNames(_) => "keep_metric_names",
        Kind::Subquery(..) => "subquery",
        Kind::Offset(..) => "offset",
        Kind::At(..) => "at",
    }
}

pub(super) struct Json {
    pub text: String,
    limit: usize,
}
impl Json {
    pub fn new(limit: usize) -> Self {
        Self {
            text: String::new(),
            limit,
        }
    }
    pub fn quoted(&mut self, value: &str) -> fmt::Result {
        if quote_len(value) > self.limit.saturating_sub(self.text.len()) {
            return Err(fmt::Error);
        }
        quote(value, &mut self.text);
        Ok(())
    }
    fn strings<'a>(&mut self, values: impl IntoIterator<Item = &'a str>) -> fmt::Result {
        self.write_char('[')?;
        for (i, value) in values.into_iter().enumerate() {
            if i != 0 {
                self.write_char(',')?;
            }
            self.quoted(value)?;
        }
        self.write_char(']')
    }
}
impl Write for Json {
    fn write_str(&mut self, value: &str) -> fmt::Result {
        if value.len() > self.limit.saturating_sub(self.text.len()) {
            return Err(fmt::Error);
        }
        self.text.push_str(value);
        Ok(())
    }
}

fn children<'a>(expr: &'a Expr, mut visit: impl FnMut(&'a Expr) -> Result<()>) -> Result<()> {
    match &expr.0.kind {
        Kind::Template(template) => {
            for child in template.children() {
                visit(child)?;
            }
        }
        Kind::Extra(extra) => {
            for child in extra.children() {
                visit(child)?;
            }
        }
        Kind::Range(c, _)
        | Kind::Unary(_, c)
        | Kind::KeepNames(c)
        | Kind::Parenthesized(c)
        | Kind::Subquery(c, ..)
        | Kind::Offset(c, _)
        | Kind::At(c, _) => visit(c)?,
        Kind::Call(_, args) | Kind::Aggregate(_, args, ..) | Kind::Tuple(args) => {
            for child in args {
                visit(child)?;
            }
        }
        Kind::Binary(b) => {
            visit(&b.lhs)?;
            visit(&b.rhs)?;
        }
        _ => {}
    }
    Ok(())
}

pub(super) fn inspect(
    root: &Expr,
    analysis_only: bool,
    max_bytes: usize,
    max_items: usize,
) -> Result<String> {
    let mut nodes = vec![root];
    let mut ids = HashMap::from([(Arc::as_ptr(&root.0), 0usize)]);
    let mut edges = Vec::new();
    let mut matchers = Vec::new();
    let mut matcher_ids = HashMap::new();
    let mut items = 1usize;
    let mut charge = || -> Result<()> {
        items = items.saturating_add(1);
        if items > max_items {
            Err("diagnostics exceed max_items".into())
        } else {
            Ok(())
        }
    };
    if max_items == 0 {
        return Err("diagnostics exceed max_items".into());
    }
    let mut index = 0;
    while index < nodes.len() {
        let node = nodes[index];
        let mut child_ids = Vec::new();
        children(node, |child| {
            charge()?; // Bound edges as well as unique nodes.
            let key = Arc::as_ptr(&child.0);
            let id = *ids.entry(key).or_insert_with(|| {
                nodes.push(child);
                nodes.len() - 1
            });
            child_ids.push(id);
            Ok(())
        })?;
        edges.push(child_ids);
        if let Kind::Selector(s) = &node.0.kind {
            let mut current = s.matchers.as_ref();
            while let Some(matcher) = current {
                let key = Arc::as_ptr(matcher);
                if matcher_ids.contains_key(&key) {
                    break;
                }
                charge()?;
                matcher_ids.insert(key, matchers.len());
                matchers.push(matcher.as_ref());
                current = matcher.previous.as_ref();
            }
        }
        index += 1;
    }
    // Postorder memoization counts depth once per unique node, including shared descendants.
    let mut depths = vec![None; nodes.len()];
    let mut has_aggregate = vec![false; nodes.len()];
    let mut nested_aggregate = false;
    let mut pending = vec![(0usize, false)];
    while let Some((id, finish)) = pending.pop() {
        if depths[id].is_some() {
            continue;
        }
        if finish {
            depths[id] = Some(
                edges[id]
                    .iter()
                    .map(|&c| depths[c].unwrap() + 1)
                    .max()
                    .unwrap_or(0usize),
            );
            let child_aggregate = edges[id].iter().any(|&c| has_aggregate[c]);
            let aggregate = matches!(nodes[id].0.kind, Kind::Aggregate(..));
            nested_aggregate |= aggregate && child_aggregate;
            has_aggregate[id] = aggregate || child_aggregate;
        } else {
            pending.push((id, true));
            pending.extend(edges[id].iter().rev().map(|&c| (c, false)));
        }
    }
    let mut metrics = BTreeSet::new();
    let mut functions = BTreeSet::new();
    let mut ranges = BTreeSet::new();
    let mut function_count = 0;
    let mut or_count = 0;
    let mut comparisons = false;
    let mut arithmetic = false;
    for expr in &nodes {
        match &expr.0.kind {
            Kind::Selector(s) if !s.name.is_empty() => {
                metrics.insert(s.name.as_ref());
            }
            Kind::Call(n, _) | Kind::Aggregate(n, ..) => {
                functions.insert(n.as_str());
                function_count += 1;
            }
            Kind::Range(_, w) | Kind::Subquery(_, w, _) => {
                ranges.insert(w.as_str());
            }
            Kind::Binary(b) => {
                or_count += usize::from(b.op == "or");
                comparisons |= comparison(&b.op);
                arithmetic |= matches!(b.op.as_str(), "+" | "-" | "*" | "/" | "%" | "^" | "atan2");
            }
            _ => {}
        }
    }
    let labels: BTreeSet<_> = matchers.iter().map(|m| m.label.as_ref()).collect();
    let mut issues = Vec::new();
    if matchers.iter().any(|m| matches!(m.op, "=~" | "!~")) {
        issues.push("Contains regex label matchers (potentially expensive)");
    }
    if or_count > 3 {
        issues.push("Contains many OR operations (may be inefficient)");
    }
    if nested_aggregate {
        issues.push("Contains nested aggregations (may be expensive)");
    }
    if ranges.iter().any(|w| {
        w.ends_with('d')
            || w.ends_with('w')
            || w.ends_with('y')
            || w.strip_suffix('h')
                .and_then(|v| v.parse::<u64>().ok())
                .is_some_and(|v| v >= 24)
    }) {
        issues.push("Contains long time ranges (may be expensive)");
    }
    let mut patterns = Vec::new();
    if ["rate", "irate", "increase"]
        .iter()
        .any(|n| functions.contains(n))
    {
        patterns.push("Rate calculation pattern detected");
    }
    if has_aggregate[0] {
        patterns.push("Aggregation pattern detected");
    }
    if comparisons {
        patterns.push("Comparison/alerting pattern detected");
    }
    if arithmetic {
        patterns.push("Arithmetic computation pattern detected");
    }
    let mut out = Json::new(max_bytes);
    let serialize = |out: &mut Json| -> fmt::Result {
        let score = depths[0].unwrap() as f64 * 2.0
            + nodes.len() as f64 * 0.5
            + function_count as f64 * 3.0;
        let level = if score < 10.0 {
            "Low"
        } else if score < 25.0 {
            "Medium"
        } else if score < 50.0 {
            "High"
        } else {
            "Very High"
        };
        write!(out, "{{\"schema\":1,\"counting\":\"unique expression nodes\",\"metrics\":{{\"unique_metrics\":{},\"metric_names\":", metrics.len())?;
        out.strings(metrics.iter().copied())?;
        write!(out, ",\"unique_labels\":{},\"label_names\":", labels.len())?;
        out.strings(labels.iter().copied())?;
        write!(
            out,
            ",\"function_count\":{function_count},\"function_types\":"
        )?;
        out.strings(functions.iter().copied())?;
        write!(out, "}},\"complexity\":{{\"depth\":{},\"node_count\":{},\"matcher_count\":{},\"function_count\":{function_count},\"expanded_nodes\":{},\"output_bytes\":{},\"complexity_score\":{score},\"complexity_level\":\"{level}\"}},\"performance\":{{\"issue_count\":{},\"potential_issues\":", depths[0].unwrap(), nodes.len(), matchers.len(), root.complexity().expanded_nodes, root.complexity().output_bytes, issues.len())?;
        out.strings(issues.iter().copied())?;
        out.write_str(",\"range_durations\":")?;
        out.strings(ranges.iter().copied())?;
        write!(
            out,
            "}},\"patterns\":{{\"pattern_count\":{},\"detected_patterns\":",
            patterns.len()
        )?;
        out.strings(patterns.iter().copied())?;
        out.write_char('}')?;
        if !analysis_only {
            out.write_str(",\"root\":0,\"nodes\":[\n")?;
            for (id, expr) in nodes.iter().enumerate() {
                if id != 0 {
                    out.write_str(",\n")?;
                }
                write!(out, "{{\"id\":{id},\"kind\":\"{}\",\"type\":\"{:?}\",\"required_mode\":\"{:?}\",\"children\":{:?}", name(&expr.0.kind), expr.0.ty, expr.0.required_mode, edges[id])?;
                match &expr.0.kind {
                    Kind::Selector(s) => {
                        out.write_str(",\"metric\":")?;
                        out.quoted(&s.name)?;
                        match &s.matchers {
                            Some(m) => {
                                write!(out, ",\"matcher\":{}", matcher_ids[&Arc::as_ptr(m)])?
                            }
                            None => out.write_str(",\"matcher\":null")?,
                        }
                    }
                    Kind::Number(n) => {
                        out.write_str(",\"value\":")?;
                        if n.is_finite() {
                            write!(out, "{n}")?;
                        } else {
                            out.quoted(&n.to_string())?;
                        }
                    }
                    Kind::String(s)
                    | Kind::Call(s, _)
                    | Kind::Unary(s, _)
                    | Kind::Range(_, s)
                    | Kind::Offset(_, s)
                    | Kind::At(_, s) => {
                        out.write_str(",\"value\":")?;
                        out.quoted(s)?;
                    }
                    Kind::Aggregate(n, _, groups, without) => {
                        out.write_str(",\"name\":")?;
                        out.quoted(n)?;
                        write!(out, ",\"without\":{without},\"grouping\":")?;
                        if let Some(groups) = groups {
                            out.strings(groups.iter().map(String::as_str))?;
                        } else {
                            out.write_str("null")?;
                        }
                    }
                    Kind::Binary(b) => {
                        out.write_str(",\"operator\":")?;
                        out.quoted(&b.op)?;
                        write!(out, ",\"bool\":{}", b.return_bool)?;
                        for (key, modifier) in
                            [("matching", &b.matching), ("grouping", &b.grouping)]
                        {
                            write!(out, ",\"{key}\":")?;
                            if let Some(m) = modifier {
                                out.write_str("{\"kind\":")?;
                                out.quoted(&m.0)?;
                                out.write_str(",\"labels\":")?;
                                out.strings(m.1.iter().map(String::as_str))?;
                                out.write_char('}')?;
                            } else {
                                out.write_str("null")?;
                            }
                        }
                    }
                    Kind::Subquery(_, w, s) => {
                        out.write_str(",\"window\":")?;
                        out.quoted(w)?;
                        out.write_str(",\"step\":")?;
                        out.quoted(s)?;
                    }
                    _ => {}
                }
                out.write_char('}')?;
            }
            out.write_str("],\"matchers\":[")?;
            for (id, m) in matchers.iter().enumerate() {
                if id != 0 {
                    out.write_char(',')?;
                }
                write!(out, "{{\"id\":{id},\"label\":")?;
                out.quoted(&m.label)?;
                out.write_str(",\"op\":")?;
                out.quoted(m.op)?;
                out.write_str(",\"value\":")?;
                out.quoted(&m.value)?;
                out.write_str(",\"previous\":")?;
                match &m.previous {
                    Some(p) => write!(out, "{}", matcher_ids[&Arc::as_ptr(p)])?,
                    None => out.write_str("null")?,
                }
                out.write_char('}')?;
            }
            out.write_char(']')?;
        }
        out.write_char('}')
    };
    serialize(&mut out).map_err(|_| "diagnostics exceed max_output_bytes")?;
    Ok(out.text)
}

pub(super) fn positions(
    root: &Expr,
    mode: super::Mode,
    options: super::BuildOptions,
) -> Result<String> {
    let mut spans = Json::new(options.limits.max_output_bytes);
    spans
        .write_str("{\"schema\":1,\"positions\":[")
        .map_err(|_| "diagnostics exceed max_output_bytes")?;
    let mut first = true;
    let source = super::render::build_observed(root, mode, options, |expr, offset| {
        let mut serialize = |spans: &mut Json| -> fmt::Result {
            if !first {
                spans.write_char(',')?;
            }
            first = false;
            write!(
                spans,
                "{{\"kind\":\"{}\",\"offset_bytes\":{offset},\"length_bytes\":{}}}",
                name(&expr.0.kind),
                expr.complexity().output_bytes
            )
        };
        serialize(&mut spans).map_err(|_| "diagnostics exceed max_output_bytes".into())
    })?;
    let serialize = |spans: &mut Json| -> fmt::Result {
        spans.write_str("],\"source\":")?;
        spans.quoted(&source)?;
        spans.write_char('}')
    };
    serialize(&mut spans).map_err(|_| "diagnostics exceed max_output_bytes")?;
    Ok(spans.text)
}
