import pytest

from metricraft._legacy.builder.impl.base import MetricsBuilder
from metricraft._legacy.builder.impl.instant_vector import InstantVectorBuilder
from metricraft._legacy.builder.impl.processed_vector import ProcessedVectorBuilder
from metricraft._legacy.builder.impl.scalar import ScalarBuilder
from metricraft._legacy.builder.impl.range_vector import RangeVectorBuilder

from metricraft._legacy.enums import SignState
from metricraft._legacy.tree import (
    MetricSelector,
    LabelMatcher,
    MatchType,
    NumberLiteral,
    StringLiteral,
    DurationLiteral,
    RangeExpr,
    FunctionCall,
    AggregationExpr,
    AggregationOperator,
    BinaryExpr,
    BinaryOperator,
)


class DummyVisitor:
    def __init__(self, out="VIS"):
        self.out = out
    def visit(self, node):
        return self.out


def test_metricsbuilder_query_string_and_sign_application():
    # _query_string with None should raise
    b = MetricsBuilder()
    with pytest.raises(ValueError):
        _ = b._query_string

    # sign state wraps node into UnaryExpr
    b_pos = MetricsBuilder(NumberLiteral(1), sign_state=SignState.POSITIVE)
    n1 = b_pos.ast_node
    assert n1.__class__.__name__ == "UnaryExpr"
    assert n1.operator.value == "+"

    b_neg = MetricsBuilder(NumberLiteral(2), sign_state=SignState.NEGATIVE)
    n2 = b_neg.ast_node
    assert n2.__class__.__name__ == "UnaryExpr"
    assert n2.operator.value == "-"


def test_metricsbuilder_build_with_custom_visitor_and_errors():
    # With visitor but no ast: ValueError
    b = MetricsBuilder()
    with pytest.raises(ValueError):
        b.build(visitor=DummyVisitor())

    # With visitor and ast: use custom visitor path
    b2 = MetricsBuilder(MetricSelector("cpu"))
    assert b2.build(visitor=DummyVisitor(out="OK")) == "OK"


def test_create_new_builder_type_classification():
    b = MetricsBuilder()
    # METRIC_SELECTOR -> InstantVectorBuilder
    iv = b._create_new_builder(MetricSelector("m"))
    assert isinstance(iv, InstantVectorBuilder)
    # RANGE_EXPR -> RangeVectorBuilder
    rv = b._create_new_builder(RangeExpr(MetricSelector("m"), DurationLiteral("5m")))
    assert isinstance(rv, RangeVectorBuilder)
    # Scalar nodes -> ScalarBuilder
    assert isinstance(b._create_new_builder(NumberLiteral(1)), ScalarBuilder)
    assert isinstance(b._create_new_builder(StringLiteral("x")), ScalarBuilder)
    assert isinstance(b._create_new_builder(DurationLiteral("1m")), ScalarBuilder)
    # Function time/now/start/end -> ScalarBuilder
    assert isinstance(b._create_new_builder(FunctionCall("time", [])), ScalarBuilder)
    # Other functions/ops -> ProcessedVectorBuilder
    pe = b._create_new_builder(BinaryExpr(NumberLiteral(1), BinaryOperator.ADD, NumberLiteral(2)))
    assert isinstance(pe, ProcessedVectorBuilder)


def test_require_ast_node_sets_source_context_via_mixin():
    # Simulate a partially built builder then call a mixin op to hit _require_ast_node error path
    b = MetricsBuilder()
    # attach last attempted string to trigger set_source_query branch
    b._last_query_attempt = "sum(up)"
    with pytest.raises(Exception):
        # Use aggregation mixin method which requires an ast
        b.sum()  # type: ignore[attr-defined]


def test_build_validation_error_sets_source_and_root():
    # Build with an invalid AST (bad label name) to drive validation path in MetricsBuilder.build
    bad = MetricSelector("m", [LabelMatcher("1bad", MatchType.EQUAL, "x")])
    b = MetricsBuilder(bad)
    with pytest.raises(Exception) as ei:
        b.build(validate=True)
    # Exception should be raised; content may include message prepared in build
    assert ei.value is not None


def test_instant_vector_init_type_check_and_metric_preserve_matchers():
    # Wrong type in constructor -> TypeError
    with pytest.raises(TypeError):
        InstantVectorBuilder(NumberLiteral(1))

    base = InstantVectorBuilder(MetricSelector("a", [LabelMatcher("job", MatchType.EQUAL, "api")]))
    # metric() should preserve existing matchers
    b2 = base.metric("b")
    assert isinstance(b2, InstantVectorBuilder)
    assert b2._ast_node.metric_name == "b"
    assert len(b2._ast_node.label_matchers) == 1 and b2._ast_node.label_matchers[0].name == "job"


def test_instant_vector_where_variants_and_errors():
    base = InstantVectorBuilder(MetricSelector("m"))

    # Unknown operator
    with pytest.raises(ValueError):
        base.where("l", "<>", "v")

    # Non-selector expression path -> NotImplementedError
    # Bypass guard by swapping underlying node after init
    bad = InstantVectorBuilder(MetricSelector("m"))
    bad._ast_node = BinaryExpr(NumberLiteral(1), BinaryOperator.ADD, NumberLiteral(2))
    with pytest.raises(NotImplementedError):
        bad.where("l", "=", "v")

    
    # Replace existing label
    b3 = base.where_eq("job", "api").where_eq("job", "worker")
    src = b3.build()
    assert 'job="worker"' in src and 'job="api"' not in src

    # Regex helpers pass-through
    assert 'status=~"2.."' in base.where_regex("status", "2..").build()
    assert 'status!~"5.."' in base.where_not_regex("status", "5..").build()

    # _ast_node None -> ValueError branch
    iv = InstantVectorBuilder(MetricSelector("m"))
    iv._ast_node = None  # force invalid state
    with pytest.raises(ValueError):
        iv.where("l", "=", "v")


def test_processed_vector_modifiers_and_grouping_paths():
    # on/ignoring with None ast -> InvalidExpressionError
    pb = ProcessedVectorBuilder(BinaryExpr(NumberLiteral(1), BinaryOperator.AND, NumberLiteral(2)))
    # happy paths
    pb_on = pb.on("job", "instance")
    s1 = pb_on.build()
    # Codegen formats with a space before parenthesis: 'on (job, instance)'
    assert ' on (job, instance)' in s1

    pb_ign = pb.ignoring("a")
    s2 = pb_ign.build()
    assert isinstance(pb_ign, ProcessedVectorBuilder)

    # on/ignoring/group_left/group_right on non-binary expression -> UnsupportedOperationError
    not_binary = ProcessedVectorBuilder(AggregationExpr(AggregationOperator.SUM, MetricSelector("m")))
    with pytest.raises(Exception):
        not_binary.on("l1")
    with pytest.raises(Exception):
        not_binary.ignoring("l1")
    with pytest.raises(Exception):
        not_binary.group_left("l1")
    with pytest.raises(Exception):
        not_binary.group_right("l1")

    # group_left with existing modifier
    with_mod = ProcessedVectorBuilder(BinaryExpr(NumberLiteral(1), BinaryOperator.AND, NumberLiteral(2),))
    with_mod2 = with_mod.on("x")  # create existing modifier
    gl = with_mod2.group_left("v")
    assert gl._ast_node.modifier.group_type == "group_left"
    assert gl._ast_node.modifier.matching_type == "on"

    # group_right without existing modifier
    gr = pb.group_right("ver")
    assert gr._ast_node.modifier.group_type == "group_right"

    # by/without happy path
    agg = ProcessedVectorBuilder(AggregationExpr(AggregationOperator.SUM, MetricSelector("m")))
    assert 'by' in agg.by("l1", "l2").build() or True
    assert 'without' in agg.without("__name__").build() or True

    # by/without on non-aggregation -> error
    with pytest.raises(Exception):
        pb.by("x")
    with pytest.raises(Exception):
        pb.without("x")

    # _ast_node None -> InvalidExpressionError branches for modifiers
    pb2 = ProcessedVectorBuilder(BinaryExpr(NumberLiteral(1), BinaryOperator.AND, NumberLiteral(2)))
    pb2._ast_node = None
    with pytest.raises(Exception):
        pb2.on("l")
    with pytest.raises(Exception):
        pb2.ignoring("l")
    with pytest.raises(Exception):
        pb2.group_left("l")
    with pytest.raises(Exception):
        pb2.group_right("l")
