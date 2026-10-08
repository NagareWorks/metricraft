import pytest

from metricraft._legacy.exceptions import InvalidParameterError, ValidationError
from metricraft._legacy.tree.utils.validation import (
    validate_label_name_string,
    validate_metric_name_string,
    StructuralASTValidator,
)
from metricraft._legacy.tree import AggregationExpr, MetricSelector
from metricraft._legacy.enums import AggregationOperator


def test_validate_label_name_string_fast_and_whitelist_and_errors():
    # Whitelist fast path
    assert validate_label_name_string('job') is True

    # Fast ASCII path valid
    assert validate_label_name_string('abc_123') is True

    # Empty -> error
    with pytest.raises(InvalidParameterError):
        validate_label_name_string('')

    # Starts with digit -> error (slow path formatting)
    with pytest.raises(InvalidParameterError):
        validate_label_name_string('9abc')

    # Invalid character '-' -> error
    with pytest.raises(InvalidParameterError):
        validate_label_name_string('a-b')

    # Double-underscore labels (e.g. custom '__reserved') are allowed
    assert validate_label_name_string('__reserved') is True


def test_validate_metric_name_string_valid_and_errors():
    assert validate_metric_name_string('http_requests_total') is True

    with pytest.raises(InvalidParameterError):
        validate_metric_name_string('')

    with pytest.raises(InvalidParameterError):
        validate_metric_name_string('9metric')


def test_structural_aggregation_param_and_grouping_duplicates():
    v = StructuralASTValidator()

    # topk without parameter -> error
    agg = AggregationExpr(AggregationOperator.TOPK, MetricSelector('m', []))
    errs = v.validate(agg, agg)
    assert any(isinstance(e, ValidationError) and 'requires a parameter' in str(e) for e in errs)

    # duplicate grouping labels -> error
    agg2 = AggregationExpr(AggregationOperator.SUM, MetricSelector('m', []))
    agg2 = agg2.by('a', 'a')
    errs2 = v.validate(agg2, agg2)
    assert any('Duplicate labels' in str(e) for e in errs2)
