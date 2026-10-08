import pytest

from metricraft._legacy.builder.mixins import FactoryMixin
from metricraft._legacy.builder.utils import templates as T
from metricraft._legacy.exceptions import InvalidParameterError


def test_maybe_parenthesize_rules():
    a = FactoryMixin.from_metric('a')
    b = FactoryMixin.from_metric('b')

    # AND/OR/UNLESS should be parenthesized
    and_expr = (a & b).ast_node
    wrapped = T.maybe_parenthesize(and_expr)
    assert wrapped.__class__.__name__ == 'ParenthesizedExpr'

    # Non-logical BinaryExpr also parenthesized
    add_expr = (a + 1).ast_node
    assert T.maybe_parenthesize(add_expr).__class__.__name__ == 'ParenthesizedExpr'

    # AggregationExpr and FunctionCall parenthesized
    agg = a.sum().ast_node
    assert T.maybe_parenthesize(agg).__class__.__name__ == 'ParenthesizedExpr'
    func = a.clamp_min(1).ast_node
    assert T.maybe_parenthesize(func).__class__.__name__ == 'ParenthesizedExpr'


def test_convert_to_ast_node_and_require_ast_errors():
    a = FactoryMixin.from_metric('a')
    # convert builder-like with missing ast should raise
    dummy = FactoryMixin.from_metric('x')
    dummy._ast_node = None  # simulate builder without expression
    with pytest.raises(InvalidParameterError):
        T.convert_to_ast_node(dummy)

    # numeric and string convert
    assert T.convert_to_ast_node(5).__class__.__name__ == 'NumberLiteral'
    assert T.convert_to_ast_node('m').__class__.__name__ == 'MetricSelector'

    # require_ast_node should raise InvalidExpressionError when no expression
    b = FactoryMixin.from_metric('b')
    b._last_query_attempt = 'b'
    b._ast_node = None
    with pytest.raises(Exception) as ei:
        T.require_ast_node(b, 'op')
    assert 'op' in str(ei.value)


def test_create_function_helpers_and_arg_bounds():
    a = FactoryMixin.from_metric('a')
    # create_unary_function
    _ = T.create_unary_function(a, 'vector')

    # create_function_with_args min/max bounds
    with pytest.raises(InvalidParameterError):
        T.create_function_with_args(a, 'f', [], min_args=1)
    with pytest.raises(InvalidParameterError):
        T.create_function_with_args(a, 'f', [1,2,3], max_args=2)

    # create_label_function type guard
    with pytest.raises(InvalidParameterError):
        T.create_label_function(a, 'label_join', 123)  # non-string arg


def test_create_aggregation_function_param_rules():
    a = FactoryMixin.from_metric('a')

    # by and without together should raise
    with pytest.raises(Exception):
        T.create_aggregation_function(a, 'sum', by=['x'], without=['y'])

    # valid grouping labels should pass
    _ = T.create_aggregation_function(a, 'sum', by=['x'])

    # topk/bottomk bounds and quantile range
    with pytest.raises(InvalidParameterError):
        T.create_aggregation_function(a, 'topk', param=0)
    with pytest.raises(InvalidParameterError):
        T.create_aggregation_function(a, 'quantile', param=2.0)

    # accept string/number/builder param
    _ = T.create_aggregation_function(a, 'topk', param=3)
    _ = T.create_aggregation_function(a, 'count_values', param='ver')
    _ = T.create_aggregation_function(a, 'sum', param=a)


def test_create_range_and_simple_over_time_errors_and_happy():
    a = FactoryMixin.from_metric('a')

    # happy paths
    _ = T.create_simple_over_time_function(a, 'avg_over_time', '1m')
    _ = T.create_range_vector_function(a, 'predict_linear', '5m', extra_args=[60])

    # invalid extra arg type
    class Dummy:
        pass
    with pytest.raises(InvalidParameterError):
        T.create_range_vector_function(a, 'predict_linear', '5m', extra_args=[Dummy()])


def test_convert_to_ast_node_unsupported_type():
    """Test convert_to_ast_node with unsupported operand type."""
    with pytest.raises(InvalidParameterError, match="operand"):
        T.convert_to_ast_node([1, 2, 3])  # list is not supported


def test_require_ast_node_with_last_query_attempt():
    """Test require_ast_node error handling with _last_query_attempt."""
    b = FactoryMixin.from_metric('test')
    b._ast_node = None
    b._last_query_attempt = 'test_metric{label="value"}'
    
    with pytest.raises(Exception):
        T.require_ast_node(b, 'test_operation')


def test_create_aggregation_function_param_builder_without_ast():
    """Test aggregation function with builder param that has no AST node."""
    a = FactoryMixin.from_metric('a')
    b = FactoryMixin.from_metric('b')
    b._ast_node = None
    
    with pytest.raises(InvalidParameterError, match="param"):
        T.create_aggregation_function(a, 'sum', param=b)


def test_create_aggregation_function_param_unsupported_type():
    """Test aggregation function with unsupported param type."""
    a = FactoryMixin.from_metric('a')
    
    with pytest.raises(InvalidParameterError, match="param"):
        T.create_aggregation_function(a, 'sum', param=[1, 2, 3])


def test_create_range_vector_function_with_builder_arg():
    """Test create_range_vector_function with QueryBuilder as extra arg."""
    a = FactoryMixin.from_metric('a')
    b = FactoryMixin.from_metric('b')
    
    # Should work with builder as extra arg
    result = T.create_range_vector_function(a, 'predict_linear', '5m', extra_args=[b, 60])
    assert result is not None


def test_create_range_vector_function_with_string_arg():
    """Test create_range_vector_function with string as extra arg."""
    a = FactoryMixin.from_metric('a')
    
    # Should work with string as extra arg
    result = T.create_range_vector_function(a, 'predict_linear', '5m', extra_args=["label", 60])
    assert result is not None


def test_create_range_vector_function_with_ast_node_arg():
    """Test create_range_vector_function with VMASTNode as extra arg."""
    from metricraft._legacy.tree.nodes.literals import NumberLiteral
    
    a = FactoryMixin.from_metric('a')
    node = NumberLiteral(42.0)
    
    # Should work with AST node as extra arg
    result = T.create_range_vector_function(a, 'predict_linear', '5m', extra_args=[node])
    assert result is not None


def test_create_range_vector_function_with_builder_no_ast():
    """Test create_range_vector_function with builder that has no AST."""
    a = FactoryMixin.from_metric('a')
    b = FactoryMixin.from_metric('b')
    b._ast_node = None
    
    with pytest.raises(InvalidParameterError, match="arg"):
        T.create_range_vector_function(a, 'predict_linear', '5m', extra_args=[b])
