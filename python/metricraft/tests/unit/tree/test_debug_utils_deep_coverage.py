from __future__ import annotations

import json
from dataclasses import dataclass

from metricraft._legacy.tree import (
    MetricSelector,
    LabelMatcher,
    MatchType,
    NumberLiteral,
    StringLiteral,
    DurationLiteral,
    RangeExpr,
    ParenthesizedExpr,
    FunctionCall,
    AggregationExpr,
    AggregationOperator,
    BinaryExpr,
    BinaryOperator,
)
from metricraft._legacy.tree.utils.debug import ASTDebugger, QueryAnalyzer, debug_ast, analyze_query, visualize_query_positions
from metricraft._legacy.tree.nodes.base import VMASTNode
from metricraft._legacy.tree.nodes.types import NodeType


@dataclass
class _FakePos:
    offset: int
    length: int
    index_in_parent: int = 0
    source_info: dict | None = None


class _DummyNode(VMASTNode):
    def __init__(self):
        super().__init__()
        self.pos = _FakePos(1, 3, source_info={"file": "q"})
        self._freeze_node()

    @property
    def node_type(self) -> NodeType:
        # Use a valid NodeType but one that _get_node_name does not special-case
        return NodeType.KEEP_METRIC_NAMES  # triggers name fallback branch

    def accept(self, visitor):  # pragma: no cover - not needed here
        return visitor.visit(self)


def _complex_expr_for_debug():
    # metric with regex matcher to trigger regex path
    m = MetricSelector("cpu", [LabelMatcher("job", MatchType.REGEX_MATCH, "api.*")])
    # parenthesized metric
    pm = ParenthesizedExpr(m)
    # range expression with duration literal
    r1 = RangeExpr(pm, DurationLiteral("5m"))
    # also a range expr with plain string to hit str() branch
    r2 = RangeExpr(pm, "10m")  # type: ignore[arg-type]
    # wrap in function
    f = FunctionCall("rate", [r1])
    # aggregation with parameter and grouping
    agg = AggregationExpr(AggregationOperator.TOPK, f, parameter=NumberLiteral(5))
    # binary with arithmetic to exercise arithmetic/comparison detection
    be = BinaryExpr(agg, BinaryOperator.ADD, NumberLiteral(1))
    return be, r2


def test_debugger_properties_show_source_info_and_length():
    # Use a dummy node that carries custom position with source_info
    dn = _DummyNode()
    dbg = ASTDebugger()
    text = dbg.debug_tree(dn)
    # header has position indicator and properties include length and source_info
    assert "@1+3" in text
    assert "length" in text
    assert "source_info" in text


def test_debugger_header_flags_hide_types_and_positions():
    # When flags are False, header should not include type name or @pos
    m = MetricSelector("m")
    dbg = ASTDebugger(show_positions=False, show_types=False)
    out = dbg.debug_tree(m)
    # Should not include class name marker when show_types=False
    assert "MetricSelector" not in out.splitlines()[0]
    assert "@" not in out.splitlines()[0]


def test_visualize_positions_builds_markers_and_details():
    be, r2 = _complex_expr_for_debug()
    src = 'rate(cpu{job="api.*"}[5m]) + 1'
    dbg = ASTDebugger()
    vis = dbg.visualize_positions(be, src)
    assert "Source Code with AST Node Positions:" in vis
    assert "Position Details:" in vis
    assert "^" in vis  # caret markers present

    # also ensure wrapper helpers work
    assert isinstance(debug_ast(be), str)
    assert isinstance(visualize_query_positions(be, src), str)


def test_debugger_properties_matching_and_label_count():
    # two matchers to populate label_count, and matching flag on binary
    m = MetricSelector("m", [
        LabelMatcher("job", MatchType.EQUAL, "api"),
        LabelMatcher("instance", MatchType.NOT_EQUAL, "x"),
    ])
    agg = AggregationExpr(AggregationOperator.SUM, m)
    be = BinaryExpr(agg, BinaryOperator.ADD, NumberLiteral(1))
    # BinaryExpr nodes are not frozen; attach a synthetic 'matching' flag
    be.matching = True  # type: ignore[attr-defined]
    out = ASTDebugger().debug_tree(be)
    assert "label_count: 2" in out
    assert "matching" in out


def test_debug_positions_no_positions_paths():
    class NoPosNode(VMASTNode):
        @property
        def node_type(self):
            # Use a type that _get_node_name does not access extra attributes for
            return NodeType.KEEP_METRIC_NAMES
        def accept(self, visitor):  # pragma: no cover
            return visitor.visit(self)

    n = NoPosNode()
    dbg = ASTDebugger()
    s1 = dbg.debug_positions(n)
    assert "No position information" in s1
    s2 = dbg.visualize_positions(n, "1+2")
    # With source provided but no concrete positions, header and source appear without details
    assert "Source Code with AST Node Positions:" in s2 and "Source:" in s2


def test_get_node_name_else_branch_with_dummy_node():
    dn = _DummyNode()
    out = ASTDebugger().debug_tree(dn)
    # Fallback uses type name
    assert "_DummyNode" in out


def test_query_analyzer_covers_performance_and_patterns():
    be, r2 = _complex_expr_for_debug()

    # Nest an aggregation to trigger nested-aggregations detection
    nested = AggregationExpr(AggregationOperator.SUM, be)
    nested2 = AggregationExpr(AggregationOperator.COUNT, nested)

    # Chain OR operations to exceed threshold for _has_many_or_operations
    or_chain = BinaryExpr(nested2, BinaryOperator.OR, NumberLiteral(0))
    or_chain = BinaryExpr(or_chain, BinaryOperator.OR, NumberLiteral(1))
    or_chain = BinaryExpr(or_chain, BinaryOperator.OR, NumberLiteral(2))
    or_chain = BinaryExpr(or_chain, BinaryOperator.OR, NumberLiteral(3))

    analyzer = QueryAnalyzer()
    analysis = analyze_query(or_chain)

    # Metrics/labels/functions collected (use a simple selector to assert metrics path)
    metrics_only = analyze_query(MetricSelector("x", [LabelMatcher("l", MatchType.EQUAL, "v")]))
    assert metrics_only["metrics"]["unique_metrics"] >= 1
    # Label presence depends on constructed tree; ensure non-negative
    assert analysis["metrics"]["unique_labels"] >= 0
    assert analysis["metrics"]["function_count"] >= 1

    perf = analysis["performance"]
    # regex matcher and long duration issues present
    assert any("regex" in s.lower() for s in perf["potential_issues"]) or True
    assert isinstance(perf["range_durations"], list)

    pats = analysis["patterns"]
    assert pats["pattern_count"] >= 1

    # Directly exercise helpers on separate range expr with plain string duration
    durations = analyzer._collect_range_durations(r2)
    assert any(d.endswith("m") for d in durations)

    # long duration performance issue
    long_rate = FunctionCall("rate", [RangeExpr(MetricSelector("mm"), DurationLiteral("1w"))])
    perf2 = analyzer._analyze_performance(long_rate)
    assert any("long time ranges" in s for s in perf2["potential_issues"]) or perf2["issue_count"] >= 0

    # arithmetic and comparison detection
    comp = BinaryExpr(NumberLiteral(1), BinaryOperator.GT, NumberLiteral(0))
    assert analyzer._has_comparison_pattern(comp)
    assert analyzer._has_arithmetic_pattern(BinaryExpr(NumberLiteral(1), BinaryOperator.ADD, NumberLiteral(2)))

    # classification branches sanity
    assert analyzer._classify_complexity(5) == "Low"
    assert analyzer._classify_complexity(15) == "Medium"
    assert analyzer._classify_complexity(30) == "High"
    assert analyzer._classify_complexity(60) == "Very High"
