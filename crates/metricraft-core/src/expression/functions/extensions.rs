//! MetricsQL rollup and transform signatures, separate from common PromQL functions.
use super::{Signature, Type};

pub(super) fn signature(name: &str) -> Option<Signature> {
    use Type::*;
    Some(match name {
        "ascent_over_time"
        | "changes_prometheus"
        | "decreases_over_time"
        | "default_rollup"
        | "delta_prometheus"
        | "deriv_fast"
        | "descent_over_time"
        | "distinct_over_time"
        | "geomean_over_time"
        | "histogram_over_time"
        | "ideriv"
        | "increase_prometheus"
        | "increase_pure"
        | "increases_over_time"
        | "integrate"
        | "lag"
        | "lifetime"
        | "outlier_iqr_over_time"
        | "range_over_time"
        | "rate_prometheus"
        | "scrape_interval"
        | "stale_samples_over_time"
        | "sum2_over_time"
        | "tfirst_over_time"
        | "timestamp_with_name"
        | "tlast_change_over_time"
        | "tlast_over_time"
        | "tmax_over_time"
        | "tmin_over_time" => (&[Range], 1, 1, Instant, true),
        "count_eq_over_time" | "count_gt_over_time" | "count_le_over_time"
        | "count_ne_over_time" | "duration_over_time" | "share_eq_over_time"
        | "share_gt_over_time" | "share_le_over_time" | "sum_eq_over_time" | "sum_gt_over_time"
        | "sum_le_over_time" => (&[Range, Scalar], 2, 2, Instant, true),
        "hoeffding_bound_lower" | "hoeffding_bound_upper" => {
            (&[Scalar, Range], 2, 2, Instant, true)
        }
        "count_values_over_time" => (&[String, Range], 2, 2, Instant, true),
        "rollup_candlestick"
        | "rollup_delta"
        | "rollup_deriv"
        | "rollup_increase"
        | "rollup_scrape_interval" => (&[Range, String], 1, 2, Instant, true),
        "bitmap_and" | "bitmap_or" | "bitmap_xor" => (&[Instant, Scalar], 2, 2, Instant, true),
        "buckets_limit" => (&[Scalar, Instant], 2, 2, Instant, true),
        "drop_empty_series"
        | "interpolate"
        | "keep_last_value"
        | "keep_next_value"
        | "prometheus_buckets"
        | "range_avg"
        | "range_first"
        | "range_last"
        | "range_linear_regression"
        | "range_mad"
        | "range_max"
        | "range_median"
        | "range_min"
        | "range_stddev"
        | "range_stdvar"
        | "range_sum"
        | "range_zscore"
        | "remove_resets"
        | "running_avg"
        | "running_max"
        | "running_min"
        | "running_sum"
        | "ttf" => (&[Instant], 1, 1, Instant, true),
        "range_normalize" => (&[Instant], 0, usize::MAX, Instant, true),
        "range_quantile" | "range_trim_outliers" | "range_trim_spikes" | "range_trim_zscore" => {
            (&[Scalar, Instant], 2, 2, Instant, true)
        }
        "histogram_share" => (&[Scalar, Instant, String], 2, 3, Instant, true),
        "limit_offset" => (&[Scalar, Scalar, Instant], 3, 3, Instant, true),
        "ru" => (&[Instant, Instant], 2, 2, Instant, true),
        "rand" | "rand_exponential" | "rand_normal" => (&[Scalar], 0, 1, Scalar, true),
        "timezone_offset" => (&[String], 1, 1, Scalar, true),
        _ => return None,
    })
}
