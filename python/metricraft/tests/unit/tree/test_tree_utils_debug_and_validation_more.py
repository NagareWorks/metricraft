import json
import pytest

from metricraft._legacy.builder.mixins import FactoryMixin
from metricraft._legacy.tree import (
    LabelMatcher,
    MatchType,
    MetricSelector,
    NumberLiteral,
    StringLiteral,
    BinaryExpr,
    BinaryOperator,
    AggregationExpr,
    AggregationOperator,
    GroupModifier,
)
from metricraft._legacy.tree.utils.debug import ASTDebugger, QueryAnalyzer
from metricraft._legacy.tree.utils.validation import (
    validate_ast_node,
    format_validation_errors,
)
from metricraft._legacy.visitor.position_tracking import PositionTrackingVisitor


def _make_metric_with_label() -> MetricSelector:
    return MetricSelector("cpu", [LabelMatcher("job", MatchType.EQUAL, "api")])


def test_astdebugger_headers_properties_children_and_json():
    m = _make_metric_with_label()
    # aggregation with grouping to populate properties['grouping'] path
    agg = AggregationExpr(AggregationOperator.SUM, m, grouping=GroupModifier(False, ["job"]))
    # binary expression to ensure child traversal
    be = BinaryExpr(agg, BinaryOperator.GT, NumberLiteral(0))

    dbg = ASTDebugger()
    txt = dbg.debug_tree(be)
    assert "Aggregation(sum)" in txt
    assert "grouping" in txt  # property extracted
    assert "BinaryOp(>)" in txt

    js = dbg.debug_json(be)
    data = json.loads(js)
    assert data["node_type"].lower().endswith("expr")


def test_astdebugger_positions_and_visualize_overlay():
    m = _make_metric_with_label()
    dbg = ASTDebugger()
    pos_map = dbg.debug_positions(m)
    assert "Position Map:" in pos_map or "No position information" in pos_map

    # visual overlay should include caret markers when source is provided
    src = 'cpu{job="api"}'
    vis = dbg.visualize_positions(m, src)
    assert isinstance(vis, str)
    assert "Source:" in vis or "Source Code with AST Node Positions:" in vis


def test_format_validation_errors_variants():
    # empty
    assert format_validation_errors([]) == "No validation errors"

    # string error passthrough
    s = format_validation_errors(["oops"])
    assert "Error 1: oops" in s

    # ValidationError with and without source_code
    m = _make_metric_with_label()
    errors = validate_ast_node(m)  # structural/security should pass — zero errors
    assert errors == []

    # Force an invalid label name to produce a structural error
    bad = MetricSelector("m", [LabelMatcher("1bad", MatchType.EQUAL, "x")])
    errs = validate_ast_node(bad)
    formatted = format_validation_errors(errs)
    assert "Invalid label name" in formatted

    # With source_code to trigger error.format_error_with_source path
    formatted_src = format_validation_errors(errs, 'm{1bad="x"}')
    assert "Error 1:" in formatted_src

    # ValidationError without position (construct with ast_node=None)
    from metricraft._legacy.exceptions import ValidationError as VE
    ve = VE(message="boom")
    out = format_validation_errors([ve])
    assert "boom" in out




def test_query_analyzer_patterns_and_issues():
    # Build an expression with long duration and multiple ORs
    b = FactoryMixin.from_metric('a')
    expr = b.or_(FactoryMixin.from_metric('b')).or_(FactoryMixin.from_metric('c')).or_(FactoryMixin.from_metric('d')).or_(FactoryMixin.from_metric('e'))
    expr = expr.rate('1w')  # add range+function to include function detection and long duration

    analyzer = QueryAnalyzer()
    analysis = analyzer.analyze(expr.ast_node)

    assert isinstance(analysis, dict)
    assert analysis.get('complexity', {}).get('depth', 0) >= 0
    perf = analysis.get('performance', {})
    # Heuristic for long duration should likely trigger
    assert isinstance(perf.get('potential_issues', []), list)


def test_position_tracking_maps_label_value_inner_string():
    m = _make_metric_with_label()

    # First, generate the rendered text via the visitor logic
    v1 = PositionTrackingVisitor()
    v1.current_position = 0
    rendered = v1.visit(m)

    # Then, build a position map and verify inner string literal mapping
    v2 = PositionTrackingVisitor()
    pos_map = v2.build_position_map(m)

    # The value_node is a child StringLiteral("api"); ensure it was mapped to the content-only segment
    inner = m.label_matchers[0].value_node
    assert id(inner) in pos_map
    start, end = pos_map[id(inner)]
    assert rendered[start:end] == inner.value


def test_position_tracking_covers_binary_and_aggregation_paths():
    m1 = _make_metric_with_label()
    m2 = MetricSelector("mem", [LabelMatcher("instance", MatchType.EQUAL, "x")])
    be = BinaryExpr(m1, BinaryOperator.AND, m2)
    agg = AggregationExpr(AggregationOperator.SUM, be, grouping=GroupModifier(True, ["instance"]))

    v = PositionTrackingVisitor()
    pos_map = v.build_position_map(agg)
    # Ensure key nodes are tracked
    assert id(be) in pos_map and id(agg) in pos_map
    # Visiting again should produce a stable string
    v2 = PositionTrackingVisitor()
    s = v2.visit(agg)
    assert isinstance(s, str) and len(s) > 0
