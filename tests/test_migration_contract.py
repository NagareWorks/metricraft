"""Retained calling conventions exercised exclusively through the Rust builder."""
import copy
from datetime import datetime, timezone
import json
import operator
import ast
import importlib.util
from pathlib import Path

import pytest

from metricraft import QueryBuilder as Q


def test_every_historical_public_method_has_an_explicit_disposition():
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("migration_witnesses", root / "tests/conformance/migration.py")
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    old_names = set()
    for path in (root / "python/metricraft/src/metricraft/_legacy/builder").rglob("*.py"):
        if path.parent.name not in ("impl", "mixins"):
            continue
        for cls in ast.walk(ast.parse(path.read_text(encoding="utf-8-sig"))):
            if isinstance(cls, ast.ClassDef):
                for node in cls.body:
                    if isinstance(node, ast.FunctionDef) and (
                        not node.name.startswith("_") or node.name.startswith("__") and node.name != "__init__"
                    ):
                        old_names.add(node.name)
    expressions = migration.expression_cases()
    assert old_names == set(expressions) | migration.DIAGNOSTICS | set(migration.RETIRED)
    for name, query in expressions.items():
        assert query.build("metricsql"), name
    for name in migration.RETIRED:
        if name != "__getattribute__":
            assert not hasattr(Q, name)


@pytest.mark.parametrize("name,args", [
    (name, ()) for name in ("sum", "avg", "min", "max", "count", "stddev", "stdvar",
                            "group", "any", "median", "mode", "mad")
] + [(name, (3,)) for name in ("topk", "bottomk", "outliersk", "limitk")]
  + [("quantile", (0.5,)), ("count_values", ("value",))])
def test_aggregation_call_forms_and_immutable_grouping(name, args):
    base = Q.from_metric("up")
    method = getattr(base, name)
    aggregate = method(*args)
    query = aggregate.without("instance")
    assert " without (instance) " in query.build()
    assert " by (job) " in aggregate.by("job").build()
    assert " without (instance) " in query.build()
    assert " without () " in aggregate.without().build()
    with pytest.raises(TypeError, match="unexpected keyword"):
        method(*args, by=[], without=[])
    with pytest.raises(TypeError, match="unexpected keyword"):
        method(*args, without="instance")
    for grouped in (aggregate.by("job"), query, aggregate.by(), aggregate.without()):
        for grouping in ("by", "without"):
            with pytest.raises(ValueError, match="already has grouping"):
                getattr(grouped, grouping)("job")
    assert " by " not in aggregate.build() and " without " not in aggregate.build()
    assert base.build() == "up"


@pytest.mark.parametrize("name", [
    "rate", "irate", "increase", "delta", "idelta", "deriv", "changes", "resets",
    "sum_over_time", "avg_over_time", "min_over_time", "max_over_time", "count_over_time",
    "stddev_over_time", "stdvar_over_time", "last_over_time", "present_over_time",
    "mad_over_time", "median_over_time", "mode_over_time", "zscore_over_time", "rate_over_sum",
    "rollup_rate",
])
def test_duration_keyword_and_prebuilt_range(name):
    base = Q.from_metric("up")
    expected = name + "(up[10m])"
    assert getattr(base, name)(duration="10m").build() == expected
    assert getattr(base.range(duration="10m"), name)().build() == expected
    with pytest.raises(TypeError, match="either window or duration"):
        getattr(base, name)("5m", duration="10m")
    assert base.build() == "up"


def test_retained_convenience_signatures():
    a = Q.from_metric("up")
    assert a.range().build() == "up[5m]"
    assert a.sort("desc").build() == "sort_desc(up)"
    with pytest.raises(ValueError):
        a.sort("random")
    assert Q.from_scalar(2).vector().build() == Q.vector(value=2).build() == "vector(2)"
    assert a.round(to_nearest=0.5).build() == "round(up, 0.5)"
    assert a.predict_linear(prediction_seconds=60, duration="10m").build() == "predict_linear(up[10m], 60)"
    assert a.quantile_over_time(quantile=0.9, duration="10m").build() == "quantile_over_time(0.9, up[10m])"
    assert a.subquery(range_duration="10m", resolution="1m").build() == "(up)[10m:1m]"
    assert a.rollup("avg", "10m").build() == a.rollup(func="avg", duration="10m").build() == 'rollup(up[10m], "avg")'
    assert a.where_eq("job", None).build() == 'up{job=""}'
    assert a.positive().negative().parenthesize().build() == "(-(+(up)))"
    assert a.build() == "up"


@pytest.mark.parametrize("operation,symbol", [
    (operator.gt, ">"), (operator.ge, ">="), (operator.lt, "<"),
    (operator.le, "<="), (operator.eq, "=="), (operator.ne, "!="),
    (operator.and_, "and"), (operator.or_, "or"),
])
def test_operators_build_expressions_and_cannot_be_used_as_python_predicates(operation, symbol):
    a, b = Q.from_metric("a"), Q.from_metric("b")
    result = operation(a, b)
    assert result.build("promql") == "(a " + symbol + " b)"
    with pytest.raises(TypeError, match="truth value"):
        bool(result)
    assert copy.copy(result) is result
    assert copy.deepcopy(result) is result
    assert a.build() == "a"


def test_timestamp_inputs_are_deterministic_and_in_seconds():
    a = Q.from_metric("up")
    for value in (datetime(2025, 1, 1, tzinfo=timezone.utc), "2025-01-01T00:00:00Z", 1735689600):
        assert a.at(value).build("promql") == "up @ 1735689600"
    assert a.at("start()").build("promql") == "up @ start()"
    for value in ("2025-01-01", datetime(2025, 1, 1), "now()", "0) or up"):
        with pytest.raises(ValueError):
            a.at(value)


def test_diagnostics_preserve_shared_nodes_and_escape_data():
    a = Q.from_metric("up").where_eq("job", '中文"\\\n\u0001')
    branch = a.where_eq("env", "prod")
    query = a + branch
    graph = json.loads(query.to_debug_json())
    assert len(graph["nodes"]) == 3
    assert len(graph["matchers"]) == 2
    assert graph["matchers"][1]["previous"] == 0
    assert graph["matchers"][0]["value"] == '中文"\\\n\u0001'
    analysis = query.analyze()
    assert analysis["complexity"]["node_count"] == 3
    assert analysis["metrics"]["metric_names"] == ["up"]
    assert "nodes" not in analysis
    assert query.debug() == query.to_debug_json()
    assert a.build() == 'up{job="中文\\\"\\\\\\n\\u0001"}'


def test_diagnostics_remain_bounded_for_exponential_expansion():
    query = Q.from_metric("up")
    for _ in range(60):
        query = query + query
    assert query.analyze()["complexity"]["node_count"] == 61
    assert len(json.loads(query.to_debug_json())["nodes"]) == 61
    with pytest.raises(ValueError, match="max_output_bytes"):
        query.debug_positions()
    with pytest.raises(ValueError, match="max_items"):
        query.analyze(max_items=120)
    with pytest.raises(ValueError, match="max_output_bytes"):
        query.to_debug_json(max_output_bytes=20)
    assert query.analyze()["complexity"]["depth"] == 60


def test_positions_describe_exact_rendered_utf8_occurrences():
    a = Q.from_metric("up").where_eq("job", "中文")
    query = a + a
    report = json.loads(query.debug_positions(mode="promql"))
    encoded = report["source"].encode("utf-8")
    slices = [encoded[p["offset_bytes"]:p["offset_bytes"] + p["length_bytes"]].decode("utf-8")
              for p in report["positions"]]
    assert slices == [query.build(), a.build(), a.build()]
    assert query.visualize_positions(query.build()) == query.debug_positions()
    with pytest.raises(ValueError, match="source_code must equal"):
        query.visualize_positions("something else")
    with pytest.raises(ValueError, match="experimental_functions"):
        a.sort_by_label("job").debug_positions(mode="promql")
    assert a.sort_by_label("job").debug_positions(mode="promql", experimental_functions=True)


def test_native_validation_and_uninitialized_diagnostics():
    a = Q.from_metric("up")
    assert a.validate("PromQL") == ""
    assert "MetricsQL-only" in a.alias("renamed").validate("PromQL")
    with pytest.raises(ValueError, match="always enabled"):
        a.validate(strict=False)
    for method in ("debug", "analyze", "to_debug_json", "debug_positions", "validate"):
        with pytest.raises(ValueError, match="from_"):
            getattr(Q(), method)()
