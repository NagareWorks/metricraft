//! Function signatures for the supported migration surface. No raw-name fallback.
use super::{Expr, Kind, Mode, Result, Type};

mod extensions;
mod labels;
pub(super) mod variadic;
type Signature = (&'static [Type], usize, usize, Type, bool);

// Server features are independent of dialect support and are checked at build time.
pub(super) fn experimental(name: &str) -> bool {
    matches!(
        name,
        "sort_by_label"
            | "sort_by_label_desc"
            | "mad_over_time"
            | "double_exponential_smoothing"
            | "limitk"
            | "limit_ratio"
            | "info"
            | "ts_of_last_over_time"
            | "ts_of_max_over_time"
            | "ts_of_min_over_time"
            | "ts_of_first_over_time"
            | "histogram_quantiles"
            | "start_timestamp"
            | "min_of"
            | "max_of"
            | "start"
            | "end"
            | "step"
            | "range"
    )
}

pub(super) fn validate(name: &str, args: &[Expr]) -> Result<(Type, Option<Mode>)> {
    for arg in args.iter().filter(|a| a.0.ty == Type::Range) {
        let mut current = arg;
        loop {
            match &current.0.kind {
                Kind::Extra(super::Extra::Suffix(_, modifier)) => {
                    let allowed = matches!(name, "rate" | "increase" | "delta")
                        || *modifier == "anchored" && matches!(name, "changes" | "resets");
                    if !allowed {
                        return Err(format!("{name} does not accept {modifier} range selectors"));
                    }
                    break;
                }
                Kind::Offset(base, _)
                | Kind::At(base, _)
                | Kind::Parenthesized(base)
                | Kind::Extra(super::Extra::Offset(base, _)) => current = base,
                _ => break,
            }
        }
    }
    if let Some(result) = variadic::validate(name, args) {
        return result;
    }
    use Type::*;
    let (types, min, max, output, vm_only): Signature = match name {
        "rate" | "irate" | "increase" | "delta" | "idelta" | "deriv" | "changes" | "resets"
        | "sum_over_time" | "avg_over_time" | "min_over_time" | "max_over_time"
        | "count_over_time" | "stddev_over_time" | "stdvar_over_time" | "last_over_time"
        | "present_over_time" | "absent_over_time" | "mad_over_time" | "first_over_time" => {
            (&[Range], 1, 1, Instant, false)
        }
        "median_over_time" | "mode_over_time" | "zscore_over_time" | "rate_over_sum" => {
            (&[Range], 1, 1, Instant, true)
        }
        "rollup" | "rollup_rate" => (&[Range, String], 1, 2, Instant, true),
        "union" => (&[Instant], 0, usize::MAX, Instant, true),
        "holt_winters" => (&[Range, Scalar, Scalar], 3, 3, Instant, true),
        "double_exponential_smoothing" => (&[Range, Scalar, Scalar], 3, 3, Instant, false),
        "smooth_exponential" => (&[Instant, Scalar], 2, 2, Instant, true),
        "info" => (&[Instant, Instant], 1, 2, Instant, false),
        "ts_of_last_over_time"
        | "ts_of_max_over_time"
        | "ts_of_min_over_time"
        | "ts_of_first_over_time" => (&[Range], 1, 1, Instant, false),
        "now" => (&[], 0, 0, Scalar, true),
        "start" | "end" | "step" | "range" => (&[], 0, 0, Scalar, false),
        "start_timestamp" => (&[Instant], 1, 1, Instant, false),
        "min_of" | "max_of" => (&[Scalar, Scalar], 2, 2, Scalar, false),
        "abs" | "absent" | "ceil" | "floor" | "sqrt" | "exp" | "ln" | "log2" | "log10" | "sgn"
        | "sort" | "sort_desc" | "timestamp" | "sin" | "cos" | "tan" | "asin" | "acos" | "atan"
        | "sinh" | "cosh" | "tanh" | "asinh" | "acosh" | "atanh" | "deg" | "rad"
        | "histogram_avg" | "histogram_count" | "histogram_sum" | "histogram_stddev"
        | "histogram_stdvar" => (&[Instant], 1, 1, Instant, false),
        "day_of_month" | "day_of_week" | "day_of_year" | "days_in_month" | "hour" | "minute"
        | "month" | "year" => (&[Instant], 0, 1, Instant, false),
        "time" | "pi" => (&[], 0, 0, Scalar, false),
        "scalar" => (&[Instant], 1, 1, Scalar, false),
        "vector" => (&[Scalar], 1, 1, Instant, false),
        "clamp" => (&[Instant, Scalar, Scalar], 3, 3, Instant, false),
        "clamp_min" | "clamp_max" => (&[Instant, Scalar], 2, 2, Instant, false),
        "round" => (&[Instant, Scalar], 1, 2, Instant, false),
        "histogram_quantile" => (&[Scalar, Instant, String], 2, 3, Instant, false),
        "histogram_fraction" => (&[Scalar, Scalar, Instant], 3, 3, Instant, false),
        "quantile_over_time" => (&[Scalar, Range], 2, 2, Instant, false),
        "predict_linear" => (&[Range, Scalar], 2, 2, Instant, false),
        _ => labels::signature(name)
            .or_else(|| extensions::signature(name))
            .ok_or_else(|| format!("function {name:?} is not implemented"))?,
    };
    if args.len() < min || args.len() > max {
        return Err(format!("invalid argument count for {name}"));
    }
    let mut implicit_range = name == "histogram_quantile" && args.len() == 3;
    for (i, arg) in args.iter().enumerate() {
        let expected = types[i.min(types.len() - 1)];
        if expected != arg.0.ty
            && matches!(expected, Scalar | Instant | Range)
            && matches!(arg.0.ty, Scalar | Instant | Range)
        {
            implicit_range = true;
        } else if arg.0.ty != expected {
            return Err(format!("{name} argument {} requires {expected:?}", i + 1));
        }
    }
    labels::validate(name, args)?;
    let prom_only = matches!(
        name,
        "histogram_count"
            | "histogram_sum"
            | "double_exponential_smoothing"
            | "info"
            | "ts_of_last_over_time"
            | "ts_of_max_over_time"
            | "ts_of_min_over_time"
            | "ts_of_first_over_time"
            | "start_timestamp"
            | "min_of"
            | "max_of"
            | "range"
    ) || matches!(name, "sort_by_label" | "sort_by_label_desc") && args.len() == 1;
    if implicit_range && prom_only {
        return Err(format!("{name} requires an explicit range vector"));
    }
    match name {
        "info" if args.len() == 2 => {
            if !matches!(&args[1].0.kind, Kind::Selector(s) if s.name.is_empty()) {
                return Err(
                    "info second argument must be an unnamed label selector; use from_labels()"
                        .into(),
                );
            }
        }
        "holt_winters" | "double_exponential_smoothing" => {
            for arg in &args[1..] {
                if let Kind::Number(n) = arg.0.kind {
                    if !(0.0 < n && n < 1.0) {
                        return Err(
                            "smoothing and trend factors must be strictly between 0 and 1".into(),
                        );
                    }
                }
            }
        }
        "smooth_exponential" => {
            if let Kind::Number(n) = args[1].0.kind {
                if !(0.0..=1.0).contains(&n) {
                    return Err("smoothing factor must be between 0 and 1".into());
                }
            }
        }
        "rollup"
        | "rollup_rate"
        | "rollup_delta"
        | "rollup_deriv"
        | "rollup_increase"
        | "rollup_scrape_interval"
        | "rollup_candlestick"
            if args.len() == 2 =>
        {
            let Kind::String(value) = &args[1].0.kind else {
                return Err("rollup result must be a string literal".into());
            };
            let allowed: &[&str] = if name == "rollup_candlestick" {
                &["open", "close", "low", "high"]
            } else {
                &["min", "max", "avg"]
            };
            if !allowed.contains(&value.as_str()) {
                return Err(format!("rollup result must be one of {allowed:?}"));
            }
        }
        _ => {}
    }
    Ok((
        output,
        if prom_only {
            Some(Mode::PromQl)
        } else if vm_only || implicit_range {
            Some(Mode::MetricsQl)
        } else {
            None
        },
    ))
}
