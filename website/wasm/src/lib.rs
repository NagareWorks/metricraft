//! The documentation's deliberately small UI contract, backed by the real SDK core.
//! This is not a published JavaScript SDK or a query execution engine.
use metricraft_core::{Expr, Mode};
use serde::Deserialize;
use wasm_bindgen::prelude::*;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Matcher {
    label: String,
    op: String,
    value: String,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Plan {
    metric: String,
    matchers: Vec<Matcher>,
    rollup: String,
    window: u32,
    aggregate: String,
    grouping: String,
    labels: Vec<String>,
    arithmetic: String,
    operand: f64,
    #[serde(rename = "scalarSide")]
    scalar_side: String,
    comparison: String,
    threshold: f64,
}

fn construct(input: &str) -> Result<String, String> {
    if input.len() > 16_384 {
        return Err("Configuration exceeds 16 KiB".into());
    }
    let plan: Plan = serde_json::from_str(input).map_err(|e| e.to_string())?;
    if plan.matchers.len() > 12 || plan.labels.len() > 12 {
        return Err("Use at most 12 filters and 12 grouping labels".into());
    }
    if !(1..=3600).contains(&plan.window)
        || !plan.threshold.is_finite()
        || !plan.operand.is_finite()
    {
        return Err("Window must be 1–3600 seconds; numeric operands must be finite".into());
    }
    let mut expr = Expr::apply("metric", &plan.metric, "", &[])?;
    for matcher in plan.matchers {
        if !matches!(matcher.op.as_str(), "=" | "!=" | "=~" | "!~") {
            return Err("Unsupported playground label matcher".into());
        }
        expr = Expr::apply(&matcher.op, &matcher.label, &matcher.value, &[expr])?;
    }
    if plan.rollup != "none" {
        if !matches!(
            plan.rollup.as_str(),
            "rate"
                | "increase"
                | "avg_over_time"
                | "min_over_time"
                | "max_over_time"
                | "sum_over_time"
        ) {
            return Err("Unsupported playground rollup".into());
        }
        expr = Expr::apply("range", &format!("{}s", plan.window), "", &[expr])?;
        expr = Expr::apply(&plan.rollup, "", "", &[expr])?;
    }
    if !matches!(plan.grouping.as_str(), "none" | "by" | "without") {
        return Err("Unsupported grouping mode".into());
    }
    if plan.aggregate == "none" {
        if plan.grouping != "none" || !plan.labels.is_empty() {
            return Err("Grouping requires an aggregation".into());
        }
    } else {
        if !matches!(
            plan.aggregate.as_str(),
            "sum" | "avg" | "min" | "max" | "count"
        ) {
            return Err("Unsupported playground aggregation".into());
        }
        expr = Expr::apply(&plan.aggregate, "", "", &[expr])?;
        if plan.grouping != "none" {
            let mut args = vec![expr];
            for label in plan.labels {
                args.push(Expr::apply("string", &label, "", &[])?);
            }
            expr = Expr::apply(&plan.grouping, "", "", &args)?;
        } else if !plan.labels.is_empty() {
            return Err("Choose by or without before selecting grouping labels".into());
        }
    }
    if !matches!(plan.scalar_side.as_str(), "left" | "right") {
        return Err("Choose left or right for the scalar operand".into());
    }
    match plan.arithmetic.as_str() {
        "none" => {}
        "negate" | "positive" => {
            expr = Expr::apply(&plan.arithmetic, "", "", &[expr])?;
        }
        "+" | "-" | "*" | "/" | "%" | "**" => {
            if plan.scalar_side == "left" && matches!(plan.arithmetic.as_str(), "%" | "**") {
                return Err("Python reverse modulo and power are not overloaded; put the expression on the left".into());
            }
            let scalar = Expr::apply("number", &plan.operand.to_string(), "", &[])?;
            let args = if plan.scalar_side == "left" {
                [scalar, expr]
            } else {
                [expr, scalar]
            };
            let op = if plan.arithmetic == "**" {
                "^"
            } else {
                &plan.arithmetic
            };
            expr = Expr::apply(op, "", "", &args)?;
        }
        _ => return Err("Unsupported playground arithmetic".into()),
    }
    if plan.comparison != "none" {
        if !matches!(
            plan.comparison.as_str(),
            ">" | ">=" | "<" | "<=" | "==" | "!="
        ) {
            return Err("Unsupported playground comparison".into());
        }
        let threshold = Expr::apply("number", &plan.threshold.to_string(), "", &[])?;
        expr = Expr::apply(&plan.comparison, "", "", &[expr, threshold])?;
    }
    expr.build(Mode::PromQl)
}

#[wasm_bindgen]
pub fn build_query(input: &str) -> Result<String, JsValue> {
    construct(input).map_err(|e| JsValue::from_str(&e))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ui_values_are_literals_not_query_fragments() {
        let input = serde_json::json!({
            "metric": "requests_total", "matchers": [{"label":"job", "op":"=", "value":"api\"} or up #"}],
            "rollup":"rate", "window":300, "aggregate":"sum", "grouping":"by", "labels":["job"],
            "comparison":">", "threshold":2.0,
            "arithmetic":"none", "operand":100.0, "scalarSide":"right"
        });
        let query = construct(&input.to_string()).unwrap();
        assert!(query.contains("job=\"api\\\"} or up #\""), "{query}");
        assert!(query.contains("rate("));
        assert!(query.contains("by (job)"), "{query}");
    }
}
