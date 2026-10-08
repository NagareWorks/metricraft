"""Behavioral tests for the migrated function, modifier and time surfaces."""

import pytest

from metricraft import QueryBuilder as Q


def test_binary_modifier_order_and_shared_base():
    original = Q.from_metric("a").gt(Q.from_metric("b"))
    modified = original.group_left("zone").bool().on("job")
    assert modified.build("promql") == "(a > bool on (job) group_left (zone) b)"
    assert original.build("promql") == "(a > b)"


def test_range_omission_is_a_vm_only_call_form():
    base = Q.from_metric("up")
    implicit = base.rate()
    explicit = base.rate("5m")
    assert implicit.build("metricsql") == "rate(up)"
    with pytest.raises(ValueError, match="MetricsQL-only"):
        implicit.sum().build("promql")
    assert explicit.build("promql") == "rate(up[5m])"
    assert implicit.build("metricsql") == "rate(up)"


def test_scalar_comparison_bool_is_checked_at_build():
    query = Q.from_scalar(1).eq(2)
    with pytest.raises(ValueError, match="require bool"):
        query.build("promql")
    assert query.bool().build("promql") == "(1 == bool 2)"


def test_label_constraints_are_conjunctive_and_the_metric_is_fixed():
    base = Q.from_metric("a").where_eq("tenant", "one")
    selected = base.where_eq("tenant", "two")
    assert selected.build() == 'a{tenant="one",tenant="two"}'
    assert base.build() == 'a{tenant="one"}'
    assert not hasattr(base, "metric")
    with pytest.raises(ValueError, match="not implemented"):
        base._unary("rename_metric", "b")


def test_time_modifiers_are_pure_and_preserve_subquery_structure():
    base = Q.from_metric("up").rate("5m").sum()
    query = base.subquery("1h", "1m").at("end").offset("-5m").max_over_time()
    assert (
        query.build("promql")
        == "max_over_time((sum (rate(up[5m])))[1h:1m] @ end() offset -5m)"
    )
    assert base.build() == "sum (rate(up[5m]))"


def test_label_strings_do_not_become_syntax():
    query = Q.from_metric("up").label_replace("dst", '$1"\\', "src", '(.*)"')
    assert (
        query.build("promql")
        == 'label_replace(up, "dst", "$1\\"\\\\", "src", "(.*)\\"")'
    )
    assert (
        Q.from_metric("up").label_set(job='x"').build()
        == 'label_set(up, "job", "x\\"")'
    )


@pytest.mark.parametrize(
    "operation", ["label_set", "label_del", "label_keep", "if_", "ifnot"]
)
def test_vm_metadata_cannot_be_lost_by_wrapping(operation):
    base = Q.from_metric("up")
    query = (
        base.label_set(job="api")
        if operation == "label_set"
        else getattr(base, operation)(base if operation in ("if_", "ifnot") else "job")
    )
    assert getattr(Q, operation).vm_only
    with pytest.raises(ValueError, match="MetricsQL-only"):
        query.sum().build("promql")


@pytest.mark.parametrize(
    "make",
    [
        lambda: Q.from_metric("a").add(1).on("job").build("promql"),
        lambda: Q.from_metric("a").add(Q.from_metric("b")).bool(),
        lambda: Q.from_metric("a").or_(Q.from_metric("b")).group_left(),
        lambda: Q.from_metric("a").and_(1).build("promql"),
        lambda: Q.from_metric("a").add(Q.from_metric("b")).on("job").group_left("job"),
        lambda: Q.from_metric("a").add(Q.from_metric("b")).group_left("job").on("job"),
        lambda: Q.from_metric("a").add(Q.from_metric("b")).on().ignoring(),
        lambda: Q.from_metric("a").add(Q.from_metric("b")).on("job\n"),
        lambda: Q.from_metric("a").offset("1h;up"),
        lambda: Q.from_metric("a").offset("1h").offset("5m"),
        lambda: Q.from_metric("a").at("end").at("start"),
        lambda: Q.from_metric("a").at("1) or up"),
        lambda: Q.from_metric("a").at(float("nan")),
        lambda: Q.from_metric("a").sum().offset("1h").build("promql"),
        lambda: Q.from_scalar(1).subquery("1h").build("promql"),
        lambda: Q.from_metric("a").subquery("1h", "0s"),
        lambda: Q.from_metric("a").subquery("1h", "1m] or up"),
        lambda: Q.from_metric("a").range("5m").range("1h"),
        lambda: Q.from_metric("a").label_replace("bad\nlabel", "$1", "src", "(.*)"),
        lambda: Q.function("label_set", Q.from_metric("a"), "job"),
        lambda: Q.function("sum(up) or", Q.from_metric("a")),
        lambda: Q.function("clamp", Q.from_metric("a"), "raw", 2),
        lambda: Q.from_metric("a").topk("3"),
        lambda: Q.from_metric("a").count_values("bad\nlabel"),
        lambda: Q.from_metric("a").label_join("dst", ",", "bad\nlabel"),
    ],
)
def test_invalid_combinations_fail_without_rendering_raw_fragments(make):
    with pytest.raises(ValueError):
        make()


def test_python_truth_testing_does_not_silently_discard_a_query():
    with pytest.raises(TypeError, match="truth value"):
        bool(Q.from_metric("up"))


def test_generic_function_entry_keeps_type_and_dialect_checks():
    q = Q.function("label_del", Q.from_metric("up"), "job")
    with pytest.raises(ValueError, match="MetricsQL-only"):
        q.build("promql")
    with pytest.raises(ValueError, match="MetricsQL-only"):
        Q.function("vector", Q.from_metric("up")).build("promql")


@pytest.mark.parametrize("name", ["histogram_count", "histogram_sum"])
def test_prometheus_native_histogram_functions_reject_metricsql(name):
    query = getattr(Q.from_metric("a"), name)()
    assert getattr(Q, name).prom_only
    assert query.build("promql") == name + "(a)"
    with pytest.raises(ValueError, match="PromQL-only"):
        query.sum().build("metricsql")
