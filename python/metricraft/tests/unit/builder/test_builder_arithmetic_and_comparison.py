import pytest
from metricraft._legacy.builder.mixins import FactoryMixin

def test_arithmetic_chain():
    b = FactoryMixin.from_metric('cpu')
    b2 = FactoryMixin.from_metric('mem')
    add = b + b2
    sub = b - b2
    mul = b * b2
    div = b / b2
    assert add is not None and sub is not None and mul is not None and div is not None

def test_comparison_chain():
    b = FactoryMixin.from_metric('cpu')
    b2 = FactoryMixin.from_metric('mem')
    gt = b > b2
    ge = b >= b2
    lt = b < b2
    le = b <= b2
    eq = b == b2
    ne = b != b2
    assert all([gt, ge, lt, le, eq, ne])
