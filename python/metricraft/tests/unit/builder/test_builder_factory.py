import pytest
from metricraft._legacy.builder.mixins import FactoryMixin

def test_from_metric():
    b = FactoryMixin.from_metric('cpu_usage')
    assert b is not None
    assert hasattr(b, 'where_eq')
    assert hasattr(b, 'metric')

def test_from_scalar():
    b = FactoryMixin.from_scalar(42)
    assert b is not None
    # ScalarBuilder supports chained arithmetic
    b2 = b
    assert b2 is not None


def test_from_string():
    b = FactoryMixin.from_string('abc')
    assert b is not None

def test_from_expr():
    b = FactoryMixin.from_expr('sum(rate(http_requests[5m]))')
    assert b is not None
