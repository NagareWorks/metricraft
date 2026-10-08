import pytest

from metricraft._legacy.builder.mixins import FactoryMixin
from metricraft._legacy.tree.nodes.types import NodeType
from metricraft._legacy.exceptions import VMInvalidExpressionError
from metricraft._legacy.exceptions import RangeVectorError


def test_range_raises_when_no_ast():
    b = FactoryMixin.from_metric('m')
    # simulate no AST expression
    b._ast_node = None
    with pytest.raises(VMInvalidExpressionError):
        b.range('5m')


def test_quantile_over_time_raises_when_no_ast_and_bounds():
    b = FactoryMixin.from_metric('m')
    # clear AST to hit InvalidExpressionError path
    b._ast_node = None
    with pytest.raises(VMInvalidExpressionError):
        b.quantile_over_time(0.5, '5m')

    # restore and hit bounds (covered elsewhere, but sanity here)
    b2 = FactoryMixin.from_metric('m')
    with pytest.raises(Exception):
        b2.quantile_over_time(-0.1, '5m')
    with pytest.raises(Exception):
        b2.quantile_over_time(1.1, '5m')


def test_predict_linear_raises_when_no_ast_and_range_vector_error(monkeypatch):
    b = FactoryMixin.from_metric('m')
    # clear AST to hit InvalidExpressionError path
    b._ast_node = None
    with pytest.raises(VMInvalidExpressionError):
        b.predict_linear(60, '5m')

    # Force RangeVectorError by monkeypatching range() to return an object without _ast_node
    b2 = FactoryMixin.from_metric('m')

    class Dummy:
        _ast_node = None
    
    monkeypatch.setattr(b2, 'range', lambda d: Dummy())
    with pytest.raises(RangeVectorError):
        b2.predict_linear(60, '5m')


def test_holt_winters_raises_when_no_ast_and_range_vector_error(monkeypatch):
    b = FactoryMixin.from_metric('m')
    b._ast_node = None
    with pytest.raises(VMInvalidExpressionError):
        b.holt_winters('5m', 0.3, 0.3)

    b2 = FactoryMixin.from_metric('m')

    class Dummy:
        _ast_node = None
    
    monkeypatch.setattr(b2, 'range', lambda d: Dummy())
    with pytest.raises(RangeVectorError):
        b2.holt_winters('5m', 0.3, 0.3)


def test_range_on_existing_range_applies_sign_to_inner_expr():
    # Build a range, then apply sign and range again to hit NodeType.RANGE_EXPR branch
    base = FactoryMixin.from_metric('cpu')
    r1 = base.range('1m')
    r2 = (-r1).range('5m')
    assert r2.ast_node is not None
    assert r2.ast_node.node_type is NodeType.RANGE_EXPR
    # inner expr should be wrapped by unary when sign was present (covered by earlier tests),
    # here we only assert shape
    assert hasattr(r2.ast_node, 'expr') and r2.ast_node.expr is not None
