from metricraft._legacy.visitor import PositionTrackingVisitor
from metricraft._legacy.tree.nodes.types import NodeType
from metricraft._legacy.enums.operators import MatchType


def test_position_tracking_label_matcher_without_value_node():
    class FakeLM:
        node_type = NodeType.LABEL_MATCHER
        def __init__(self):
            self.name = 'a'
            self.op = MatchType.EQUAL
            self.value = 'v'
    v = PositionTrackingVisitor()
    out = v.visit(FakeLM())
    assert out == 'a="v"'
