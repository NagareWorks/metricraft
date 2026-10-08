from metricraft._legacy.tree import NumberLiteral, DurationLiteral
from metricraft._legacy.tree.nodes.selectors import MetricSelector
from metricraft._legacy.tree.nodes.expressions import BinaryExpr, UnaryExpr
from metricraft._legacy.tree.nodes.selectors import OffsetExpr, AtExpr
from metricraft._legacy.enums.operators import BinaryOperator, UnaryOperator
from metricraft._legacy.visitor import QueryToStringVisitor


def test_binary_group_left_and_chain_copy_semantics():
    a = MetricSelector("a", [])
    b = MetricSelector("b", [])
    expr = BinaryExpr(a, BinaryOperator.SUB, b)

    # group_left with labels when no modifier
    gl = expr.group_left("l1", "l2")
    s = QueryToStringVisitor().visit(gl)
    assert "group_left(l1, l2)" in s

    # Now add on() over existing modifier to check copy of group
    on_then = gl.on("x")
    s2 = QueryToStringVisitor().visit(on_then)
    assert "on (x)" in s2 and "group_left(l1, l2)" in s2


def test_offset_and_at_expr_string_and_number_timestamp():
    m = MetricSelector("m", [])
    off = OffsetExpr(m, DurationLiteral("5m"))
    s = QueryToStringVisitor().visit(off)
    assert s == "m offset 5m"

    at_str = AtExpr(m, "start()")
    s2 = QueryToStringVisitor().visit(at_str)
    assert s2.endswith(" @ start()")

    at_num = AtExpr(m, 1700000000)
    s3 = QueryToStringVisitor().visit(at_num)
    assert s3.endswith(" @ 1700000000")


def test_unary_plus_and_minus_codegen():
    up = UnaryExpr(UnaryOperator.PLUS, NumberLiteral(3))
    um = UnaryExpr(UnaryOperator.MINUS, NumberLiteral(4))
    v = QueryToStringVisitor()
    assert v.visit(up) == "+3"
    assert v.visit(um) == "-4"
