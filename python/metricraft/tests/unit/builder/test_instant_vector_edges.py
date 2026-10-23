import pytest

from metricraft import QueryBuilder


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


def test_where_validation_error_context_mapping():
    # Invalid label name pattern should fail validation and go through error-context mapping
    b = QueryBuilder.from_metric("m")
    with pytest.raises(Exception):
        b.where("bad\nlabel", "=", "x")
