import pytest

from metricraft import QueryBuilder
from metricraft._legacy.enums import MatchType
from metricraft._legacy.builder.impl.instant_vector import InstantVectorBuilder
from metricraft._legacy.tree import NumberLiteral


def test_metric_is_selected_at_construction_and_filters_can_be_reused_purely():
    def select(name, matchers):
        query = QueryBuilder.from_metric(name)
        for label, value in matchers:
            query = query.where_eq(label, value)
        return query

    matchers = (("job", "api"),)
    first = select("http_requests_total", matchers)
    second = select("http_requests_rate", matchers)
    assert first.build() == 'http_requests_total{job="api"}'
    assert second.build() == 'http_requests_rate{job="api"}'
    assert not hasattr(first, "metric")
    assert matchers == (("job", "api"),)


def test_where_invalid_operator():
    b = QueryBuilder.from_metric("m")
    with pytest.raises(ValueError):
        b.where("job", "~=", "api")


def test_instant_vector_init_rejects_non_selector():
    with pytest.raises(TypeError):
        InstantVectorBuilder(ast_node=NumberLiteral(1))


def test_where_validation_error_context_mapping():
    # Invalid label name pattern should fail validation and go through error-context mapping
    b = QueryBuilder.from_metric("m")
    with pytest.raises(Exception):
        b.where("bad\nlabel", "=", "x")


def test_where_without_base_expression():
    """Test that where() raises ValueError when no base expression exists."""
    builder = InstantVectorBuilder(ast_node=None)
    with pytest.raises(
        ValueError, match="Cannot add label filter without a base expression"
    ):
        builder.where("label", "=", "value")


def test_metric_without_existing_node():
    """Test metric() method when no existing AST node."""
    builder = InstantVectorBuilder(ast_node=None)
    new_builder = builder.metric("new_metric")
    result = new_builder.build(validate=False)
    assert result == "new_metric"
