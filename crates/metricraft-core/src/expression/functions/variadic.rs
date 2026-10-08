//! Signatures with a scalar list between a label and a vector, or a typed tuple.
use super::super::valid_name;
use super::{Expr, Kind, Mode, Result, Type};

pub(super) fn validate(name: &str, args: &[Expr]) -> Option<Result<(Type, Option<Mode>)>> {
    match name {
        "histogram_quantiles" | "quantiles_over_time" => Some(quantiles(name, args)),
        "aggr_over_time" => Some(rollups(args)),
        _ => None,
    }
}

pub(in crate::expression) fn quantiles(name: &str, args: &[Expr]) -> Result<(Type, Option<Mode>)> {
    if args.len() < 3 {
        return Err(format!("{name} requires a label, quantiles and a vector"));
    }
    let prom = name == "histogram_quantiles" && args[0].0.ty == Type::Instant;
    let (label_index, scalars, source) = if prom {
        if args.len() > 12 {
            return Err("histogram_quantiles supports up to 10 quantiles in PromQL".into());
        }
        (1, &args[2..], &args[0])
    } else {
        (0, &args[1..args.len() - 1], args.last().unwrap())
    };
    if args[label_index].0.ty != Type::String
        || matches!(&args[label_index].0.kind, Kind::String(s) if !valid_name(s))
    {
        return Err("quantiles require a string label name".into());
    }
    if scalars.iter().any(|arg| {
        arg.0.ty != Type::Scalar && (prom || !matches!(arg.0.ty, Type::Instant | Type::Range))
    }) {
        return Err("quantiles must be scalar expressions".into());
    }
    let expected = if name == "quantiles_over_time" {
        Type::Range
    } else {
        Type::Instant
    };
    if source.0.ty != expected
        && (prom || !matches!(source.0.ty, Type::Instant | Type::Scalar | Type::Range))
    {
        return Err(format!("{name} requires {expected:?}"));
    }
    Ok((
        Type::Instant,
        Some(if prom { Mode::PromQl } else { Mode::MetricsQl }),
    ))
}

fn rollups(args: &[Expr]) -> Result<(Type, Option<Mode>)> {
    if args.len() != 2 || !matches!(args[1].0.ty, Type::Range | Type::Instant | Type::Scalar) {
        return Err("aggr_over_time requires function names and a range vector".into());
    }
    let names = if let Kind::Tuple(names) = &args[0].0.kind {
        names.as_slice()
    } else {
        &args[..1]
    };
    for name in names {
        let Kind::String(name) = &name.0.kind else {
            return Err("aggr_over_time requires literal function names".into());
        };
        // The backend accepts a specific subset, not every rollup function.
        if !matches!(
            name.as_str(),
            "absent_over_time"
                | "ascent_over_time"
                | "avg_over_time"
                | "changes"
                | "count_over_time"
                | "decreases_over_time"
                | "default_rollup"
                | "delta"
                | "deriv"
                | "deriv_fast"
                | "descent_over_time"
                | "distinct_over_time"
                | "first_over_time"
                | "geomean_over_time"
                | "idelta"
                | "ideriv"
                | "increase"
                | "increase_pure"
                | "increases_over_time"
                | "integrate"
                | "irate"
                | "iqr_over_time"
                | "lag"
                | "last_over_time"
                | "lifetime"
                | "mad_over_time"
                | "max_over_time"
                | "median_over_time"
                | "min_over_time"
                | "mode_over_time"
                | "present_over_time"
                | "range_over_time"
                | "rate"
                | "rate_over_sum"
                | "resets"
                | "scrape_interval"
                | "stale_samples_over_time"
                | "stddev_over_time"
                | "stdvar_over_time"
                | "sum_over_time"
                | "sum2_over_time"
                | "tfirst_over_time"
                | "timestamp"
                | "timestamp_with_name"
                | "tlast_change_over_time"
                | "tlast_over_time"
                | "tmax_over_time"
                | "tmin_over_time"
                | "zscore_over_time"
        ) {
            return Err(format!("{name:?} is not supported by aggr_over_time"));
        }
    }
    Ok((Type::Instant, Some(Mode::MetricsQl)))
}
