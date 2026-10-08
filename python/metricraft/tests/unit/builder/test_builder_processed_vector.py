import pytest
from metricraft._legacy.builder.mixins import FactoryMixin

def test_on_ignoring_group():
    b1 = FactoryMixin.from_metric('cpu')
    b2 = b1 + FactoryMixin.from_metric('mem')
    p = b2.on('host').ignoring('zone')
    assert hasattr(p, 'on')
    assert hasattr(p, 'ignoring')
    # Only need to ensure no exception raised

def test_group_left_right():
    b1 = FactoryMixin.from_metric('cpu')
    b2 = b1 + FactoryMixin.from_metric('mem')
    p = b2.group_left('foo').group_right('bar')
    assert hasattr(p, 'group_left')
    assert hasattr(p, 'group_right')

def test_by_without():
    b = FactoryMixin.from_metric('cpu').sum()
    p1 = b.by('host', 'zone')
    p2 = b.without('foo')
    assert hasattr(p1, 'by')
    assert hasattr(p2, 'without')