"""Explicit responsibility and syntax witnesses for official documentation topics.

New upstream prose has no default exemption: an unmatched item remains a gap.
"""
TOPICS = {
    "aggregate-functions": ["sum", "variadic_aggregate", "aggregate_limit"],
    "implicit-query-conversions": ["scalar_rollup", "range_transform", "scalar_aggregate"],
    "label-manipulation-functions": ["label_copy", "label_replace"],
    "metricsql-features": ["with_template", "selector_or", "group_prefix"],
    "metricsql-functions": ["rate", "abs", "sum"],
    "rollup-functions": ["rate", "implicit_range"],
    "transform-functions": ["abs", "label_replace"],
    "prom-basics/duration-expressions": ["duration_expression", "duration_subquery", "duration_offset"],
    "prom-basics/examples": ["rate", "subquery", "matching"],
    "prom-basics/expression-language-data-types": ["scalar", "rate", "selector", "label_replace"],
    "prom-basics/extended-range-selectors": ["anchored", "smoothed", "smoothed_instant"],
    "prom-basics/extended-range-selectors/anchored": ["anchored"],
    "prom-basics/extended-range-selectors/smoothed": ["smoothed", "smoothed_instant"],
    "prom-basics/functions": ["rate", "histogram_quantile"],
    "prom-basics/literals": ["nonfinite_nan", "duration_literal", "numeric_suffix", "selector"],
    "prom-basics/operators": ["arithmetic", "matching"],
    "prom-basics/time-series-selectors": ["selector", "utf8_names", "rate"],
    "prom-operators/aggregation-operators": ["sum", "count_values", "experimental_limitk", "experimental_limit_ratio"],
    "prom-operators/binary-operators": ["arithmetic", "comparison", "set_and"],
    "prom-operators/detailed-explanations": ["sum", "avg", "topk"],
    "prom-operators/filling-in-missing-matches": ["fill", "fill_sides"],
    "prom-operators/histogram-trim-operators": ["histogram_trim_lower", "histogram_trim_upper"],
    "prom-operators/vector-matching": ["matching", "matching_bool", "empty_matching"],
}
for title, names in {
    "avg": ["avg"], "count": ["count"], "count_values": ["count_values"],
    "group": ["group"], "limit_ratio": ["experimental_limit_ratio"], "limitk": ["experimental_limitk"],
    "min-and-max": ["min", "max"], "quantile": ["quantile"], "stddev": ["stddev"],
    "stdvar": ["stdvar"], "sum": ["sum"], "topk-and-bottomk": ["topk", "bottomk"],
}.items():
    for suffix in ("", "/example", "/examples"):
        TOPICS["prom-operators/detailed-explanations/" + title + suffix] = names

FEATURES = (
    ("The duration suffix is optional.", ["unitless_range"]),
    ("Support for matching against multiple numeric", ["tuple_equal", "tuple_not_equal"]),
    ("Numeric values may include underscore", ["numeric_suffix"]),
    ("[offset]", ["step_range", "fractional_subquery", "aggregate_offset"]),
    ("Aggregate functions support optional `limit", ["aggregate_limit"]),
    ("[Series selectors]", ["selector_or", "selector_or_common_filter", "selector_or_nested_filter"]),
    ("[Aggregate functions]", ["variadic_aggregate"]),
    ("[histogram_quantile]", ["histogram_bounds"]),
    ("Metric names and labels names may contain escaped", ["utf8_names", "quoted_group", "quoted_matching"]),
    ("Graphite-compatible filters", ["graphite_selector"]),
    ("String literals may be concatenated.", ["with_string", "with_string_filter"]),
    ("[@ modifier]", ["at_expression"]),
    ("Arbitrary subexpression can be used as", ["at_expression"]),
    ("`WITH` templates.", ["with_value", "with_ordered", "with_template", "with_zero_arg"]),
    ("Metric names and label names may contain any unicode", ["utf8_names"]),
    ("Support for `group_left(*)`", ["group_wildcard", "group_prefix"]),
    ("Lookbehind window in square brackets and", ["fractional_range"]),
    ("The duration can be placed anywhere", ["duration_literal", "duration_step_scalar"]),
    ("Numeric values can have", ["numeric_suffix"]),
)


def witnesses(row):
    if row["kind"] == "topic":
        return TOPICS.get(row["name"], [])
    for prefix, names in FEATURES:
        if row.get("description", "").startswith(prefix):
            return names
    return []


def responsibility(row):
    if row.get("in_prometheus_baseline_catalog") is False:
        return "upstream_ahead", "Present in upstream main, absent from the pinned Prometheus 3.15.0 release; tracked for the next baseline."
    if row["kind"] == "semantic_difference" or row["name"] in {
        "prom-basics/reconciliation-of-histogram-bucket-layouts", "prom-basics/samples",
        "prom-basics/staleness", "prom-basics/gotchas", "prom-basics/avoiding-slow-queries-and-overloads",
    }:
        return "backend_owned", "The SDK builds and transports queries; sample evaluation, storage and query scheduling belong to the selected server."
    if row["name"] == "prom-basics/comments" or row.get("description", "").startswith("Trailing commas on all the lists"):
        return "canonical_output", "The builder emits canonical expressions without comments or trailing separators; importing or formatting query source is outside its contract."
    return None
