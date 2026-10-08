import pytest

from metricraft._legacy.builder.mixins import FactoryMixin
from metricraft._legacy.builder.impl.base import MetricsBuilder
from metricraft._legacy.builder.utils.templates import (
    convert_to_ast_node,
    create_binary_operation,
    create_reverse_binary_operation,
    create_unary_function,
    create_function_with_args,
    create_label_function,
    create_range_vector_function,
    create_simple_over_time_function,
    maybe_parenthesize,
)
from metricraft._legacy.tree import NumberLiteral, FunctionCall, AggregationExpr, ParenthesizedExpr, BinaryExpr
from metricraft._legacy.enums import BinaryOperator
from metricraft._legacy.exceptions import InvalidParameterError, AggregationError
from metricraft._legacy.exceptions import VMInvalidExpressionError


class DummyBuilder:
    def __init__(self, node=None):
        self._ast_node = node
        self.ast_node = node


def test_convert_to_ast_node_unsupported_and_builder_like_without_expr():
    with pytest.raises(InvalidParameterError):
        convert_to_ast_node(object())
    # builder-like without expression
    dummy = DummyBuilder(node=None)
    with pytest.raises(InvalidParameterError):
        convert_to_ast_node(dummy)


def test_create_function_with_args_min_max_enforced():
    b = FactoryMixin.from_metric('cpu')
    with pytest.raises(InvalidParameterError):
        create_function_with_args(b, 'union', [], min_args=1)
    with pytest.raises(InvalidParameterError):
        create_function_with_args(b, 'label_join', ['a','b','c'], min_args=0, max_args=2)


def test_create_label_function_invalid_arg_type():
    b = FactoryMixin.from_metric('cpu')
    with pytest.raises(InvalidParameterError):
        create_label_function(b, 'label_replace', 1)  # non-string arg


def test_create_range_vector_function_invalid_extra_arg_type():
    b = FactoryMixin.from_metric('cpu')
    with pytest.raises(InvalidParameterError):
        create_range_vector_function(b, 'rate', '5m', extra_args=[{'bad': 'type'}])


def test_create_unary_function_requires_node():
    empty = MetricsBuilder()
    with pytest.raises(VMInvalidExpressionError):
        create_unary_function(empty, 'timestamp')


def test_create_binary_and_reverse_operations_and_parenthesize_rules():
    b = FactoryMixin.from_metric('cpu')
    # + operation with number
    res = create_binary_operation(b, BinaryOperator.ADD, 1)
    assert isinstance(res.ast_node, BinaryExpr)
    # reverse op (number on left)
    res2 = create_reverse_binary_operation(b, BinaryOperator.SUB, 2)
    assert isinstance(res2.ast_node, BinaryExpr)

    # maybe_parenthesize rules
    n = NumberLiteral(1)
    assert maybe_parenthesize(n) is n
    # wrap BinaryExpr in parentheses
    wrapped = maybe_parenthesize(res.ast_node)
    assert isinstance(wrapped, ParenthesizedExpr)
    # wrap FunctionCall and AggregationExpr
    f = FunctionCall('time', [n])
    assert isinstance(maybe_parenthesize(f), ParenthesizedExpr)
    agg = AggregationExpr(operator=None, expr=n)  # type: ignore[arg-type]
    assert isinstance(maybe_parenthesize(agg), ParenthesizedExpr)


def test_aggregation_conflicting_by_without_raises():
    b = FactoryMixin.from_metric('cpu')
    with pytest.raises(AggregationError):
        b.sum(by=['a'], without=['b'])


def test_simple_over_time_helper_and_range_vector_creation():
    b = FactoryMixin.from_metric('cpu')
    # Should succeed and return a ProcessedVectorBuilder
    out = create_simple_over_time_function(b, 'avg_over_time', '2m')
    assert out.ast_node is not None
