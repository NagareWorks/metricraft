"""Reject obsolete configuration before creating a native expression."""

import pytest
from metricraft import QueryBuilder


@pytest.mark.parametrize(
    "args,kwargs",
    [
        (("vm",), {}),
        ((), {"unknown": 123}),
        ((), {"db_type": "vm", "instance": "default"}),
    ],
)
def test_constructor_rejects_configuration_with_migration_guidance(args, kwargs):
    with pytest.raises(TypeError, match="takes no configuration.*build"):
        QueryBuilder(*args, **kwargs)
