from metricraft._legacy.enums.operators import BinaryOperator, UnaryOperator, AggregationOperator, MatchType
from metricraft._legacy.enums.modifiers import GroupModifierType, BinaryModifierType


def test_binary_operator_properties():
    # arithmetic/comparison/logical/set
    assert BinaryOperator.ADD.is_arithmetic
    assert BinaryOperator.GT.is_comparison
    assert BinaryOperator.AND.is_logical
    assert BinaryOperator.GROUP_LEFT.is_set_operator
    # operation_name fallback returns something non-empty
    assert isinstance(BinaryOperator.ADD.operation_name, str) and BinaryOperator.ADD.operation_name


def test_unary_operator_properties():
    assert UnaryOperator.PLUS.operation_name == "unary +"


def test_aggregation_operator_meta():
    assert AggregationOperator.SUM.is_standard_promql
    assert AggregationOperator.MEDIAN.is_metricsql_extension
    assert AggregationOperator.TOPK.requires_parameter


def test_match_type_flags():
    assert MatchType.REGEX_MATCH.is_regex
    assert MatchType.NOT_EQUAL.is_negated
    assert isinstance(MatchType.EQUAL.operation_name, str)


def test_group_and_binary_modifier_types():
    assert GroupModifierType.BY.is_inclusive is True
    assert GroupModifierType.WITHOUT.is_inclusive is False

    assert BinaryModifierType.ON.is_matching_modifier
    assert BinaryModifierType.GROUP_RIGHT.is_group_modifier
    assert BinaryModifierType.ON.is_inclusive is True
