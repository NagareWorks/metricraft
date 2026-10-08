import pytest
from metricraft._legacy.builder.mixins import FactoryMixin

def test_validate_success():
    b = FactoryMixin.from_metric('cpu').where_eq('host', 'a')
    # validate should not raise
    b.validate()

def test_validate_fail():
    b = FactoryMixin.from_metric('cpu')
    # invalid label name should raise
    with pytest.raises(Exception):
        b.where_eq('1badlabel', 'x').validate()

def test_sign_state():
    b = FactoryMixin.from_metric('cpu')
    neg = -b
    pos = +b
    assert neg is not None and pos is not None
