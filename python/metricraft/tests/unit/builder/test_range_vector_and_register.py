import pytest

from metricraft._legacy.builder.impl.range_vector import RangeVectorBuilder
from metricraft._legacy.builder.impl.register import BuilderRegister
from metricraft._legacy.builder.impl.types import BuilderType
from metricraft._legacy.tree import RangeExpr, NumberLiteral


def test_range_vector_builder_rejects_non_range_expr():
    with pytest.raises(Exception):
        RangeVectorBuilder(ast_node=NumberLiteral(1.0))


def test_register_unknown_builder_type_raises():
    # Ensure asking for an unknown type errors clearly by using a valid enum member
    # that is very unlikely to be registered in tests. We temporarily clear registry.
    saved = dict(BuilderRegister._builders)
    try:
        BuilderRegister._builders.clear()
        with pytest.raises(ValueError):
            BuilderRegister.get_builder(BuilderType.INSTANT_VECTOR)
    finally:
        BuilderRegister._builders = saved
