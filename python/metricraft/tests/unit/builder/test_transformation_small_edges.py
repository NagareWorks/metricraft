import pytest

from metricraft import QueryBuilder


def test_sort_invalid_direction():
    b = QueryBuilder.from_metric("m")
    with pytest.raises(Exception):
        b.sort("zzz")


def test_label_set_requires_labels_and_expression():
    with pytest.raises(Exception):
        QueryBuilder().label_set()

    b = QueryBuilder.from_metric("m")
    assert b.label_set().build() == "label_set(m)"


def test_subquery_parameter_validation():
    b = QueryBuilder.from_metric("m")
    with pytest.raises(Exception):
        b.subquery("").build("promql")
    with pytest.raises(Exception):
        b.subquery("5m", " ")


def test_smooth_exponential_factor_range():
    b = QueryBuilder.from_metric("m")
    with pytest.raises(Exception):
        b.smooth_exponential(-0.1)
    with pytest.raises(Exception):
        b.smooth_exponential(1.1)


def test_union_accepts_a_single_source():
    b = QueryBuilder.from_metric("m")
    assert b.union().build() == "union(m)"
