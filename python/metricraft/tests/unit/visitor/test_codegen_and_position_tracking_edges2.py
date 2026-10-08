from metricraft._legacy.visitor import QueryToStringVisitor, PositionTrackingVisitor
from metricraft._legacy.tree import NumberLiteral
from metricraft._legacy.tree.nodes.selectors import LabelMatcher, MetricSelector
from metricraft._legacy.enums.operators import MatchType, BinaryOperator
from metricraft._legacy.tree.nodes.expressions import AggregationExpr, BinaryExpr
from metricraft._legacy.enums import AggregationOperator


def test_query_to_string_dispatch_and_label_escape_and_none():
    v = QueryToStringVisitor()
    # None branch
    assert v.visit(None) == ""

    # Label matcher escaping: backslash, quote, newline, tab, carriage return
    lm = LabelMatcher("a", MatchType.EQUAL, '\\\"x\n\t\r')
    ms = MetricSelector("m", [lm])
    s = v.visit(ms)
    # Expect escaped sequences in the value
    assert 'a="\\\\\\\"x\\n\\t\\r"' in s


def test_function_call_fallback_exception_path():
    class Tricky:
        # Has an 'accept' attribute that is NOT callable; this triggers exception path
        accept = True
        def __str__(self) -> str:
            return "T"

    from metricraft._legacy.tree.nodes.expressions import FunctionCall
    v = QueryToStringVisitor()
    out = v.visit(FunctionCall("f", [Tricky()]))
    assert out == "f(T)"


def test_position_tracking_binary_and_aggregation_maps():
    left = MetricSelector("m1", [])
    right = MetricSelector("m2", [])
    bin_expr = BinaryExpr(left, BinaryOperator.MUL, right)

    agg = AggregationExpr(AggregationOperator.SUM, left).by("job")

    pt = PositionTrackingVisitor()
    pos_map_bin = pt.build_position_map(bin_expr)
    assert id(left) in pos_map_bin and id(right) in pos_map_bin and id(bin_expr) in pos_map_bin

    pos_map_agg = pt.build_position_map(agg)
    assert id(agg) in pos_map_agg and id(agg.expr) in pos_map_agg

    # Also ensure number literal is handled
    pt2 = PositionTrackingVisitor()
    n = NumberLiteral(10.0)
    s = pt2.visit(n)
    assert s == "10" and id(n) in pt2.position_map
