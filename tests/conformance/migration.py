"""Executable witnesses for the retained historical builder surface (no legacy runtime)."""
from metricraft import QueryBuilder as Q

RETIRED = {
    "metric": "Metric identity is fixed by from_metric; no retargeting method.",
    "ast_node": "Mutable Python AST access is replaced by bounded native diagnostics.",
    "from_expr": "The old string-literal wrapper was not a parser; saved strings go to the client.",
    "dedup": "The old helper emitted an unsupported dedup function; deduplication is backend policy.",
    "get_builder": "The provider/subtype registry is replaced by one QueryBuilder.",
    "register_builder": "The provider/subtype registry is replaced by one QueryBuilder.",
    "__getattribute__": "Internal dispatch machinery, not a retained SDK operation.",
}
DIAGNOSTICS = {"build", "validate", "debug", "analyze", "to_debug_json",
               "debug_positions", "visualize_positions"}


def expression_cases():
    a, b = Q.from_metric("a"), Q.from_metric("b")
    result = {}
    for name in ("abs acos acosh asin asinh atan atanh ceil cos cosh deg exp floor ln "
                 "log10 log2 rad sin sinh sqrt tan tanh day_of_month day_of_week day_of_year "
                 "hour minute month year timestamp sort_desc positive negative parenthesize "
                 "__pos__ __neg__").split():
        result[name] = getattr(a, name)()
    for name in ("rate irate increase delta idelta deriv changes resets sum_over_time "
                 "avg_over_time min_over_time max_over_time count_over_time stddev_over_time "
                 "stdvar_over_time last_over_time present_over_time mad_over_time median_over_time "
                 "mode_over_time zscore_over_time rate_over_sum rollup_rate moving_average range").split():
        result[name] = getattr(a, name)(duration="5m")
    for name in "sum avg min max count stddev stdvar group any median mode mad".split():
        result[name] = getattr(a, name)().without("instance")
    for name in "topk bottomk outliersk limitk".split():
        result[name] = getattr(a, name)(3).without("instance")
    for name in ("add sub mul div mod pow eq ne gt ge lt le and_ or_ unless atan2 default "
                 "__add__ __sub__ __mul__ __truediv__ __mod__ __pow__ __eq__ __ne__ "
                 "__gt__ __ge__ __lt__ __le__ __and__ __or__").split():
        result[name] = getattr(a, name)(b)
    for name in "__radd__ __rsub__ __rmul__ __rtruediv__".split():
        result[name] = getattr(a, name)(2)
    for name in "from_time from_now from_start from_end".split():
        result[name] = getattr(Q, name)()
    for name in "sort_by_label sort_by_label_desc sort_by_label_numeric sort_by_label_numeric_desc".split():
        result[name] = getattr(a, name)("job")
    result.update({
        "from_metric": Q.from_metric("up"), "from_scalar": Q.from_scalar(1),
        "from_string": Q.from_string('literal"\\text'), "vector": Q.from_scalar(1).vector(),
        "where": a.where("job", "=", "api"), "where_eq": a.where_eq("job", "api"),
        "where_ne": a.where_ne("env", None), "where_regex": a.where_regex("job", "a|b"),
        "where_not_regex": a.where_not_regex("env", "test.*"),
        "at": a.at("2025-01-01T00:00:00Z"), "offset": a.offset("5m"),
        "subquery": a.subquery(range_duration="10m", resolution="1m"),
        "between": a.between(0, 1), "bool": a.gt(0).bool(),
        "by": a.sum().by("job"), "without": a.sum().without("instance"),
        "on": a.add(b).on("job"), "ignoring": a.add(b).ignoring("instance"),
        "group_left": a.add(b).on("job").group_left("env"),
        "group_right": a.add(b).on("job").group_right("env"),
        "quantile": a.quantile(0.9).without("instance"),
        "count_values": a.count_values("value").without("instance"),
        "histogram_quantile": a.histogram_quantile(0.9),
        "quantile_over_time": a.quantile_over_time(quantile=0.9, duration="5m"),
        "predict_linear": a.predict_linear(prediction_seconds=60, duration="5m"),
        "holt_winters": a.holt_winters(duration="5m", smoothing_factor=0.2, trend_factor=0.4),
        "rollup": a.rollup(func="avg", duration="5m"),
        "smooth_exponential": a.smooth_exponential(0.3), "sort": a.sort("desc"),
        "round": a.round(to_nearest=0.5), "clamp_min": a.clamp_min(0), "clamp_max": a.clamp_max(1),
        "label_join": a.label_join("dst", "/", "job", "instance"),
        "label_replace": a.label_replace("dst", "$1", "job", "(.*)"),
        "label_set": a.label_set(env="prod"), "label_del": a.label_del("env"),
        "alias": a.alias("renamed"), "union": a.union(b),
        "keep_metric_names": a.abs().keep_metric_names(),
    })
    return result


def parser_cases():
    for name, query in expression_cases().items():
        if name == "from_string":
            # Recording rules require numeric/vector results; exercise the string as data.
            query = Q.function("label_join", Q.from_metric("a"), "dst", query, "job")
        for mode in ("promql", "metricsql"):
            # The caller enables experimental functions. Unsupported modes must fail closed.
            try:
                query.build(mode, experimental_functions=True)
            except ValueError as error:
                if "MetricsQL-only" not in str(error) and "PromQL-only" not in str(error):
                    raise
                continue
            yield "migration_" + name.replace("__", "dunder_"), query, mode
