from metricraft._legacy.visitor import PositionTrackingVisitor
from metricraft._legacy.tree import NumberLiteral


def test_position_tracking_none_and_default_and_float_number():
    v = PositionTrackingVisitor()
    # None branch
    assert v.visit(None) == ""

    # Float number branch (not equal to int)
    out = v.visit(NumberLiteral(1.5))
    assert out == "1.5"

    # Default else branch with unknown node_type
    class Weird:
        node_type = object()
        def __str__(self):
            return "WZ"
    s = v.visit(Weird())
    assert s == "WZ"
