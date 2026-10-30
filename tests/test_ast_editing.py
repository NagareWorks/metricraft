"""Public saved-rule edits preserve ownership, native sharing and validation."""
import gc
import itertools
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import weakref

import pytest

from metricraft import QueryBuilder as Q


def test_saved_alert_edit_shares_unaffected_nodes_and_keeps_both_inputs():
    query = Q.parse('sum by (job) (rate(requests_total[5m])) > 100')
    threshold = Q.from_scalar(200)
    edited = query.replace_at([1], threshold, "promql")
    assert query.build("promql").endswith(" > 100)")
    assert edited.build("promql").endswith(" > 200)")
    assert edited.at_path([0]).shares_node(query.at_path([0]))
    assert edited.at_path([1]).shares_node(threshold)
    assert not edited.shares_node(query)
    assert query.node_kind() == "binary"
    assert query.value_type() == "instant"
    assert threshold.node_kind() == "number"
    assert threshold.value_type() == "scalar"


def test_traversal_handles_outlive_parent_and_source_objects():
    query = Q.parse("up + down")
    parent = weakref.ref(query)
    left, right = query.children()
    selected = query.at_path([0])
    assert selected.shares_node(left)
    assert left.children() == ()
    del query
    gc.collect()
    assert parent() is None
    assert left.build("promql") == "up"
    assert right.build("promql") == "down"
    assert selected.build("promql") == "up"


def test_replacement_changes_only_one_occurrence_of_a_shared_node():
    leaf = Q.from_metric("up")
    query = leaf + leaf
    edited = query.replace_at([1], Q.from_metric("down"), "promql")
    assert edited.build("promql") == "(up + down)"
    assert query.children()[0].shares_node(query.children()[1])
    assert edited.at_path([0]).shares_node(leaf)
    assert not edited.at_path([1]).shares_node(leaf)
    assert query.at_path([]).shares_node(query)
    assert query.replace_at([0], leaf, "promql").shares_node(query)
    other = Q.from_scalar(3)
    assert query.replace_at([], other, "promql").shares_node(other)
    assert not Q.from_metric("up").shares_node(leaf)  # No global interning.


def test_edits_validate_type_dialect_scopes_and_budgets_even_for_no_ops():
    query = Q.parse("up + 1")
    with pytest.raises(ValueError, match="value type"):
        query.replace_at([1], Q.from_metric("down"), "promql")
    for budget in ("max_output_bytes", "max_expanded_nodes"):
        with pytest.raises(ValueError):
            query.replace_at([], query, "promql", **{budget: 1})
    vm = Q.from_metric("up").default(0)
    assert vm.replace_at([], vm).shares_node(vm)
    with pytest.raises(ValueError):
        vm.replace_at([], vm, "promql")
    experimental = Q.parse('sort_by_label(up, "job")', experimental_functions=True)
    with pytest.raises(ValueError, match="experimental_functions"):
        experimental.replace_at([0], Q.from_metric("down"), "promql")
    assert experimental.replace_at(
        [0], Q.from_metric("down"), "promql", experimental_functions=True,
    ).build("promql", experimental_functions=True) == 'sort_by_label(down, "job")'
    assert query.build("promql") == "(up + 1)"


def test_metricsql_binding_edits_recheck_scopes_and_keep_child_order():
    source = Q.from_metric("up")
    query = Q.reference("saved").with_(saved=source)
    binding, body = query.children()
    assert binding.shares_node(source)
    assert body.node_kind() == "template"
    edited = query.replace_at([0], Q.from_metric("down"))
    assert edited.build() == "WITH (saved = down) (saved)"
    assert edited.at_path([1]).shares_node(body)
    with pytest.raises(ValueError, match="unbound|undefined|unknown"):
        query.replace_at([1], Q.reference("missing"))


@pytest.mark.parametrize("path,error", [
    ([True], TypeError), ([1.0], TypeError), ([-1], ValueError), ([2**100], ValueError),
    ([2], ValueError), ([0, 0], ValueError), ([0] * 1025, ValueError),
])
def test_invalid_paths_are_rejected_for_reads_and_edits(path, error):
    query = Q.parse("up + down")
    with pytest.raises(error):
        query.at_path(path)
    with pytest.raises(error):
        query.replace_at(path, Q.from_metric("other"))


def test_path_iteration_is_bounded_and_arguments_are_not_implicitly_parsed():
    query = Q.parse("up + down")
    with pytest.raises(ValueError, match="1024"):
        query.at_path(itertools.repeat(0))
    assert query.at_path(iter([1])).build() == "down"
    with pytest.raises(TypeError, match="replacement"):
        query.replace_at([1], "other")
    with pytest.raises(TypeError, match="other"):
        query.shares_node("up")
    for operation in (lambda: Q().children(), lambda: Q().node_kind(),
                      lambda: query.replace_at([], Q()), lambda: query.shares_node(Q())):
        with pytest.raises(ValueError, match="start with"):
            operation()
    from metricraft import _native_editing
    with pytest.raises(RuntimeError, match="does not support AST editing.*matching"):
        _native_editing._bind(SimpleNamespace())


def test_shared_query_supports_concurrent_independent_edits():
    query = Q.parse("up > 10")
    def edit(value):
        result = query.replace_at([1], Q.from_scalar(value), "promql")
        assert result.at_path([0]).shares_node(query.at_path([0]))
        return result.build("promql")
    with ThreadPoolExecutor(max_workers=8) as executor:
        assert list(executor.map(edit, range(32))) == ["(up > %d)" % i for i in range(32)]
    assert query.build("promql") == "(up > 10)"
