import pytest
from metricraft._legacy.builder.mixins import FactoryMixin
from metricraft._legacy.builder.impl.instant_vector import InstantVectorBuilder
from metricraft._legacy.builder.impl.processed_vector import ProcessedVectorBuilder
from metricraft._legacy.builder.impl.range_vector import RangeVectorBuilder
from metricraft._legacy.builder.impl.scalar import ScalarBuilder

# 1. InstantVectorBuilder boundaries and errors

def test_instant_vector_builder_type_guard():
    b = FactoryMixin.from_metric('cpu')
    assert isinstance(b, InstantVectorBuilder)
    # None ast_node should not raise; allow deferred AST assignment
    inst = InstantVectorBuilder(ast_node=None)
    assert isinstance(inst, InstantVectorBuilder)

# 2. where/where_eq/where_ne/where_regex/where_not_regex boundaries

def test_where_invalid_operator():
    b = FactoryMixin.from_metric('cpu')
    with pytest.raises(ValueError):
        b.where('host', '??', 'a')

def test_where_no_base():
    b = FactoryMixin.from_metric('cpu')
    b._ast_node = None
    with pytest.raises(ValueError):
        b.where('host', '=', 'a')

# 3. validate_ast_node branches

def test_where_validation_error():
    b = FactoryMixin.from_metric('cpu')
    # invalid label name
    with pytest.raises(Exception):
        b.where_eq('1bad', 'x')

# 4. metric() branches

def test_metric_replace_and_new():
    b = FactoryMixin.from_metric('cpu').where_eq('host', 'a')
    b2 = b.metric('mem')
    assert b2 is not None
    b3 = FactoryMixin.from_metric('cpu')
    b4 = b3.metric('mem')
    assert b4 is not None

# 5. ProcessedVectorBuilder branches

def test_processed_vector_on_ignoring_group():
    b1 = FactoryMixin.from_metric('cpu')
    b2 = FactoryMixin.from_metric('mem')
    p = (b1 + b2).on('host').ignoring('zone').group_left('foo').group_right('bar')
    assert isinstance(p, ProcessedVectorBuilder)

# 6. ProcessedVectorBuilder aggregation branches

def test_processed_vector_by_without():
    b = FactoryMixin.from_metric('cpu').sum()
    p1 = b.by('host')
    p2 = b.without('zone')
    assert isinstance(p1, ProcessedVectorBuilder)
    assert isinstance(p2, ProcessedVectorBuilder)
    # calling by/without on non-aggregation expression
    with pytest.raises(Exception):
        FactoryMixin.from_metric('cpu').by('host')

# 7. RangeVectorBuilder type

def test_range_vector_builder_type():
    b = FactoryMixin.from_metric('cpu').range('5m')
    assert isinstance(b, RangeVectorBuilder)

# 8. ScalarBuilder type

def test_scalar_builder_type():
    b = FactoryMixin.from_scalar(1)
    assert isinstance(b, ScalarBuilder)
    b2 = FactoryMixin.from_time()
    assert isinstance(b2, ScalarBuilder)
    b3 = FactoryMixin.from_now()
    assert isinstance(b3, ScalarBuilder)
    b4 = FactoryMixin.from_start()
    assert isinstance(b4, ScalarBuilder)
    b5 = FactoryMixin.from_end()
    assert isinstance(b5, ScalarBuilder)
