//! Shared bounded operation-stream oracle for regression tests and libFuzzer.
use metricraft_core::expression::{BuildLimits, BuildOptions, Expr, Mode};

pub fn exercise(data: &[u8]) {
    let base = Expr::apply("metric", "requests_total", "", &[]).unwrap();
    let number = Expr::apply("number", "1", "", &[]).unwrap();
    let label = Expr::apply("string", "job", "", &[]).unwrap();
    let mut roots = vec![base.clone(), number, label];
    let limits = BuildLimits {
        max_output_bytes: 16_384,
        max_expanded_nodes: 256,
    };
    const OPS: &[&str] = &[
        "abs",
        "sum",
        "+",
        "/",
        "range",
        "rate",
        "subquery",
        "by",
        "without",
        "default",
        "parenthesize",
        "negate",
        "=",
        "=~",
        "offset",
        "at",
        "bool",
        "on",
        "group_left",
        "union",
        "string",
        "metric",
        "number",
        "invalid_op",
        "label_copy",
        "label_move",
        "label_map",
        "label_lowercase",
        "label_uppercase",
        "label_match",
        "label_mismatch",
        "label_transform",
        "label_value",
        "labels_equal",
        "label_graphite_group",
        "drop_common_labels",
        "tuple",
        "selector_or",
        "range_expr",
        "subquery_expr",
        "offset_expr",
        "at_expr",
        "anchored",
        "smoothed",
        "aggregate_limit",
        "group_left_all",
        "fill",
        "reference",
        "template_call",
        "template",
        "with",
        "match_expr",
        "histogram_quantiles_auto",
        "aggr_over_time",
        "quantiles",
        "duration_literal",
        "numeric_literal",
    ];
    for instruction in data.chunks_exact(4).take(64) {
        let left = roots[usize::from(instruction[1]) % roots.len()].clone();
        let right = roots[usize::from(instruction[2]) % roots.len()].clone();
        let before = left.build_with_limits(Mode::MetricsQl, limits);
        let op = OPS[usize::from(instruction[0]) % OPS.len()];
        let field = [
            "job",
            "5m",
            "bad-label",
            "a\"\\\n中",
            "1",
            "",
            "now()",
            "1h",
        ][usize::from(instruction[3]) % 8];
        let string = |value| Expr::apply("string", value, "", &[]).unwrap();
        let args = match op {
            "metric" | "string" | "number" | "reference" | "numeric_literal"
            | "duration_literal" => vec![],
            "tuple" | "selector_or" | "range_expr" | "subquery_expr" | "offset_expr"
            | "at_expr" | "aggregate_limit" | "fill" => vec![left.clone(), right],
            "template" => vec![string("x"), left.clone()],
            "with" => vec![left.clone(), string("x"), right],
            "match_expr" => vec![left.clone(), right],
            "histogram_quantiles_auto" | "quantiles" => vec![string("phi"), right, left.clone()],
            "aggr_over_time" => vec![string("min_over_time"), left.clone()],
            "+" | "/" | "default" | "union" | "by" | "without" | "on" | "group_left" => {
                vec![left.clone(), right]
            }
            "label_copy" | "label_move" => vec![left.clone(), string("job"), string(field)],
            "label_map" => vec![left.clone(), string("job"), string(field), string("api")],
            "label_match" | "label_mismatch" => vec![left.clone(), string("job"), string(field)],
            "label_transform" => vec![left.clone(), string("job"), string(field), string("$1")],
            "labels_equal" => vec![left.clone(), string("job"), right],
            "label_lowercase"
            | "label_uppercase"
            | "label_value"
            | "label_graphite_group"
            | "drop_common_labels" => vec![left.clone(), right],
            _ => vec![left.clone()],
        };
        let second = match op {
            "reference" | "template_call" if instruction[3] & 1 == 0 => "instant",
            "match_expr" if instruction[3] & 1 == 0 => "=",
            _ => field,
        };
        let result = Expr::apply(op, field, second, &args);
        assert_eq!(left.build_with_limits(Mode::MetricsQl, limits), before);
        if let Ok(query) = result {
            for mode in [Mode::PromQl, Mode::MetricsQl] {
                let options = BuildOptions {
                    limits,
                    experimental_functions: true,
                    syntax_features: 14,
                };
                if let Ok(text) = query.build_with_options(mode, options) {
                    assert_eq!(text.len(), query.complexity().output_bytes);
                    assert_eq!(query.build_with_options(mode, options).unwrap(), text);
                }
                if let Ok(text) = query.build_with_limits(mode, limits) {
                    assert_eq!(text.len(), query.complexity().output_bytes);
                    assert_eq!(query.build_with_limits(mode, limits).unwrap(), text);
                    assert!(query
                        .build_with_limits(
                            mode,
                            BuildLimits {
                                max_output_bytes: text.len().saturating_sub(1),
                                ..limits
                            }
                        )
                        .is_err());
                }
            }
            let _ = query.inspect(false, 4096, 128);
            assert!(query.inspect(false, 1, 128).is_err());
            if roots.len() < 16 {
                roots.push(query);
            } else {
                roots[usize::from(instruction[3]) % 16] = query;
            }
        }
    }
    assert_eq!(base.build(Mode::PromQl).unwrap(), "requests_total");
}
