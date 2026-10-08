from typing import Any

import pytest

from metricraft._legacy.tree import (
    NumberLiteral,
    StringLiteral,
    DurationLiteral,
)
from metricraft._legacy.tree.nodes.expressions import (
    GroupModifier,
    BinaryModifier,
    BinaryExpr,
    UnaryExpr,
    FunctionCall,
    AggregationExpr,
    ParenthesizedExpr,
    RangeExpr,
)
from metricraft._legacy.tree.nodes.metricsql import (
    WithExpr,
    SubqueryExpr,
    RollupConfig,
    KeepMetricNames,
)
from metricraft._legacy.tree.nodes.selectors import LabelMatcher, MetricSelector
from metricraft._legacy.enums import (
    BinaryOperator,
    UnaryOperator,
    AggregationOperator,
)
from metricraft._legacy.enums.functions import DateTimeFunction
from metricraft._legacy.enums.operators import MatchType
from metricraft._legacy.visitor import QueryToStringVisitor, BaseVisitor
from metricraft._legacy.tree.nodes.types import NodeType


class DummyVisitor(BaseVisitor[str]):
    """Visitor to exercise BaseVisitor's default methods."""

    def visit(self, node) -> str:
        # We won't use dispatch here; tests call specific visit_* directly.
        return self.default_visit(node)

    def default_visit(self, node) -> str:  # type: ignore[override]
        return "ok"


def test_base_visitor_default_methods_cover():
    v = DummyVisitor()
    # Call each default method to ensure they route to default_visit
    assert v.visit_number_literal(NumberLiteral(1)) == "ok"
    assert v.visit_string_literal(StringLiteral("s")) == "ok"
    assert v.visit_duration_literal(DurationLiteral("5m")) == "ok"
    # Use simple objects for non-literal visits; only behavior matters
    class N: pass
    n = N()
    for fn in [
        v.visit_label_matcher,
        v.visit_metric_selector,
        v.visit_instant_vector_selector,
        v.visit_offset_expr,
        v.visit_at_expr,
        v.visit_binary_expr,
        v.visit_unary_expr,
        v.visit_function_call,
        v.visit_aggregation_expr,
        v.visit_parenthesized_expr,
        v.visit_range_expr,
        v.visit_group_modifier,
        v.visit_binary_modifier,
        v.visit_with_expr,
        v.visit_subquery_expr,
        v.visit_rollup_config,
        v.visit_keep_metric_names,
    ]:
        assert fn(n) == "ok"


def test_expressions_modifiers_and_positions_and_codegen():
    left = MetricSelector("cpu_usage", [LabelMatcher("instance", MatchType.EQUAL, "i-1")])
    right = MetricSelector("mem_usage", [])
    expr = BinaryExpr(left, BinaryOperator.ADD, right)

    # Add matching modifier (no existing)
    expr_on = expr.on("a", "b")
    qs_on = QueryToStringVisitor().visit(expr_on)
    assert "on (a, b)" in qs_on

    # Add group_right with no labels to hit `()` branch
    expr_gr = expr_on.group_right()
    qs_gr = QueryToStringVisitor().visit(expr_gr)
    assert "group_right()" in qs_gr and "on (a, b)" in qs_gr

    # Change matching to ignoring (existing present -> copy branch)
    expr_ign = expr_gr.ignoring("c")
    qs_ign = QueryToStringVisitor().visit(expr_ign)
    assert "ignoring (c)" in qs_ign and "on (a, b)" not in qs_ign

    # Add bool
    expr_bool = expr_ign.bool()

    # Positions can be calculated via helper
    pos = expr_bool._calculate_relative_position()
    assert pos.length > 0

    # Debug string
    assert "BinaryExpr" in str(expr_bool)

    # Codegen output includes current modifiers and bool
    qs = QueryToStringVisitor().visit(expr_bool)
    assert "group_right()" in qs
    assert "ignoring (c)" in qs
    assert qs.endswith(" bool")

    # Group modifier and aggregation helpers
    gm_by = GroupModifier(is_without=False, labels=["job", "instance"])  # noqa: F841
    gm_wo = GroupModifier(is_without=True, labels=["zone"])  # noqa: F841

    # Aggregation with parameter and grouping
    agg = AggregationExpr(
        operator=AggregationOperator.TOPK,
        expr=MetricSelector("m", []),
        parameter=NumberLiteral(5),
    ).by("instance")
    s = QueryToStringVisitor().visit(agg)
    assert s.startswith("topk(5, m)") and "by (instance)" in s

    # Unary, Parenthesized, RangeExpr (simple vs complex vs None)
    un = UnaryExpr(UnaryOperator.MINUS, NumberLiteral(2))
    assert QueryToStringVisitor().visit(un) == "-2"

    p = ParenthesizedExpr(BinaryExpr(NumberLiteral(1), BinaryOperator.ADD, NumberLiteral(2)))
    assert QueryToStringVisitor().visit(p) == "(1 + 2)"

    r_simple = RangeExpr(MetricSelector("q", []), DurationLiteral("1h"))
    assert QueryToStringVisitor().visit(r_simple) == "q[1h]"

    r_complex = RangeExpr(p, DurationLiteral("5m"))
    assert QueryToStringVisitor().visit(r_complex) == "((1 + 2))[5m]"

    r_none = RangeExpr(expr=None, range_duration=DurationLiteral("10s"))  # type: ignore[arg-type]
    assert QueryToStringVisitor().visit(r_none) == "(<missing-expr>)[10s]"


def test_metricsql_nodes_codegen_full():
    # WITH + SUBQUERY + ROLLUP + KEEP_METRIC_NAMES
    defs = {"A": MetricSelector("m1", [])}
    inner = RangeExpr(MetricSelector("m2", []), DurationLiteral("5m"))
    call = FunctionCall("rate", [inner])
    with_expr = WithExpr(definitions=defs, expr=call)
    s_with = QueryToStringVisitor().visit(with_expr)
    # Definition renders to m1, the WITH body renders the call
    assert s_with.startswith("WITH (") and "A = m1" in s_with and s_with.endswith(") rate(m2[5m])")

    sub_with_step = SubqueryExpr(MetricSelector("m3", []), DurationLiteral("5m"), DurationLiteral("1m"))
    s1 = QueryToStringVisitor().visit(sub_with_step)
    assert s1.endswith("[5m:1m]")

    sub_no_step = SubqueryExpr(MetricSelector("m3", []), DurationLiteral("5m"))
    s2 = QueryToStringVisitor().visit(sub_no_step)
    assert s2.endswith("[5m:]")

    roll = RollupConfig(MetricSelector("m4", []), {"window": "5m", "k": 2})
    s3 = QueryToStringVisitor().visit(roll)
    assert "@ rollup_config{" in s3 and 'window="5m"' in s3 and 'k="2"' in s3

    keep = KeepMetricNames(MetricSelector("m5", []))
    s4 = QueryToStringVisitor().visit(keep)
    assert s4.endswith(" keep_metric_names")

    # FunctionCall with Enum name and non-AST arg path
    f = FunctionCall(DateTimeFunction.TIME, [])
    assert QueryToStringVisitor().visit(f) == "time()"

    class Dummy:
        def __str__(self) -> str:
            return "X"

    f2 = FunctionCall("f", [Dummy()])
    assert QueryToStringVisitor().visit(f2) == "f(X)"


def test_selectors_construction_and_codegen():
    # LabelMatcher constructor validations
    with pytest.raises(ValueError):
        LabelMatcher("", MatchType.EQUAL, "v")
    
    # Empty value is now allowed for all operators (including = and =~)
    lm = LabelMatcher("n", MatchType.EQUAL, "")
    assert lm.value == ""
    
    # Empty value allowed for not equal
    lm = LabelMatcher("n", MatchType.NOT_EQUAL, "")
    assert lm.value == ""
    
    # Empty value allowed for regex match
    lm = LabelMatcher("n", MatchType.REGEX_MATCH, "")
    assert lm.value == ""

    # MetricSelector without name but with matchers
    ms = MetricSelector(None, [LabelMatcher("a", MatchType.EQUAL, "b")])
    out = QueryToStringVisitor().visit(ms)
    assert out.startswith("{") and out.endswith("}") and "a=\"b\"" in out

    # Empty selector {}
    ms2 = MetricSelector(None, None)
    assert QueryToStringVisitor().visit(ms2) == "{}"


def test_binary_modifier_individual_str_and_position():
    bm = BinaryModifier(matching_type="on", labels=["a"], group_type="group_left", group_labels=["x", "y"])  # noqa: E501
    assert "on(1 labels)" in str(bm)
    # Position calc relies on codegen
    pos = bm._calculate_relative_position()
    assert pos.length > 0

    gm = GroupModifier(False, ["l1"])  # __str__ path
    assert "GroupModifier(by" in str(gm)

