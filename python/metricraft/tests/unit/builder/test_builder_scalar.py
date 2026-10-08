import pytest
from metricraft._legacy.builder.mixins import FactoryMixin

def test_scalar_basic():
    b = FactoryMixin.from_scalar(3.14)
    assert b is not None
    b2 = FactoryMixin.from_time()
    assert b2 is not None
    b3 = FactoryMixin.from_now()
    assert b3 is not None
    b4 = FactoryMixin.from_start()
    assert b4 is not None
    b5 = FactoryMixin.from_end()
    assert b5 is not None