"""Representative generated expressions checked by both upstream parsers."""

from metricraft import QueryBuilder as Q

ROLLUPS = (
    "rate",
    "irate",
    "increase",
    "delta",
    "idelta",
    "deriv",
    "changes",
    "resets",
    "sum_over_time",
    "avg_over_time",
    "min_over_time",
    "max_over_time",
    "count_over_time",
    "stddev_over_time",
    "stdvar_over_time",
    "last_over_time",
    "present_over_time",
    "absent_over_time",
)
TRANSFORMS = (
    "abs",
    "absent",
    "ceil",
    "floor",
    "sqrt",
    "exp",
    "ln",
    "log2",
    "log10",
    "sgn",
    "sort",
    "sort_desc",
    "timestamp",
    "sin",
    "cos",
    "tan",
    "asin",
    "acos",
    "atan",
    "sinh",
    "cosh",
    "tanh",
    "asinh",
    "acosh",
    "atanh",
    "deg",
    "rad",
    "histogram_avg",
    "histogram_count",
    "histogram_sum",
    "histogram_stddev",
    "histogram_stdvar",
)
DATES = (
    "day_of_month",
    "day_of_week",
    "day_of_year",
    "days_in_month",
    "hour",
    "minute",
    "month",
    "year",
)


def cases():
    a, b = Q.from_metric("a"), Q.from_metric("b")
    common = {
        "selector": a.where_eq("job", 'api"} or up{job="\\\n\t\r\u0001').where_ne(
            "env", "test"
        ),
        "regex": a.where_regex("job", "a|b").where_not_regex("env", "dev.*"),
        "same_label_conjunction": a.where_ne("env", "dev").where_ne("env", "test"),
        "unnamed_selector": Q.from_labels(job="api").where_regex("instance", "a|b"),
        "scalar": Q.from_scalar(-1.25),
        "negate": -(a + b),
        "positive": +a,
        "arithmetic": (a + b) * (a - 2) / 3 % 2,
        "power": a**2,
        "atan2": a.atan2(b),
        "comparison": a.gt(0),
        "comparison_bool": a.ne(b).bool(),
        "scalar_comparison": Q.from_scalar(1).lt(2).bool(),
        "matching": a.div(b).on("job").group_left("zone"),
        "matching_bool": a.ge(b).bool().ignoring("instance").group_right("zone"),
        "empty_matching": a.add(b).on().group_left(),
        "set_and": a.and_(b).on("job"),
        "set_or": a.or_(b).ignoring("instance"),
        "set_unless": a.unless(b),
        "subquery": a.rate("5m").sum().by("job").subquery("1h", "1m").max_over_time(),
        "subquery_default_step": a.subquery("1h").avg_over_time(),
        "offset": a.range("5m").offset("1h").rate(),
        "negative_offset": a.offset("-5m"),
        "at_timestamp": a.at(1700000000.25),
        "at_start": a.at("start").offset("5m"),
        "at_end": a.offset("5m").at("end"),
        "subquery_offset": a.subquery("1h", "1m")
        .at("end")
        .offset("5m")
        .avg_over_time(),
        "empty_by": a.sum().by(),
        "empty_without": a.sum().without(),
        "topk": a.topk(3).by("job"),
        "bottomk": a.bottomk(3).without("instance"),
        "quantile": a.quantile(0.99),
        "count_values": a.count_values("value"),
        "histogram_quantile": a.histogram_quantile(0.99),
        "histogram_fraction": a.histogram_fraction(0, 1),
        "quantile_over_time": a.range("5m").quantile_over_time(0.5),
        "predict_linear": a.range("5m").predict_linear(60),
        "label_replace": a.label_replace("dst", "$1\\suffix", "src", "(.*)"),
        "label_join": a.label_join("dst", '"\\', "job", "instance"),
        "clamp": a.clamp(0, 1),
        "clamp_min": a.clamp_min(0),
        "clamp_max": a.clamp_max(1),
        "round": a.round(),
        "round_nearest": a.round(0.01),
        "vector": Q.vector(2),
        "scalar_conversion": a.scalar(),
        "time": Q.time(),
        "pi": Q.function("pi"),
        "moving_average": a.moving_average("10m"),
        "between": a.between(0, 1),
        "label_join_no_sources": a.label_join("dst", ","),
    }
    for name in ROLLUPS:
        common[name] = getattr(a.range("5m"), name)()
    for name in TRANSFORMS:
        common[name] = getattr(a, name)()
    for name in DATES:
        common[name] = Q.function(name)
        common[name + "_vector"] = Q.function(name, a)
    for name in ("sum", "avg", "min", "max", "count", "stddev", "stdvar", "group"):
        common[name] = a.aggregate(name).by("job")
    for name, query in common.items():
        yield name, query, "promql"
        if name not in ("histogram_count", "histogram_sum"):
            yield name, query, "metricsql"
    vm = {
        "default": a.default(0),
        "if": a.if_(b),
        "ifnot": a.ifnot(b),
        "keep_names": a.rate("5m").keep_metric_names(),
        "keep_binary_names": a.add(b).keep_metric_names(),
        "implicit_range": a.rate(),
        "implicit_subquery": a.sum().rate(),
        "label_set": a.label_set(team='x"\\y', env="prod"),
        "label_del": a.label_del("zone"),
        "label_keep": a.label_keep("job", "instance"),
        "label_copy": a.label_copy(("job", "service"), ("job", "owner")),
        "label_copy_empty": a.label_copy(),
        "label_move": a.label_move(("job", "service"), ("service", "owner")),
        "label_move_empty": a.label_move(),
        "label_map": a.label_map("job", ('a"\\\n', "api"), ("b", "worker")),
        "label_map_empty": a.label_map("job"),
        "label_lowercase": a.label_lowercase("job", "instance"),
        "label_uppercase": a.label_uppercase("job", "instance"),
        "label_match": a.label_match("job", "api|worker"),
        "label_mismatch": a.label_mismatch("job", "test.*"),
        "label_transform": a.label_transform("job", "(api)", '$1"\\\n'),
        "label_value": a.label_value("shard"),
        "labels_equal": a.labels_equal("job", "service", "owner"),
        "label_graphite_group": a.label_graphite_group(0, 2),
        "drop_common_labels": a.drop_common_labels(),
        "drop_common_labels_multiple": a.drop_common_labels(b),
        "union": a.union(b),
        "alias": a.alias('name"\\suffix'),
        "outliersk": a.outliersk(3).by("job"),
        "holt_winters": a.holt_winters("5m", 0.3, 0.3),
        "smooth_exponential": a.smooth_exponential(0.3),
        "sort_by_label": a.sort_by_label("job", "instance"),
        "sort_by_label_desc": a.sort_by_label_desc("job"),
        "sort_by_label_numeric": a.sort_by_label_numeric("job"),
        "sort_by_label_numeric_desc": a.sort_by_label_numeric_desc("job"),
        "now": Q.now(),
        "start": Q.start(),
        "end": Q.end(),
        "step": Q.step(),
        "limitk": a.limitk(3).by("job"),
    }
    for name in ("mad_over_time", "median_over_time", "mode_over_time", "zscore_over_time",
                 "rate_over_sum", "rollup", "rollup_rate"):
        vm[name] = getattr(a, name)("5m")
        vm[name + "_implicit"] = getattr(a, name)()
    for name in ("rollup", "rollup_rate"):
        for result in ("min", "max", "avg"):
            vm[name + "_" + result] = getattr(a, name)("5m", result=result)
    for name in ("any", "median", "mode", "mad"):
        vm[name] = getattr(a, name)().by("job")
        vm[name + "_without"] = getattr(a, name)().without("instance")
    for name, query in vm.items():
        yield name, query, "metricsql"


def experimental_cases():
    a = Q.from_metric("a")
    for name, query in {
        "sort_by_label": a.sort_by_label("job", "instance"),
        "sort_by_label_desc": a.sort_by_label_desc("job"),
        "mad_over_time": a.mad_over_time("5m"),
        "double_exponential_smoothing": a.double_exponential_smoothing("5m"),
        "limitk": a.limitk(3).without("instance"),
        "limit_ratio": a.limit_ratio(0.3).by("job"),
        "info": a.info(),
        "info_selector": a.info(Q.from_labels(job="api")),
        "ts_of_max_over_time": a.ts_of_max_over_time("5m"),
        "ts_of_min_over_time": a.ts_of_min_over_time("5m"),
        "ts_of_last_over_time": a.ts_of_last_over_time("5m"),
    }.items():
        yield "experimental_" + name, query, "promql"
