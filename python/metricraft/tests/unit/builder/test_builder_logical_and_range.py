import pytest
from metricraft._legacy.builder.mixins import FactoryMixin

def test_logical_chain():
    b = FactoryMixin.from_metric('cpu')
    b2 = FactoryMixin.from_metric('mem')
    anded = b & b2
    ored = b | b2
    unlessed = b - b2  # logical minus
    assert anded is not None and ored is not None and unlessed is not None

def test_range_and_functions():
    b = FactoryMixin.from_metric('cpu')
    r = b.range('5m')
    assert r is not None
    # Common over-time functions
    for fn in ['rate', 'increase', 'avg_over_time', 'min_over_time', 'max_over_time']:
        f = getattr(r, fn)()
        assert f is not None
