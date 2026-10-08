//! Validated aggregation construction. Grouping remains an immutable derivation.
use super::{labels, Expr, Kind, Mode, Result, Type};

pub(super) fn is_name(name: &str) -> bool {
    matches!(
        name,
        "sum"
            | "avg"
            | "min"
            | "max"
            | "count"
            | "stddev"
            | "stdvar"
            | "group"
            | "topk"
            | "bottomk"
            | "quantile"
            | "count_values"
            | "limitk"
            | "limit_ratio"
            | "any"
            | "median"
            | "mode"
            | "mad"
            | "outliersk"
            | "outliers_mad"
            | "outliers_iqr"
            | "distinct"
            | "geomean"
            | "histogram"
            | "quantiles"
            | "share"
            | "sum2"
            | "zscore"
            | "topk_avg"
            | "topk_last"
            | "topk_max"
            | "topk_median"
            | "topk_min"
            | "bottomk_avg"
            | "bottomk_last"
            | "bottomk_max"
            | "bottomk_median"
            | "bottomk_min"
    )
}

pub(super) fn construct(name: &str, args: &[Expr]) -> Result<Expr> {
    let common = matches!(
        name,
        "sum"
            | "avg"
            | "min"
            | "max"
            | "count"
            | "stddev"
            | "stdvar"
            | "group"
            | "topk"
            | "bottomk"
            | "quantile"
            | "count_values"
            | "limitk"
    );
    let rank = name.starts_with("topk_") || name.starts_with("bottomk_");
    let parameterized = rank
        || matches!(
            name,
            "topk"
                | "bottomk"
                | "quantile"
                | "count_values"
                | "outliersk"
                | "outliers_mad"
                | "limitk"
                | "limit_ratio"
        );
    let mut vm = !common && name != "limit_ratio";
    if name == "quantiles" {
        super::functions::variadic::quantiles(name, args)?;
    } else if parameterized {
        if !(args.len() == 2 || rank && args.len() == 3) {
            return Err(format!("invalid argument count for {name}"));
        }
        if name == "count_values" {
            if args[0].0.ty != Type::String {
                return Err("count_values requires a string label".into());
            }
            if matches!(args[0].0.kind, Kind::String(_)) {
                labels(&args[..1])?;
            } else {
                vm = true;
            }
        } else if args[0].0.ty != Type::Scalar {
            if !matches!(args[0].0.ty, Type::Instant | Type::Range) {
                return Err(format!("invalid parameter type for {name}"));
            }
            vm = true;
        }
        if args[1].0.ty != Type::Instant {
            if !matches!(args[1].0.ty, Type::Scalar | Type::Range) {
                return Err("aggregation requires an instant vector".into());
            }
            vm = true;
        }
        if args.len() == 3 && args[2].0.ty != Type::String {
            return Err("other-series label must be a string".into());
        }
    } else {
        if name == "outliers_iqr" && args.len() != 1 {
            return Err("outliers_iqr requires exactly one vector argument".into());
        }
        if args.is_empty()
            || args
                .iter()
                .any(|arg| !matches!(arg.0.ty, Type::Instant | Type::Range | Type::Scalar))
        {
            return Err("aggregation requires instant vector arguments".into());
        }
        vm |= args.len() > 1;
        vm |= args.iter().any(|arg| arg.0.ty != Type::Instant);
    }
    if vm && name == "limit_ratio" {
        return Err("limit_ratio requires PromQL argument types".into());
    }
    Ok(Expr::new(
        Kind::Aggregate(name.into(), args.to_vec(), None, false),
        Type::Instant,
        if name == "limit_ratio" {
            Some(Mode::PromQl)
        } else if vm {
            Some(Mode::MetricsQl)
        } else {
            None
        },
    ))
}
