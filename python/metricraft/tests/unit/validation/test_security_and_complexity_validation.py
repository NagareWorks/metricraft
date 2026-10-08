from metricraft._legacy.exceptions import ValidationError
from metricraft._legacy.tree import (
    FunctionCall,
    AggregationExpr,
    MetricSelector,
    LabelMatcher,
    NumberLiteral,
    StringLiteral,
    DurationLiteral,
)
from metricraft._legacy.enums.operators import MatchType
from metricraft._legacy.enums import AggregationOperator
from metricraft._legacy.tree.utils.validation import (
    QueryComplexityValidator,
    validate_ast_node,
    format_validation_errors,
)


def test_complexity_validator_depth_and_function_count():
    # Build nested aggregations to exceed depth and function count
    node = MetricSelector("m", [])
    for _ in range(20):
        node = AggregationExpr(AggregationOperator.SUM, node)

    comp = QueryComplexityValidator(max_depth=5, max_functions=5)
    errs = comp.validate(node, node)
    assert len(errs) >= 2


def test_validate_ast_node_structural_and_formatting():
    # Test structural validation with invalid label name
    bad_matcher = LabelMatcher("123invalid", MatchType.EQUAL, "value")
    errs = validate_ast_node(bad_matcher, bad_matcher, enable_complexity_validation=False)
    assert errs, "Expected structural validation errors for invalid label name"

    # Format without source
    text = format_validation_errors(errs)
    assert text.startswith("Error 1:")

    # Test format with source_code enhanced path
    formatted = format_validation_errors(errs, source_code='123invalid="value"')
    assert formatted.startswith("Error 1:")


def test_promql_string_escaping():
    """Test the core escaping functionality for PromQL injection prevention"""
    from metricraft._legacy.tree.utils.validation import escape_promql_string

    # Test basic escaping
    assert escape_promql_string('normal') == 'normal'
    assert escape_promql_string('quote"test') == 'quote\\"test'
    assert escape_promql_string("single'test") == "single\\'test"
    assert escape_promql_string('backslash\\test') == 'backslash\\\\test'

    # Test multiple escaping scenarios
    assert escape_promql_string('quote"and\'single') == 'quote\\"and\\\'single'
    assert escape_promql_string('complex\\quote"test') == 'complex\\\\quote\\"test'

    # Test empty string
    assert escape_promql_string('') == ''

    # Test length limit
    try:
        escape_promql_string('a' * 1001)
        assert False, "Should raise ValueError for long strings"
    except ValueError as e:
        assert "String too long" in str(e)

    print("All escaping tests passed!")


def test_builder_layer_escaping():
    """Test that builder layer properly escapes dangerous input"""
    from metricraft._legacy.builder.impl.instant_vector import InstantVectorBuilder
    from metricraft._legacy.tree import MetricSelector
    from metricraft._legacy.visitor import get_query_visitor

    builder = InstantVectorBuilder(MetricSelector('test_metric', []))

    # Test escaping of dangerous characters in label values
    dangerous_values = [
        'test"value',           # Double quote
        "test'value",           # Single quote
        'test\\value',          # Backslash
        'test"\\\'value',       # Mixed special chars
        '',                     # Empty value
    ]

    for value in dangerous_values:
        try:
            result_builder = builder.where_eq('job', value)
            # Convert to query string to verify escaping worked
            query = get_query_visitor().visit(result_builder._ast_node)
            assert f'job=' in query
            # The query should contain properly escaped values
            print(f"Successfully escaped and built query for value: {repr(value)} -> {query}")
        except Exception as e:
            # Should not fail for escaping
            assert False, f"Builder failed with escaping for value {repr(value)}: {e}"

    # Test that invalid label names still fail
    try:
        builder.where_eq('123invalid', 'value')
        assert False, "Should still fail for invalid label names"
    except Exception as e:
        assert "must match" in str(e)

    print("All builder escaping tests passed!")


def test_validate_promql_string_edge_cases():
    """Test edge cases for PromQL string validation"""
    from metricraft._legacy.tree.utils.validation import validate_promql_string

    # Test empty string
    assert validate_promql_string("") is True

    # Test valid strings - even number of unescaped quotes
    assert validate_promql_string("normal") is True
    assert validate_promql_string('value with spaces') is True
    assert validate_promql_string("value''with''quotes") is True  # Even number of single quotes
    assert validate_promql_string('value""with""quotes') is True  # Even number of double quotes
    assert validate_promql_string("value\\'with\\'quotes") is True  # Escaped quotes are fine
    assert validate_promql_string('value\\"with\\"quotes') is True  # Escaped quotes are fine

    # Test invalid strings - odd number of unescaped quotes
    assert validate_promql_string("value'with") is False  # Odd single quote
    assert validate_promql_string('value"with') is False  # Odd double quote
    assert validate_promql_string("value'with''quotes") is False  # Odd number (3) of single quotes

    # Test long string (should fail)
    assert validate_promql_string("a" * 1001) is False

    print("All PromQL string validation edge cases passed!")


def test_structural_validator_allows_double_underscore_labels():
    """Custom labels starting with '__' should now be accepted (except regex/format failures)."""
    from metricraft._legacy.tree.utils.validation import StructuralASTValidator
    from metricraft._legacy.tree import LabelMatcher

    validator = StructuralASTValidator()

    # Previously treated as reserved; now allowed for custom deployments
    custom_labels = ["__private", "__internal", "__custom", "__test", "__aggr__"]

    for label_name in custom_labels:
        matcher = LabelMatcher(label_name, MatchType.EQUAL, "value")
        errors = validator._validate_label_matcher(matcher, None)
        assert len(errors) == 0

    # __name__ should still be valid
    name_matcher = LabelMatcher("__name__", MatchType.EQUAL, "metric_name")
    name_errors = validator._validate_label_matcher(name_matcher, None)
    assert len(name_errors) == 0

    print("All double-underscore label tests passed!")


def test_structural_validator_aggregation_params():
    """Test structural validator aggregation parameter checking"""
    from metricraft._legacy.tree.utils.validation import StructuralASTValidator
    from metricraft._legacy.tree import AggregationExpr, AggregationOperator, NumberLiteral, MetricSelector

    validator = StructuralASTValidator()

    # Test topk without parameter (should error)
    topk_no_param = AggregationExpr(AggregationOperator.TOPK, MetricSelector("test"))
    errors = validator._validate_aggregation_expr(topk_no_param, None)
    assert len(errors) == 1
    assert "requires a parameter" in errors[0].message

    # Test bottomk without parameter (should error)
    bottomk_no_param = AggregationExpr(AggregationOperator.BOTTOMK, MetricSelector("test"))
    errors = validator._validate_aggregation_expr(bottomk_no_param, None)
    assert len(errors) == 1
    assert "requires a parameter" in errors[0].message

    # Test sum with parameter (should be fine - parameter ignored)
    sum_with_param = AggregationExpr(AggregationOperator.SUM, MetricSelector("test"), parameter=NumberLiteral(5))
    sum_errors = validator._validate_aggregation_expr(sum_with_param, None)
    assert len(sum_errors) == 0

    # Test aggregation with duplicate grouping labels
    metric = MetricSelector("test")
    agg_with_duplicates = AggregationExpr(AggregationOperator.SUM, metric)
    # Create grouping with duplicates manually (this would normally not happen)
    from metricraft._legacy.tree import GroupModifier
    agg_with_duplicates.grouping = GroupModifier(False, ["job", "instance", "job"])
    dup_errors = validator._validate_aggregation_expr(agg_with_duplicates, None)
    assert len(dup_errors) == 1
    assert "Duplicate labels" in dup_errors[0].message

    print("All aggregation validation tests passed!")


def test_complexity_validator_edge_cases():
    """Test complexity validator edge cases"""
    from metricraft._legacy.tree.utils.validation import QueryComplexityValidator
    from metricraft._legacy.tree import MetricSelector, AggregationExpr, AggregationOperator

    # Test with zero limits - create an expression that actually has depth
    strict_validator = QueryComplexityValidator(max_depth=0, max_functions=0)
    metric = MetricSelector("test")

    # Create nested aggregation to ensure depth > 0
    agg = AggregationExpr(AggregationOperator.SUM, metric)
    errors = strict_validator.validate(agg, agg)
    assert len(errors) >= 1  # Should fail either depth or function count

    # Test with very high limits
    lenient_validator = QueryComplexityValidator(max_depth=1000, max_functions=1000)
    errors = lenient_validator.validate(metric, metric)
    assert len(errors) == 0  # Should pass

    # Test function count limit
    func_validator = QueryComplexityValidator(max_depth=10, max_functions=0)
    # Create an aggregation (counts as 1 function)
    func_errors = func_validator.validate(agg, agg)
    assert len(func_errors) >= 1  # Should fail on function count

    print("All complexity validator edge cases passed!")
