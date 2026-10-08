import pytest
from metricraft._legacy.builder.mixins import FactoryMixin

def test_where_eq_and_metric():
    b = FactoryMixin.from_metric('cpu')
    b2 = b.where_eq('host', 'a')
    assert b2 is not b
    b3 = b2.metric('mem')
    assert b3 is not None

def test_where_ne_and_regex():
    b = FactoryMixin.from_metric('cpu')
    b2 = b.where_ne('zone', 'cn')
    assert b2 is not None
    b3 = b2.where_regex('env', 'prod.*')
    assert b3 is not None
    b4 = b3.where_not_regex('env', 'test.*')
    assert b4 is not None

def test_where_replace():
    b = FactoryMixin.from_metric('cpu').where_eq('x', '1').where_eq('x', '2')
    assert b is not None