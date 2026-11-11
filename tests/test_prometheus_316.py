"""Public construction/parsing contracts for the Prometheus 3.16 baseline."""
import pytest

from metricraft import QueryBuilder as Q

UTF8_NAMES = ("promql-unquoted-utf8-names",)


@pytest.mark.parametrize("strategy", [None, 0, 1, 2, 0.5, float("inf")])
def test_integral_signature_flags_and_roundtrip(strategy):
    source = Q.from_metric("cost")
    query = source.integral("5m", strategy=strategy)
    text = query.build("promql", experimental_functions=True)
    assert Q.parse(text, experimental_functions=True).build(
        "promql", experimental_functions=True) == text
    args = () if strategy is None else (strategy,)
    assert Q.function("integral", source.range("5m"), *args).build(
        "promql", experimental_functions=True) == text
    assert source.build() == "cost"
    with pytest.raises(ValueError, match="experimental_functions"):
        query.build("promql")
    with pytest.raises(ValueError, match="PromQL-only"):
        query.build("metricsql", experimental_functions=True)


def test_integral_rejects_wrong_shapes_and_preserves_edit_sharing():
    window = Q.from_metric("cost").range("5m")
    for args in ((), (window, 0, 1), (window, "left"), (Q.from_metric("cost"),)):
        with pytest.raises((TypeError, ValueError)):
            Q.function("integral", *args)
    with pytest.raises(TypeError):
        window.integral(strategy=True)
    original = window.integral(strategy=0)
    changed = original.replace_at([1], Q.from_scalar(2), "promql", experimental_functions=True)
    assert original.build("promql", experimental_functions=True) == "integral(cost[5m], 0)"
    assert changed.build("promql", experimental_functions=True) == "integral(cost[5m], 2)"
    assert changed.at_path([0]).shares_node(window)


@pytest.mark.parametrize("source", ["rate(up[5m] anchored)", "rate(up[5m] smoothed)", "up smoothed"])
def test_extended_selectors_are_stable_and_old_opt_in_remains_accepted(source):
    parsed = Q.parse(source)
    assert parsed.build("promql") == source
    assert parsed.build("promql", features=("promql-extended-range-selectors",)) == source
    with pytest.raises(ValueError, match="PromQL-only"):
        parsed.build("metricsql")


@pytest.mark.parametrize("source", [
    'http.server.duration{service.name="api",区域="east"}',
    'sum by(service.name,区域)(http.server.duration)',
    '温度 + on(service.name) group_left(区域) 限额',
    'foo..bar', 'foo.', 'Inf.total', 'NaN.total', 'K',
])
def test_unquoted_utf8_names_are_opt_in_and_render_portably(source):
    with pytest.raises(ValueError):
        Q.parse(source)
    query = Q.parse(source, features=UTF8_NAMES)
    # The flag affects input spelling only; output can be parsed without it.
    text = query.build("promql")
    assert Q.parse(text).build("promql") == text
    assert query.build("promql", features=UTF8_NAMES) == text


@pytest.mark.parametrize("name", ["o\u0308", "a\u0345", "a١", "ⅰ", "😀", ".name", "1name"])
def test_unicode_letters_are_not_alphabetic_or_numeric_supersets(name):
    for source in (name, 'up{' + name + '="x"}', 'sum by(' + name + ')(up)'):
        with pytest.raises(ValueError):
            Q.parse(source, features=UTF8_NAMES)
    assert Q.parse(Q.from_metric(name).build("promql")).build("promql")


def test_names_keep_identity_and_utf8_error_spans():
    for name in ("a", "а", "ö", "o\u0308", "K", "K"):
        text = Q.from_metric(name).build("promql")
        assert Q.parse(text).build("promql") == text
    with pytest.raises(ValueError) as error:
        Q.parse("温度😀", features=UTF8_NAMES)
    assert (error.value.start, error.value.end) == (6, 10)


@pytest.mark.parametrize("letter", ['\U00011db0', '\U0001e6c0', '\U000323b0'])
def test_unicode_17_letters_match_the_pinned_prometheus_tables(letter):
    for source in (letter, 'up{' + letter + '="x"}', 'sum by(' + letter + ')(up)'):
        assert Q.parse(source, features=UTF8_NAMES).build("promql")


@pytest.mark.parametrize("source", ["sum by(foo:bar)(up)", "a + on(foo:bar) group_left(:zone) b"])
def test_colon_labels_remain_legacy_only(source):
    assert Q.parse(source).build("promql")
    with pytest.raises(ValueError, match="label name"):
        Q.parse(source, features=UTF8_NAMES)
