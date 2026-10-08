import pytest

from metricraft._legacy.builder.impl.base import MetricsBuilder
from metricraft._legacy.visitor.code_gen import QueryToStringVisitor


def test_query_string_raises_when_no_expression():
    b = MetricsBuilder()
    with pytest.raises(ValueError):
        _ = b._query_string


def test_build_with_custom_visitor_requires_expression():
    b = MetricsBuilder()
    # Passing a real visitor should trigger the explicit ValueError path when ast is None
    with pytest.raises(ValueError):
        b.build(validate=False, visitor=QueryToStringVisitor())


def test_require_ast_node_attaches_context():
    b = MetricsBuilder()
    # Simulate partial query capture
    b._last_query_attempt = "m{}"  # type: ignore[attr-defined]
    with pytest.raises(Exception):
        b._require_ast_node("op")


def test_native_builder_rejects_python_visitor_override():
    from metricraft import QueryBuilder

    query = QueryBuilder.from_metric("m")
    with pytest.raises(TypeError, match="visitor"):
        query.build(visitor=QueryToStringVisitor())
    assert query.build() == "m"
