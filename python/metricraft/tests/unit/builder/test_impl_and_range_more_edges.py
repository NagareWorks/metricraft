import pytest

from metricraft._legacy.builder.mixins import FactoryMixin
from metricraft._legacy.exceptions import UnsupportedOperationError


def test_instant_vector_metric_preserves_matchers():
    b = FactoryMixin.from_metric('cpu').where_eq('job', 'api')
    b2 = b.metric('cpu2')
    s = b2.build(validate=False)
    assert 'cpu2' in s and 'job="api"' in s


def test_instant_vector_where_only_on_instant_vector():
    # ProcessedVectorBuilder does not expose where_eq; ensure attribute is absent
    with pytest.raises(AttributeError):
        FactoryMixin.from_scalar(1).add(1).where_eq('job', 'x')


def test_processed_vector_modifiers_on_non_binary_raise():
    p = FactoryMixin.from_metric('a').sum()
    with pytest.raises(UnsupportedOperationError):
        p.on('job')
    with pytest.raises(UnsupportedOperationError):
        p.ignoring('job')
    with pytest.raises(UnsupportedOperationError):
        p.group_left('job')
    with pytest.raises(UnsupportedOperationError):
        p.group_right('job')


def test_processed_vector_by_without_requires_aggregation():
    p = FactoryMixin.from_metric('a').add(1)
    with pytest.raises(UnsupportedOperationError):
        p.by('job')
    with pytest.raises(UnsupportedOperationError):
        p.without('job')


def test_range_vector_functions_quantile_and_rollup_boundaries():
    b = FactoryMixin.from_metric('latency')
    # quantile_over_time boundary already covered; ensure rollup accepts string func
    _ = b.rollup('sum', '1m')


def test_base_custom_visitor_path():
    # Exercise the custom visitor path by building with a dummy visitor
    class DummyVisitor:
        def visit(self, node):
            return 'DUMMY'
    q = FactoryMixin.from_metric('x')
    out = q.build(validate=False, visitor=DummyVisitor())
    assert out == 'DUMMY'
