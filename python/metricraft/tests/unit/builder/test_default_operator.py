"""Tests for the default operator (MetricsQL extension)."""

import pytest

from metricraft import QueryBuilder


def test_default_with_numeric_value():
    """Test default operator with a numeric value."""
    builder = QueryBuilder.from_metric("cpu_usage").default(0)
    query = builder.build()
    assert "default" in query
    assert query == "(cpu_usage default 0)"


def test_default_with_float_value():
    """Test default operator with a float value."""
    builder = QueryBuilder.from_metric("response_time").default(100.5)
    query = builder.build()
    assert "default" in query
    assert query == "(response_time default 100.5)"


def test_default_with_builder_expression():
    """Test default operator with another builder expression."""
    metric_a = QueryBuilder.from_metric("metric_a")
    metric_b = QueryBuilder.from_metric("metric_b")
    builder = metric_a.default(metric_b)
    query = builder.build()
    assert "default" in query
    assert query == "(metric_a default metric_b)"


def test_default_chained_operations():
    """Test default operator in a chain of operations."""
    builder = (
        QueryBuilder.from_metric("cpu_usage").rate("5m").default(0).sum().by("instance")
    )
    query = builder.build()
    assert "default" in query
    assert "rate" in query
    assert "sum" in query


def test_default_with_complex_expression():
    """Test default with a more complex expression."""
    builder = (
        QueryBuilder.from_metric("http_requests_total").rate("5m").gt(0.5).default(0)
    )
    query = builder.build()
    assert "default" in query
    assert query.count("default") == 1


def test_default_returns_the_same_immutable_builder_type():
    """Dialect extensions do not create a second builder family."""
    builder = QueryBuilder.from_metric("test_metric").default(0)
    assert type(builder) is QueryBuilder


def test_default_without_expression_raises():
    """Test that calling default without base expression raises error."""
    from metricraft._legacy.builder.impl.base import MetricsBuilder

    with pytest.raises(Exception):
        MetricsBuilder().default(0)  # type: ignore[attr-defined]


def test_default_promql_validation_fails():
    """Test that default operator fails PromQL validation."""
    builder = QueryBuilder.from_metric("cpu_usage").default(0)
    with pytest.raises(ValueError, match="MetricsQL-only"):
        builder.build("promql")


def test_default_metricsql_build_passes():
    builder = QueryBuilder.from_metric("cpu_usage").default(0)
    assert builder.build("metricsql") == "(cpu_usage default 0)"


def test_default_with_zero():
    """Test common use case: filling gaps with zero."""
    builder = QueryBuilder.from_metric("error_count").default(0)
    query = builder.build()
    assert query == "(error_count default 0)"


def test_default_with_negative_value():
    """Test default with negative value."""
    builder = QueryBuilder.from_metric("temperature").default(-999)
    query = builder.build()
    assert query == "(temperature default -999)"


def test_default_multiple_in_binary_operation():
    """Test using default on both sides of a binary operation."""
    left = QueryBuilder.from_metric("metric_a").default(0)
    right = QueryBuilder.from_metric("metric_b").default(1)
    builder = left.add(right)
    query = builder.build()
    assert query.count("default") == 2


def test_default_with_aggregation_before():
    """Test default applied after an aggregation."""
    builder = QueryBuilder.from_metric("http_requests").sum().by("job").default(0)
    query = builder.build()
    assert "sum" in query
    assert "default" in query


def test_default_preserves_labels():
    """Test that default preserves label selectors."""
    builder = (
        QueryBuilder.from_metric("cpu_usage")
        .where_eq("instance", "localhost")
        .default(0)
    )
    query = builder.build()
    assert 'instance="localhost"' in query
    assert "default" in query
