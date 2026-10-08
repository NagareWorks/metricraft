"""The public builder is independent of client providers and configuration."""

import pytest
from metricraft import QueryBuilder
from metricraft.config import reset_config


def test_public_builder_exports_are_identical():
    from metricraft.builder import QueryBuilder as builder
    from metricraft.builder.query_builder import QueryBuilder as module
    from metricraft.builder.query_builder import QueryBuilder as implementation

    assert QueryBuilder is builder is module is implementation


def test_factory_needs_no_registered_provider_or_config():
    reset_config()
    assert QueryBuilder().from_metric("up").build("promql") == "up"


def test_mode_is_explicit_and_nested_vm_nodes_are_rejected():
    query = QueryBuilder.from_metric("up").label_del("tmp_label").sum()
    assert query.build("metricsql") == 'sum (label_del(up, "tmp_label"))'
    with pytest.raises(ValueError, match="MetricsQL-only"):
        query.build("promql")
    assert query.build("metricsql") == 'sum (label_del(up, "tmp_label"))'


def test_client_configuration_does_not_choose_query_mode():
    from metricraft.config import register_config
    from metricraft.config import PrometheusConfig

    register_config(PrometheusConfig("http://example.invalid"), instance="prometheus")
    query = QueryBuilder.from_metric("up").default(0)
    assert query.build("metricsql") == "(up default 0)"
    with pytest.raises(ValueError, match="MetricsQL-only"):
        query.build("promql")


def test_build_rejects_unknown_query_mode():
    with pytest.raises(ValueError):
        QueryBuilder.from_metric("up").build("sql")
