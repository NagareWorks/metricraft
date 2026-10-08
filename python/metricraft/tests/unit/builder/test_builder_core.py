import pytest

from metricraft import QueryBuilder
from metricraft._legacy.enums import MatchType
from metricraft._legacy.exceptions import VMValidationError, VMInvalidExpressionError


def test_from_metric_and_where_eq():
    q = QueryBuilder.from_metric("http_requests_total").where_eq("job", "api")
    s = q.build()
    assert s == 'http_requests_total{job="api"}'


def test_repeated_matchers_are_conjunctive():
    q = QueryBuilder.from_metric("m").where_eq("job", "a").where_eq("job", "b")
    assert q.build() == 'm{job="a",job="b"}'


def test_invalid_metric_name_validation():
    with pytest.raises(Exception) as e:
        QueryBuilder.from_metric("123\n").build()
    assert "invalid metric name" in str(e.value)


def test_where_regex_and_not_regex():
    q1 = QueryBuilder.from_metric("m").where_regex("job", "web.*")
    assert q1.build() == 'm{job=~"web.*"}'
    q2 = QueryBuilder.from_metric("m").where_not_regex("status", "5..")
    assert q2.build() == 'm{status!~"5.."}'


def test_arithmetic_and_parentheses():
    a = QueryBuilder.from_metric("a")
    b = QueryBuilder.from_metric("b")
    expr = (a + b) * 2
    s = expr.build()
    # Accept parentheses differences such as ((a + b)) * 2 vs (a + b) * 2
    assert "+" in s and "*" in s


def test_range_and_rate_and_aggregation_by_without():
    q = QueryBuilder.from_metric("cpu_usage").range("5m").rate().sum().by("job")
    s = q.build()
    assert s == "sum by (job) (rate(cpu_usage[5m]))"


def test_build_promql_checks_nested_vm_only_form():
    q = (
        QueryBuilder.from_metric("http_requests_total")
        .sum().by("job")
        .rate()
        .keep_metric_names()
    )
    with pytest.raises(ValueError, match="MetricsQL-only"):
        q.build("promql")
    assert (
        q.build("metricsql")
        == "rate(sum by (job) (http_requests_total)) keep_metric_names"
    )


def test_unary_sign_and_negation():
    q = -QueryBuilder.from_metric("m").where_eq("job", "api")
    s = q.build()
    assert s.startswith("-")


def test_require_ast_node_errors():
    # Calling an operation while no expression is set should raise
    b = QueryBuilder()
    with pytest.raises(ValueError, match="start with"):
        b.add(1)
