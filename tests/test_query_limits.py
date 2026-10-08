"""Expansion budgets apply at build time while expressions remain immutable."""
import pytest
from metricraft import QueryBuilder as Q


def test_shared_dag_is_rejected_before_expanding_its_query_text():
    root = Q.from_metric("up")
    for _ in range(100):
        root = root + root
    with pytest.raises(ValueError, match="max_output_bytes"):
        root.build("promql")


def test_custom_limits_are_per_call_and_count_utf8_bytes():
    query = Q.from_metric("up").where_eq("job", '中"\\\n')
    text = query.build("promql")
    size = len(text.encode("utf-8"))
    assert query.build("promql", max_output_bytes=size, max_expanded_nodes=2) == text
    with pytest.raises(ValueError, match="max_output_bytes"):
        query.build("promql", max_output_bytes=size - 1)
    with pytest.raises(ValueError, match="max_expanded_nodes"):
        query.build("promql", max_expanded_nodes=1)
    assert query.build("promql") == text


@pytest.mark.parametrize("name", ["max_output_bytes", "max_expanded_nodes"])
@pytest.mark.parametrize("value", [0, -1, 2**128, True, 1.2, "100"])
def test_invalid_budgets_do_not_wrap_at_the_ffi_boundary(name, value):
    with pytest.raises((TypeError, ValueError)):
        Q.from_metric("up").build(**{name: value})


def test_long_chain_releases_python_owners_without_recursive_native_drop():
    root = Q.from_metric("up")
    for _ in range(10_000):
        root = root.abs()
    assert root.build("promql").startswith("abs(abs(")
    del root
