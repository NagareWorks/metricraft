"""The stateless constructor replaces the configured provider factory."""

import pytest
from metricraft import QueryBuilder


def test_empty_factory_can_be_reused_without_state():
    factory = QueryBuilder()
    first = factory.from_metric("a")
    second = factory.from_metric("b")
    assert first.build() == "a"
    assert second.build() == "b"
    with pytest.raises(ValueError, match="start with"):
        factory.build()


def test_constructor_rejects_former_provider_arguments():
    with pytest.raises(TypeError, match=r"build\(mode"):
        QueryBuilder(db_type="vm", instance="default")


def test_immutable_base_cannot_be_reinitialized():
    query = QueryBuilder.from_metric("up")
    with pytest.raises(AttributeError, match="immutable"):
        query.__init__()
    assert query.build() == "up"
