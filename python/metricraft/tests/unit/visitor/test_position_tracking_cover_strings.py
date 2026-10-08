from metricraft._legacy.visitor import PositionTrackingVisitor
from metricraft._legacy.tree import StringLiteral


def test_position_tracking_string_literal_and_map_entry():
    v = PositionTrackingVisitor()
    s = StringLiteral('abc')
    out = v.visit(s)
    assert out == '"abc"'
    assert id(s) in v.position_map and v.position_map[id(s)][1] - v.position_map[id(s)][0] == len(out)
