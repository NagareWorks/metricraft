"""Structured syntax witnesses for the pinned stable upstream parsers."""
from metricraft import QueryBuilder as Q

FEATURES = (
    "promql-duration-expr", "promql-extended-range-selectors",
    "promql-binop-fill-modifiers",
)


def cases():
    a, b = Q.from_metric("a"), Q.from_metric("b")
    common = {
        "utf8_names": Q.from_metric('温度"metric').where_eq("x-y", 'a"} or up'),
        "quoted_group": a.sum().by("x-y"),
        "quoted_matching": (a / b).on("x-y").group_left("*"),
        "nonfinite_positive": Q.from_scalar(float("inf")).vector(),
        "nonfinite_negative": Q.from_scalar(float("-inf")).vector(),
        "nonfinite_nan": Q.from_scalar(float("nan")).vector(),
        "numeric_suffix": Q.from_numeric_literal("1_000Mi").vector(),
        "duration_literal": (Q.from_duration("1h30m") + 5).vector(),
        "unitless_range": a.range("300").rate(),
        "zero_offset": a.offset("0s"),
        "re2_literal": Q.from_labels().where_regex("job", r"\Qapi.+\E"),
        "reserved_metric": Q.from_metric("NaN").where_eq("job", "api"),
    }
    for name, q in common.items():
        for mode in ("promql", "metricsql"):
            yield name, q, mode
    prom = {
        "duration_expression": a.range(Q.step().max_of(60) * 2).rate(),
        "duration_subquery": a.subquery(Q.query_range().max_of(300), Q.step().max_of(60) * 2).avg_over_time(),
        "duration_offset": a.offset(Q.step() * 2),
        "anchored": a.range("5m").anchored().rate(),
        "smoothed": a.range("5m").smoothed().rate(),
        "smoothed_instant": a.smoothed(),
        "fill": (a + b).on("job").fill(0),
        "fill_sides": (a / b).fill_left(0).fill_right(1),
        "histogram_trim_lower": a.trim_lower(0.1),
        "histogram_trim_upper": a.trim_upper(10),
        "histogram_quantiles_portable": a.histogram_quantiles("phi", 0.5, 0.9),
    }
    for name, q in prom.items():
        yield name, q, "promql"
    x = Q.reference("x")
    prefix = Q.reference("prefix", kind="string")
    vm = {
        "empty_selector": Q.from_labels(),
        "selector_or": a.where_eq("job", "api").or_selector(b.where_eq("job", "worker")),
        "selector_or_common_filter": a.or_selector(b).where_eq("job", "api"),
        "selector_or_nested_filter": a.or_selector(b).where_eq("job", "api").or_selector(a).where_eq("env", "prod"),
        "fractional_range": a.range("1.5m").rate(),
        "step_range": a.range("5i").rate(),
        "fractional_subquery": a.subquery("1.5h", "2i").avg_over_time(),
        "repeated_duration": a.range("1h5h").rate(),
        "duration_step_scalar": Q.from_duration("2i").vector(),
        "at_expression": a.at(Q.end() - 120),
        "aggregate_offset": a.sum().offset("1h"),
        "aggregate_limit": a.sum().by("job").limit(10),
        "group_wildcard": (a / b).on("job").group_left_all(),
        "group_prefix": (a / b).on("job").group_right_all(prefix='x"'),
        "tuple_equal": a.eq_any(1, 2, 3),
        "tuple_not_equal": a.ne_all(1, 2, 3),
        "string_concat": Q.from_string("a") + 'b"',
        "with_value": (x + 2).with_(x=a),
        "with_ordered": (Q.reference("y") + x).with_(x=a, y=x * 2),
        "with_template": Q.template_call("f", a).with_(f=Q.template("x", body=x.rate("5m"))),
        "with_zero_arg": Q.template_call("f").with_(f=Q.template(body=a + 1)),
        "with_string": Q.from_labels().where_eq("__name__", prefix + "total").with_(prefix="http_"),
        "with_string_filter": a.where_eq("job", prefix + "api").where_ne("env", "test").with_(prefix="prod_"),
        "scalar_rollup": Q.from_scalar(1).rate(),
        "scalar_aggregate": Q.from_scalar(1).sum(),
        "scalar_set": Q.from_scalar(1).and_(2),
        "range_transform": a.range("5m").abs(),
        "range_binary": a.range("5m") + b,
        "range_unary": -a.range("5m"),
        "scalar_matching": (Q.from_scalar(1) + a).on(),
        "implicit_window_subquery": a.subquery(step="1m").avg_over_time(),
        "scalar_subquery": Q.from_scalar(1).subquery("5m", "1m").avg_over_time(),
        "graphite_selector": Q.from_labels(__graphite__="foo.*.bar"),
        "variadic_aggregate": a.avg(b),
        "histogram_bounds": a.histogram_quantile(0.9, bounds_label="bounds"),
        "with_label_argument": Q.function("label_keep", a, prefix).with_(prefix="job"),
        "histogram_quantiles_portable": a.histogram_quantiles("phi", 0.5, 0.9),
    }
    for name, q in vm.items():
        yield name, q, "metricsql"
