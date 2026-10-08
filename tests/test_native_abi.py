"""Native library compatibility and the Python error boundary."""
from types import SimpleNamespace

import pytest

from metricraft import QueryBuilder as Q
from metricraft import _native


def test_shipped_library_exposes_only_the_immutable_query_abi():
    assert _native.lib.mc_abi_version() == 4
    for symbol in ("mc_node_new_metric", "mc_node_add_child", "mc_node_set_text", "mc_codegen"):
        with pytest.raises(AttributeError):
            getattr(_native.lib, symbol)


def test_old_library_is_rejected_before_binding_expression_functions():
    with pytest.raises(RuntimeError, match="predates.*immutable ABI"):
        _native._check_abi(SimpleNamespace())


def test_incompatible_abi_has_an_actionable_error():
    with pytest.raises(RuntimeError, match=r"expected 4, got 99.*rebuild"):
        _native._check_abi(SimpleNamespace(mc_abi_version=lambda: 99))


def test_constructor_and_build_failure_do_not_poison_later_calls():
    with pytest.raises(ValueError, match="invalid metric"):
        Q.from_metric("up\ndown")
    source = Q.from_metric("up")
    query = source.rate()
    with pytest.raises(ValueError, match="MetricsQL-only"):
        query.build("promql")
    assert query.build("metricsql") == "rate(up)"
    assert source.build("promql") == "up"
