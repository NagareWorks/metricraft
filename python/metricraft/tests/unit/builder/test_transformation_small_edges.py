import pytest

from metricraft import QueryBuilder


def test_parenthesize_without_expr_raises():
    from metricraft._legacy.builder.impl.base import MetricsBuilder
    with pytest.raises(Exception):
        MetricsBuilder().parenthesize()  # type: ignore[attr-defined]


def test_sort_invalid_direction():
    b = QueryBuilder.from_metric("m")
    with pytest.raises(Exception):
        b.sort("zzz")


def test_label_set_requires_labels_and_expression():
    from metricraft._legacy.builder.impl.base import MetricsBuilder
    with pytest.raises(Exception):
        MetricsBuilder().label_set()  # type: ignore[attr-defined]

    b = QueryBuilder.from_metric("m")
    assert b.label_set().build() == "label_set(m)"


def test_subquery_parameter_validation():
    b = QueryBuilder.from_metric("m")
    with pytest.raises(Exception):
        b.subquery("").build("promql")
    with pytest.raises(Exception):
        b.subquery("5m", " ")


def test_moving_average_requires_expression():
    from metricraft._legacy.builder.impl.base import MetricsBuilder
    with pytest.raises(Exception):
        MetricsBuilder().moving_average("5m")  # type: ignore[attr-defined]


def test_smooth_exponential_factor_range():
    b = QueryBuilder.from_metric("m")
    with pytest.raises(Exception):
        b.smooth_exponential(-0.1)
    with pytest.raises(Exception):
        b.smooth_exponential(1.1)


def test_union_accepts_a_single_source():
    b = QueryBuilder.from_metric("m")
    assert b.union().build() == "union(m)"
