from metricraft._legacy.tree import NumberLiteral, StringLiteral, DurationLiteral
from metricraft._legacy.tree.nodes.selectors import LabelMatcher, MetricSelector, OffsetExpr, AtExpr
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
from metricraft._legacy.enums import BinaryOperator, UnaryOperator, AggregationOperator
from metricraft._legacy.enums.base import OperationEnum, FunctionEnum, ModifierEnum
from metricraft._legacy.enums.operators import MatchType
from metricraft._legacy.visitor import QueryToStringVisitor


def test_accept_methods_and_str_and_node_type_properties():
    v = QueryToStringVisitor()

    # Literals
    n = NumberLiteral(1.0)
    s = StringLiteral("x")
    d = DurationLiteral("1m")
    assert n.accept(v) == "1" and str(n).startswith("NumberLiteral") and n.node_type.name
    assert s.accept(v) == '"x"' and str(s).startswith("StringLiteral")
    assert d.accept(v) == "1m" and str(d).startswith("DurationLiteral")

    # Selectors and matchers
    lm = LabelMatcher("a", MatchType.EQUAL, "b")
    ms = MetricSelector("m", [lm])
    assert lm.accept(v) == 'a="b"' and "LabelMatcher" in str(lm)
    assert ms.accept(v).startswith("m{") and "MetricSelector" in str(ms)

    # Modifiers
    gm = GroupModifier(is_without=False, labels=["l1"])
    bm = BinaryModifier(matching_type="on", labels=["x"], group_type="group_left", group_labels=["y"])  # noqa: E501
    assert "GroupModifier" in str(gm) and gm.node_type.name
    assert "BinaryModifier" in str(bm) and bm.node_type.name
    assert gm.accept(v) and bm.accept(v)

    # Expressions
    be = BinaryExpr(ms, BinaryOperator.ADD, n)
    assert be.accept(v).endswith(" + 1") and "BinaryExpr" in str(be)

    ue = UnaryExpr(UnaryOperator.PLUS, n)
    assert ue.accept(v) == "+1" and "UnaryExpr" in str(ue)

    fc = FunctionCall("sum", [ms])
    assert fc.accept(v).startswith("sum(") and "FunctionCall" in str(fc)

    agg = AggregationExpr(AggregationOperator.SUM, ms)
    assert agg.accept(v).startswith("sum(") and "AggregationExpr" in str(agg)

    pe = ParenthesizedExpr(be)
    assert pe.accept(v).startswith("(") and "ParenthesizedExpr" in str(pe)

    re = RangeExpr(ms, DurationLiteral("5m"))
    assert re.accept(v).endswith("[5m]") and "RangeExpr" in str(re)

    # MetricsQL extras
    w = WithExpr({"A": ms}, fc)
    assert w.accept(v).startswith("WITH (") and "WithExpr" in str(w)

    sub = SubqueryExpr(ms, DurationLiteral("5m"), DurationLiteral("1m"))
    assert sub.accept(v).endswith("[5m:1m]")

    roll = RollupConfig(ms, {"window": "5m"})
    assert "rollup_config" in roll.accept(v)

    keep = KeepMetricNames(ms)
    assert keep.accept(v).endswith(" keep_metric_names")

    # Offset / At
    off = OffsetExpr(ms, DurationLiteral("10s"))
    assert off.accept(v).endswith(" offset 10s")

    at1 = AtExpr(ms, "now()")
    at2 = AtExpr(ms, 1700000000)
    assert at1.accept(v).endswith(" @ now()")
    assert at2.accept(v).endswith(" @ 1700000000")


def test_error_context_properties():
    # exercise error_context on base enums
    assert isinstance(OperationEnum.__mro__[0].__name__, str)  # smoke
    assert isinstance(FunctionEnum.__mro__[0].__name__, str)
    assert isinstance(ModifierEnum.__mro__[0].__name__, str)

    # Pick concrete enums to access error_context
    from metricraft._legacy.enums.operators import BinaryOperator as BO
    from metricraft._legacy.enums.functions import MathFunction
    from metricraft._legacy.enums.modifiers import GroupModifierType

    assert isinstance(BO.ADD.error_context, str)
    assert isinstance(MathFunction.ABS.error_context, str)
    assert isinstance(GroupModifierType.BY.error_context, str)


def test_codegen_default_visit_fallback():
    class Weird:
        node_type = object()  # not equal to any NodeType member
    v = QueryToStringVisitor()
    out = v.visit(Weird())
    assert out == "<Weird>"
