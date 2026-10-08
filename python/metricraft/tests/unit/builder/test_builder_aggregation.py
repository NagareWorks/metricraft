import pytest
from metricraft._legacy.builder.mixins import FactoryMixin

def test_aggregation_by_without():
    b = FactoryMixin.from_metric('cpu')
    # sum/avg/min/max/count by/without
    for agg in ['sum', 'avg', 'min', 'max', 'count']:
        agg_func = getattr(b, agg)()
        by = agg_func.by('host', 'zone')
        without = agg_func.without('foo')
        assert by is not None and without is not None

def test_topk_bottomk():
    b = FactoryMixin.from_metric('cpu')
    topk = b.topk(3)
    bottomk = b.bottomk(2)
    assert topk is not None and bottomk is not None

def test_group_left_right():
    b1 = FactoryMixin.from_metric('cpu')
    b2 = FactoryMixin.from_metric('mem')
    expr = b1 + b2
    gl = expr.group_left('foo')
    gr = expr.group_right('bar')
    assert gl is not None and gr is not None
