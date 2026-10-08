import pytest

from metricraft._legacy.visitor.base import BaseVisitor
from metricraft._legacy.visitor import get_query_visitor
from metricraft._legacy.builder.mixins import FactoryMixin


def test_visitor_base_default_visit_raises():
    class DummyVisitor(BaseVisitor):
        def visit(self, node):
            return self.default_visit(node)
    v = DummyVisitor()
    with pytest.raises(NotImplementedError):
    # Pass any node to trigger default_visit
        v.visit(FactoryMixin.from_metric('m').ast_node)


def test_codegen_smoke_for_common_paths():
    v = get_query_visitor()
    # Simple instant vector
    s1 = v.visit(FactoryMixin.from_metric('cpu').ast_node)
    assert isinstance(s1, str) and 'cpu' in s1
    # With label
    s2 = v.visit(FactoryMixin.from_metric('cpu').where_eq('job','api').ast_node)
    assert 'job' in s2
    # Smoke test visiting logical/aggregation/function/unary combinations
    expr = (
        FactoryMixin.from_metric('a').or_(FactoryMixin.from_metric('b'))
        .sum(by=['job']).timestamp().negative()
    )
    s3 = v.visit(expr.ast_node)
    assert isinstance(s3, str) and s3
