from metricraft._legacy.exceptions import VMPositionalError
from metricraft._legacy.tree import MetricSelector, LabelMatcher
from metricraft._legacy.enums import MatchType
from metricraft._legacy.tree.nodes.literals import StringLiteral


def test_calculate_absolute_position_for_label_value():
    # Root selector with label matcher
    root = MetricSelector("m", [LabelMatcher("job", MatchType.EQUAL, "api")])
    # Error crafted for label value of 'job'
    err = VMPositionalError("invalid label value for 'job'", ast_node=StringLiteral("api"), root_node=root)
    pos = err.calculate_absolute_position()
    query = 'm{job="api"}'
    # Compute expected indices
    start = query.index('job="') + len('job="')
    end = query.index('"', start)
    assert pos == (start, end)
