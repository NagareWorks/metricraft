"""Keep public builder signatures useful to downstream editors and checkers."""
import inspect

from metricraft import HttpClientOptions, MetricsInsertData, QueryBuilder


def test_public_builder_signatures_have_input_and_return_annotations():
    operators = {"__init__", "__add__", "__sub__", "__mul__", "__truediv__",
                 "__mod__", "__pow__", "__radd__", "__rsub__", "__rmul__",
                 "__rtruediv__", "__neg__", "__pos__", "__eq__", "__ne__",
                 "__lt__", "__le__", "__gt__", "__ge__", "__and__", "__or__"}
    missing = []
    for name, method in inspect.getmembers(QueryBuilder, callable):
        if name.startswith("_") and name not in operators:
            continue
        signature = inspect.signature(method)
        if signature.return_annotation is inspect.Signature.empty:
            missing.append(name + " return")
        for parameter in signature.parameters.values():
            if parameter.name not in ("self", "cls") and parameter.annotation is inspect.Parameter.empty:
                missing.append(name + "." + parameter.name)
    assert not missing, "Missing public annotations: " + ", ".join(missing)


def test_supported_call_forms_kept_by_the_typing_contract():
    Q = QueryBuilder
    base = Q.from_metric("up")
    assert base.validate("PromQL") == ""
    assert base.sum().limit(3.0).build() == "sum (up) limit 3"
    assert base.range("5m").holt_winters(None).build().startswith("holt_winters(up[5m]")
    assert base.range("5m").moving_average(None).build() == "avg_over_time(up[5m])"
    assert HttpClientOptions(timeout=5).timeout == (5.0, 5.0)
    times, values = [0, 1], [1.0, 2.0]
    assert MetricsInsertData("up", times, values).times is times
    assert MetricsInsertData("up", (0, 1), (1.0, 2.0)).values == (1.0, 2.0)
    assert base.rollup("5m", result=Q.from_string("min")).build() == 'rollup(up[5m], "min")'
    assert base.rollup("5m", func=Q.from_string("min")).build() == 'rollup(up[5m], "min")'
    assert base.rollup_rate("5m", result=Q.from_string("min")).build() == 'rollup_rate(up[5m], "min")'
    assert base.rollup_candlestick("5m", result=Q.from_string("open")).build().endswith(', "open")')
    assert base.aggr_over_time(Q.from_string("rate"), window="5m").build().startswith("aggr_over_time(")
    assert base.label_graphite_group(Q.from_scalar(1)).build() == "label_graphite_group(up, 1)"
    assert base.drop_common_labels(1).build() == "drop_common_labels(up, 1)"
    label = Q.reference("s", kind="string")
    expressions = (
        base.label_set(job=label), base.label_del(label), base.label_keep(label),
        base.label_lowercase(label), base.label_uppercase(label),
        base.label_map(label, ("api", "public")), base.label_match(label, "api"),
        base.label_mismatch(label, "api"), base.label_transform(label, "api", "public"),
        base.label_value(label), base.labels_equal(label, "instance"), base.alias(label),
        base.sort_by_label(label), base.sort_by_label_desc(label),
        base.sort_by_label_numeric(label), base.sort_by_label_numeric_desc(label),
        base.histogram_quantiles(label, 0.5), base.quantiles_over_time(label, 0.5, window="5m"),
    )
    for expression in expressions:
        assert expression.with_(s="job").build("metricsql").startswith('WITH (s = "job")')
