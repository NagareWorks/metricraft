"""Explicit backend signatures for MetricsQL additions and overload witnesses."""

def recipes(v):
    vector, window = v["Vector"], v["Matrix"]
    result = {}
    for name in (
        "count_eq_over_time", "count_gt_over_time", "count_le_over_time", "count_ne_over_time",
        "duration_over_time", "share_eq_over_time", "share_gt_over_time", "share_le_over_time",
        "sum_eq_over_time", "sum_gt_over_time", "sum_le_over_time",
    ):
        result[name] = [[window, 1]]
    for name in ("hoeffding_bound_lower", "hoeffding_bound_upper"):
        result[name] = [[0.5, window]]
    for name in ("rollup_candlestick", "rollup_delta", "rollup_deriv", "rollup_increase", "rollup_scrape_interval"):
        result[name] = [[window], [window, "open" if name == "rollup_candlestick" else "max"]]
    for name in (
        "drop_empty_series", "interpolate", "keep_last_value", "keep_next_value", "prometheus_buckets",
        "range_avg", "range_first", "range_last", "range_linear_regression", "range_mad", "range_max",
        "range_median", "range_min", "range_stddev", "range_stdvar", "range_sum", "range_zscore",
        "remove_resets", "running_avg", "running_max", "running_min", "running_sum", "ttf",
    ):
        result[name] = [[vector]]
    for name in ("bitmap_and", "bitmap_or", "bitmap_xor"):
        result[name] = [[vector, 3]]
    for name in ("range_quantile", "range_trim_outliers", "range_trim_spikes", "range_trim_zscore"):
        result[name] = [[0.5, vector]]
    for name in ("rand", "rand_exponential", "rand_normal"):
        result[name] = [[], [1]]
    result.update({
        "count_values_over_time": [["value", window]],
        "aggr_over_time": [["min_over_time", window], [vector.from_tuple("min_over_time", "max_over_time"), window]],
        "quantiles_over_time": [["phi", 0.5, window], ["phi", 0.5, 0.9, window]],
        "histogram_quantiles": [["phi", 0.5, vector], ["phi", 0.5, 0.9, vector]],
        "histogram_quantile": [[0.5, vector], [0.5, vector, "bounds"]],
        "histogram_share": [[0.5, vector], [0.5, vector, "bounds"]],
        "limit_offset": [[2, 1, vector]],
        "ru": [[vector, vector]],
        "range_normalize": [[], [vector], [vector, v["Vector2"]]],
        "buckets_limit": [[3, vector]],
        "sort_by_label": [[vector, "job"], [vector, "job", "instance"]],
        "sort_by_label_desc": [[vector, "job"], [vector, "job", "instance"]],
        "timezone_offset": [["UTC"]],
    })
    return result
