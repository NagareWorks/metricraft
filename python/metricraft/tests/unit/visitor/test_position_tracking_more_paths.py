from metricraft._legacy.tree import MetricSelector
from metricraft._legacy.tree.nodes.selectors import LabelMatcher
from metricraft._legacy.enums.operators import MatchType
from metricraft._legacy.visitor import PositionTrackingVisitor


def test_position_tracking_maps_child_string_literal():
    ms = MetricSelector("m", [LabelMatcher("a", MatchType.EQUAL, "b")])
    v = PositionTrackingVisitor()
    pos = v.build_position_map(ms)
    # Must contain both matcher and its inner value node id mapping
    lm = ms.label_matchers[0]
    assert id(ms) in pos and id(lm) in pos
    assert id(lm.value_node) in pos
