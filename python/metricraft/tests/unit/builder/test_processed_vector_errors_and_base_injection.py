import pytest

from metricraft._legacy.builder.mixins import FactoryMixin
from metricraft._legacy.builder.impl.base import MetricsBuilder
from metricraft._legacy.builder.impl.processed_vector import ProcessedVectorBuilder
from metricraft._legacy.exceptions import VMInvalidExpressionError
from metricraft._legacy.exceptions import UnsupportedOperationError


def test_processed_vector_on_ignoring_group_left_right_errors_on_non_binary():
    # sum() produces AggregationExpr, not BinaryExpr
    agg = FactoryMixin.from_metric('m').sum()
    with pytest.raises(UnsupportedOperationError):
        agg.on('a')
    with pytest.raises(UnsupportedOperationError):
        agg.ignoring('a')
    with pytest.raises(UnsupportedOperationError):
        agg.group_left('a')
    with pytest.raises(UnsupportedOperationError):
        agg.group_right('a')


def test_processed_vector_by_without_errors_on_non_aggregation():
    # or_ produces BinaryExpr, not AggregationExpr
    pv = FactoryMixin.from_metric('a').or_(FactoryMixin.from_metric('b'))
    with pytest.raises(UnsupportedOperationError):
        pv.by('x')
    with pytest.raises(UnsupportedOperationError):
        pv.without('x')
