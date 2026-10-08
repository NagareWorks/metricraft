"""Architecture contracts across the Python / native boundary."""

import copy
import gc
from concurrent.futures import ThreadPoolExecutor

import pytest
from metricraft import QueryBuilder as Q, QueryMode


def test_public_exports_and_config_free_factory():
    from metricraft.builder import QueryBuilder as BuilderExport
    from metricraft.builder.query_builder import QueryBuilder as ModuleExport

    assert Q is BuilderExport is ModuleExport
    assert Q.__module__ == "metricraft.builder.query_builder"
    expression = Q.from_metric("up")
    assert not hasattr(expression, "__dict__")
    assert all(base.__dict__.get("__slots__") == () for base in Q.__bases__[:-1])
    assert Q().from_metric("up").build() == "up"
    with pytest.raises(ValueError, match="start with"):
        Q().build()


def test_empty_grouping_is_not_discarded():
    query = Q.from_metric("up").sum()
    assert query.without().build() == "sum without () (up)"
    assert query.by().build() == "sum by () (up)"


def test_vm_default_scalar_and_unary_sign():
    query = Q.from_metric("up").default(0)
    assert query.build() == "(up default 0)"
    with pytest.raises(ValueError, match="MetricsQL-only"):
        query.build("promql")
    assert (-Q.from_metric("up")).build("promql") == "-(up)"


def test_shared_base_and_grouping_are_immutable():
    base = Q.from_metric("requests_total")
    derived = base.rate("5m").sum()
    filtered = base.where_eq("job", "api")
    grouped = derived.by("job")
    assert base.build() == "requests_total"
    assert filtered.build() == 'requests_total{job="api"}'
    assert derived.build() == "sum (rate(requests_total[5m]))"
    assert grouped.build() == "sum by (job) (rate(requests_total[5m]))"
    assert copy.deepcopy(base) is base
    with pytest.raises(AttributeError):
        base._handle = 1
    with pytest.raises(AttributeError):
        base.__init__()


def test_children_survive_python_owner_collection():
    child = Q.from_metric("requests_total")
    result = child.rate("5m").sum().by("job")
    del child
    gc.collect()
    assert result.build("promql") == "sum by (job) (rate(requests_total[5m]))"


def test_nested_vm_only_rejected_and_failure_does_not_mutate():
    query = Q.from_metric("a").default(Q.from_metric("b")).sum()
    assert Q.default.vm_only
    assert Q.keep_metric_names.vm_only
    with pytest.raises(ValueError, match="MetricsQL-only"):
        query.build(QueryMode.PROMQL)
    assert query.build(QueryMode.METRICSQL) == "sum ((a default b))"
    with pytest.raises(ValueError):
        query.build("sql")


def test_literal_data_is_escaped_and_not_reinterpreted():
    value = 'x"} or up{job="a\\b\n'
    text = Q.from_metric("up").where_eq("job", value).build()
    assert text == 'up{job="x\\"} or up{job=\\"a\\\\b\\n"}'
    assert Q.from_string('a"b').build() == '"a\\"b"'
    assert (Q.from_scalar(2) + 3).build() == "(2 + 3)"


@pytest.mark.parametrize(
    "make",
    [
        lambda: Q.from_metric("up\n"),
        lambda: Q.from_metric("up").where_eq("job\n", "x"),
        lambda: Q.from_metric("up").range("5m]) or up"),
        lambda: Q.from_metric("up").range("0m"),
        lambda: Q.from_metric("up").rate().build("promql"),
        lambda: Q.from_scalar(1).sum().build("promql"),
        lambda: Q.from_metric("up").sum().by("job", "job"),
        lambda: Q.from_metric("up").where_eq("job", "a\x00b"),
        lambda: Q.from_string("one").sum(),
    ],
)
def test_invalid_structure_is_rejected(make):
    with pytest.raises(ValueError):
        make()


def test_shared_expression_can_build_concurrently():
    base = Q.from_metric("up")
    with ThreadPoolExecutor(max_workers=4) as executor:
        texts = list(
            executor.map(
                lambda i: base.where_eq("job", str(i)).build("promql"), range(40)
            )
        )
    assert len(set(texts)) == 40
    assert base.build() == "up"
