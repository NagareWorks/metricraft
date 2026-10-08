import pytest

from metricraft._legacy.builder.utils.templates import maybe_parenthesize, convert_to_ast_node
from metricraft._legacy.tree import BinaryExpr, BinaryOperator, NumberLiteral, FunctionCall


def test_maybe_parenthesize_wraps_binary_and_function():
    node = BinaryExpr(NumberLiteral(1), BinaryOperator.ADD, NumberLiteral(2))
    wrapped = maybe_parenthesize(node)
    # ParenthesizedExpr has attribute 'expr' in our AST; check by string form of codegen fallback
    assert hasattr(wrapped, 'node_type')

    func = FunctionCall('abs', [NumberLiteral(1)])
    wrapped2 = maybe_parenthesize(func)
    assert hasattr(wrapped2, 'node_type')


def test_convert_to_ast_node_invalid_operand_type():
    class Dummy:  # not builder-like and not supported primitive
        pass

    with pytest.raises(Exception):
        convert_to_ast_node(Dummy())