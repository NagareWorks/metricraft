import pytest

from metricraft import QueryBuilder
from metricraft._legacy.builder.impl.base import MetricsBuilder
from metricraft._legacy.tree import NumberLiteral, StringLiteral, FunctionCall
from metricraft._legacy.enums.functions import DateTimeFunction


def test_create_new_builder_scalar_and_processed():
    b = MetricsBuilder()
    # NumberLiteral -> Scalar
    nb = b._create_new_builder(NumberLiteral(1.0))
    assert 'build' in dir(nb)
    # StringLiteral -> Scalar
    sb = b._create_new_builder(StringLiteral("x"))
    assert 'build' in dir(sb)
    # time() -> Scalar by special-case
    tb = b._create_new_builder(FunctionCall(DateTimeFunction.TIME, []))
    assert 'build' in dir(tb)


# Note: where() exists only on InstantVectorBuilder; non-selector path cannot be reached via public API safely.
