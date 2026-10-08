import pytest

from metricraft._legacy.builder.mixins import FactoryMixin
from metricraft._legacy.builder.impl.base import MetricsBuilder
from metricraft._legacy.enums import BinaryOperator


def test_arithmetic_reverse_ops_and_pow_mod():
    a = FactoryMixin.from_metric('a')
    # Forward chaining
    _ = a.add(1).sub(2).mul(3).div(4).mod(2).pow(2)
    # Reverse magic methods
    _ = 1 + a
    _ = 2 - a
    _ = 3 * a
    _ = 4 / a
    # Power/mod magic
    _ = a ** 2
    _ = a % 2


def test_factory_from_scalar_vector_and_expr_and_time_family():
    # New semantics: vector() is a scalar method
    v = FactoryMixin.from_scalar(1.5).vector()
    assert v.ast_node is not None
    e = FactoryMixin.from_expr('sum(rate(x[5m]))')
    assert e.ast_node is not None
    _ = FactoryMixin.from_time()
    _ = FactoryMixin.from_now()
    _ = FactoryMixin.from_start()
    _ = FactoryMixin.from_end()


def test_instant_vector_where_replaces_and_errors():
    b = FactoryMixin.from_metric('cpu')
    b2 = b.where_eq('job', 'api').where_eq('job', 'web')
    # Replace same label matcher
    s = b2.build(validate=False)
    assert 'job="web"' in s and 'job="api"' not in s
    # Unsupported operator
    with pytest.raises(ValueError):
        b.where('job', '><', 'x')


def test_base_create_new_builder_type_resolution():
    # Exercise _create_new_builder type dispatch via public API
    b = FactoryMixin.from_metric('cpu')
    # to range -> RangeVectorBuilder
    rb = b.range('5m')
    assert rb.ast_node is not None
    # number/string/time -> ScalarBuilder
    sb1 = FactoryMixin.from_scalar(1)
    sb2 = FactoryMixin.from_string('x')
    sb3 = FactoryMixin.from_time()
    for s in (sb1, sb2, sb3):
        assert s.ast_node is not None
    # binary/function/aggregation -> ProcessedVectorBuilder
    pv = b.add(1).sum()
    assert pv.ast_node is not None
