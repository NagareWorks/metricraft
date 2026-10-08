"""Retained MetricsQL features and public rollup call forms."""
import pytest
from metricraft import QueryBuilder as Q

ROLLUPS = ["mad_over_time", "median_over_time", "mode_over_time", "zscore_over_time",
           "rate_over_sum", "rollup", "rollup_rate"]


@pytest.mark.parametrize("name", ROLLUPS)
def test_vm_rollup_preserves_shared_base_and_nested_capabilities(name):
    base = Q.from_metric("up").where_eq("job", "api")
    query = getattr(base, name)("5m")
    assert query.build() == name + '(up{job="api"}[5m])'
    assert getattr(Q, name).prom_experimental if name == "mad_over_time" else getattr(Q, name).vm_only
    with pytest.raises(ValueError, match="experimental_functions" if name == "mad_over_time" else "MetricsQL-only"):
        query.sum().by("job").build("promql")
    assert base.build("promql") == 'up{job="api"}'


@pytest.mark.parametrize("name", ["rollup", "rollup_rate"])
def test_rollup_optional_result_is_checked(name):
    source = Q.from_metric("up")
    assert getattr(source, name)("5m", result="max").build() == name + '(up[5m], "max")'
    with pytest.raises(ValueError, match="rollup result"):
        getattr(source, name)("5m", result='max") or up')
    with pytest.raises(ValueError, match="requires String"):
        Q.function(name, source, 1)


@pytest.mark.parametrize("name", ["any", "median", "mode", "mad"])
def test_vm_aggregation_keeps_its_mode_in_independent_grouping_branches(name):
    source = Q.from_metric("up")
    aggregate = getattr(source, name)()
    assert aggregate.by("job").build() == name + " by (job) (up)"
    query = aggregate.without("instance")
    assert query.build() == name + " without (instance) (up)"
    with pytest.raises(ValueError, match="MetricsQL-only"):
        query.build("promql")
    assert source.build() == "up"


def test_union_alias_and_outliers_keep_types_and_dialects():
    a, b = Q.from_metric("a"), Q.from_metric("b")
    assert a.union(b).build() == "union(a, b)"
    assert a.alias('new"name').build() == 'alias(a, "new\\"name")'
    assert a.outliersk(3).by("job").build() == "outliersk by (job) (3, a)"
    for q in [a.union(b), a.alias("new_name"), a.outliersk(3).without()]:
        with pytest.raises(ValueError, match="MetricsQL-only"):
            q.sum().build("promql")
    assert a.union(1).build() == "union(a, 1)"
    with pytest.raises(ValueError, match="requires Instant"):
        a.union("one")
    with pytest.raises(ValueError, match="parameter type"):
        a.outliersk("three")


@pytest.mark.parametrize("name", ["irate", "increase", "delta", "idelta", "deriv", "changes",
    "resets", "sum_over_time", "avg_over_time", "min_over_time", "max_over_time",
    "count_over_time", "stddev_over_time", "stdvar_over_time", "last_over_time",
    "present_over_time", "absent_over_time"])
def test_common_rollups_accept_a_window_or_an_existing_range(name):
    source = Q.from_metric("up")
    explicit = getattr(source, name)("5m")
    assert explicit.build("promql") == getattr(source.range("5m"), name)().build("promql")
    with pytest.raises(ValueError, match="MetricsQL-only"):
        getattr(source, name)().build("promql")


@pytest.mark.parametrize("name", ["day_of_month", "day_of_week", "day_of_year", "days_in_month",
                                "hour", "minute", "month", "year"])
def test_date_helpers_use_the_same_signature_checks(name):
    assert getattr(Q.from_metric("up"), name)().build("promql") == name + "(up)"
    query = getattr(Q.from_scalar(1), name)()
    assert query.build("metricsql") == name + "(1)"
    with pytest.raises(ValueError, match="MetricsQL-only"):
        query.build("promql")
