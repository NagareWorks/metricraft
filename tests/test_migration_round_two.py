"""Experimental gates and retained convenience operations share immutable Rust nodes."""
import pytest
from metricraft import QueryBuilder as Q


@pytest.mark.parametrize("make", [
    lambda a: a.sort_by_label("job", "instance"),
    lambda a: a.sort_by_label_desc("job"),
    lambda a: a.mad_over_time("5m"),
    lambda a: a.limitk(3).by("job"),
    lambda a: a.limit_ratio(0.5).without("instance"),
    lambda a: a.double_exponential_smoothing("5m"),
    lambda a: a.info(),
    lambda a: a.ts_of_max_over_time("5m"),
    lambda a: a.ts_of_min_over_time("5m"),
    lambda a: a.ts_of_last_over_time("5m"),
])
def test_experimental_opt_in_is_per_build_and_checked_in_nested_nodes(make):
    base = Q.from_metric("up")
    query = make(base).sum()
    with pytest.raises(ValueError, match="experimental_functions"):
        query.build("promql")
    assert query.build("promql", experimental_functions=True)
    with pytest.raises(ValueError, match="experimental_functions"):
        query.build("promql")
    assert base.build("promql") == "up"


@pytest.mark.parametrize("value", [1, "true", None])
def test_feature_option_is_boolean(value):
    with pytest.raises(TypeError, match="must be a bool"):
        Q.from_metric("up").build(experimental_functions=value)


@pytest.mark.parametrize("name", ["sort_by_label", "sort_by_label_desc", "sort_by_label_numeric", "sort_by_label_numeric_desc"])
def test_label_sorting_rejects_empty_and_injected_labels(name):
    a = Q.from_metric("up")
    assert getattr(a, name)("job").build() == name + '(up, "job")'
    for args in [(1,), ("job\n",), ("",)]:
        with pytest.raises((ValueError, TypeError)):
            getattr(a, name)(*args)
    if "numeric" in name:
        with pytest.raises(ValueError, match="MetricsQL-only"):
            getattr(a, name)("job").build("promql", experimental_functions=True)


def test_smoothing_names_types_and_windows_are_explicit():
    a = Q.from_metric("up")
    assert a.holt_winters("10m", 0.2, 0.4).build() == "holt_winters(up[10m], 0.2, 0.4)"
    assert a.range("5m").holt_winters(None).build() == "holt_winters(up[5m], 0.3, 0.3)"
    assert a.smooth_exponential(0.3).build() == "smooth_exponential(up, 0.3)"
    assert a.moving_average("10m").build("promql") == "avg_over_time(up[10m])"
    with pytest.raises(ValueError, match="explicit range"):
        a.double_exponential_smoothing()
    with pytest.raises(ValueError, match="PromQL-only"):
        a.double_exponential_smoothing("5m").build()
    with pytest.raises(ValueError, match="MetricsQL-only"):
        a.holt_winters().build("promql", experimental_functions=True)
    for factor in [0, 1, -0.1, 1.1]:
        with pytest.raises(ValueError, match="strictly between"):
            a.holt_winters(smoothing_factor=factor)
    with pytest.raises(ValueError, match="between"):
        a.smooth_exponential(1.1)
    assert a.range("5m").smooth_exponential(0.3).build() == "smooth_exponential(up[5m], 0.3)"


def test_between_preserves_sample_values_and_rejects_invalid_sources():
    a = Q.from_metric("up").where_eq("job", "api")
    assert a.between(0, 1).build("promql") == '((up{job="api"} >= 0) <= 1)'
    assert a.build() == 'up{job="api"}'
    for lower, upper in [(2, 1), (True, 2), (float("nan"), 2)]:
        with pytest.raises((ValueError, TypeError)):
            a.between(lower, upper)
    for source in [Q.from_scalar(1), a.range("5m")]:
        with pytest.raises(ValueError, match="instant vector"):
            source.between(0, 1)


@pytest.mark.parametrize("name", ["now", "start", "end", "step"])
def test_time_factories_build_query_functions_without_reading_local_clock(name):
    q = getattr(Q, name)()
    assert q.build() == name + "()"
    with pytest.raises(ValueError, match="MetricsQL-only" if name == "now" else "experimental_functions"):
        q.build("promql")
    if name != "now":
        assert q.build("promql", experimental_functions=True) == name + "()"
    if name != "step":
        assert getattr(Q, "from_" + name)().build() == q.build()


def test_generic_calls_cannot_bypass_smoothing_or_feature_validation():
    a = Q.from_metric("up")
    q = Q.function("sort_by_label", a, "job")
    with pytest.raises(ValueError, match="experimental_functions"):
        q.build("promql")
    with pytest.raises(ValueError, match="strictly between"):
        Q.function("holt_winters", a.range("5m"), 1, 0.3)


def test_info_selector_constraint_and_label_join_zero_sources():
    a = Q.from_metric("up")
    assert a.info(Q.from_labels(job="api")).build("promql", experimental_functions=True) == 'info(up, {job="api"})'
    for invalid in [a, a.abs(), Q.from_scalar(1)]:
        with pytest.raises(ValueError):
            a.info(invalid)
    assert a.label_join("dst", ",").build("promql") == 'label_join(up, "dst", ",")'


def test_unnamed_selector_is_typed_escaped_and_shared():
    source = Q.from_labels(job='api"\\', env="")
    expected = '{job="api\\\"\\\\",env=""}'
    assert source.build("promql") == expected
    assert source.where_eq("region", "west").build("promql") == expected[:-1] + ',region="west"}'
    assert source.rate("5m").build("promql") == "rate(" + expected + "[5m])"
    assert source.build() == expected
    for args in [{}, {"job": ""}]:
        query = Q.from_labels(**args)
        assert query.build("metricsql")
        with pytest.raises(ValueError, match="excludes empty"):
            query.build("promql")
    for args in [{"bad\nlabel": "api"}, {"job": 1}]:
        with pytest.raises((TypeError, ValueError)):
            Q.from_labels(**args)
