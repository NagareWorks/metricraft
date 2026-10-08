import pytest
from datetime import datetime, timezone

from metricraft._legacy.builder.mixins import FactoryMixin
from metricraft._legacy.builder.impl.base import MetricsBuilder
from metricraft._legacy.exceptions import VMInvalidExpressionError
from metricraft._legacy.exceptions import InvalidParameterError


def test_time_range_at_variants():
    b = FactoryMixin.from_metric('cpu')

    # datetime input
    dt = datetime(2021, 1, 1, tzinfo=timezone.utc)
    res = b.at(dt)
    assert res.ast_node is not None

    # ISO string input
    res2 = b.at('2021-01-01T00:00:00Z')
    assert res2.ast_node is not None

    # bad string treated as raw
    res3 = b.at('not-a-date')
    assert res3.ast_node is not None

    # milliseconds -> seconds
    res4 = b.at(1609459200000)
    assert res4.ast_node is not None


def test_time_range_offset_no_ast_error():
    empty = MetricsBuilder()
    with pytest.raises(ValueError):
        empty.offset('5m')


def test_transformation_sort_invalid_direction():
    b = FactoryMixin.from_metric('cpu')
    with pytest.raises(InvalidParameterError):
        b.sort('up')


def test_transformation_label_set_no_labels():
    b = FactoryMixin.from_metric('cpu')
    with pytest.raises(InvalidParameterError):
        b.label_set()


def test_transformation_parenthesize_and_keep_metric_names_no_ast_error():
    empty = MetricsBuilder()
    with pytest.raises(VMInvalidExpressionError):
        empty.parenthesize()
    with pytest.raises(VMInvalidExpressionError):
        empty.keep_metric_names()


def test_transformation_smooth_exponential_range_check():
    b = FactoryMixin.from_metric('cpu')
    with pytest.raises(InvalidParameterError):
        b.smooth_exponential(1.5)


def test_transformation_subquery_duration_and_resolution_validation():
    b = FactoryMixin.from_metric('cpu')
    with pytest.raises(InvalidParameterError):
        b.subquery('')
    with pytest.raises(InvalidParameterError):
        b.subquery('5m', '')


def test_debug_analyzer_regex_label_issue_detected():
    expr = FactoryMixin.from_metric('m').where_regex('job', 'api-.*')
    analysis = expr.analyze()
    assert isinstance(analysis, dict)
    issues = analysis.get('performance', {}).get('potential_issues', [])
    assert any('regex label matchers' in x.lower() for x in issues)
