"""Regression contracts for structured syntax, dialects and native ownership."""
import gc
import json

import pytest
from metricraft import QueryBuilder as Q

DURATION = ("promql-duration-expr",)
EXTENDED = ("promql-extended-range-selectors",)
FILL = ("promql-binop-fill-modifiers",)


def test_info_data_label_selector_exception_does_not_leak():
    data = Q.from_labels(k="")
    info = Q.from_metric("up").info(data)
    assert info.build("promql", experimental_functions=True) == 'info(up, {k=""})'
    assert info.analyze()["complexity"]["output_bytes"] == len('info(up, {k=""})')
    for query in (data, info + data, data.info(Q.from_labels(k="x"))):
        with pytest.raises(ValueError, match="excludes empty"):
            query.build("promql", experimental_functions=True)


@pytest.mark.parametrize("pattern", [r"\141", r"\0", r"\07", r"[\141-\143]", r"\Q\141\E"])
def test_unnamed_re2_octal_matchers_keep_the_original_pattern(pattern):
    query = Q.from_labels().where_regex("job", pattern)
    assert query.build("promql") == '{job=~' + json.dumps(pattern) + '}'


@pytest.mark.parametrize("pattern", [r"\1", r"\12"])
def test_re2_backreferences_are_not_mistaken_for_octal(pattern):
    with pytest.raises(ValueError, match="regex"):
        Q.from_labels().where_regex("job", pattern)


def test_scoped_templates_are_immutable_and_do_not_leak_bindings():
    x = Q.reference("x")
    f = Q.template("x", body=x.rate("5m"))
    call = Q.template_call("f", Q.from_metric("a"))
    bound = call.with_(f=f)
    assert bound.build() == "WITH (f(x) = rate(x[5m])) (f(a))"
    del f, x
    gc.collect()
    assert bound.build() == "WITH (f(x) = rate(x[5m])) (f(a))"
    with pytest.raises(ValueError, match="unbound"):
        call.build()
    with pytest.raises(ValueError, match="MetricsQL-only"):
        bound.build("promql")


@pytest.mark.parametrize("make,error", [
    (lambda: Q.reference("x").build(), "unbound"),
    (lambda: Q.reference("x").with_(y=1).build(), "unbound"),
    (lambda: Q.reference("x").with_(x=Q.reference("x")).build(), "unbound"),
    (lambda: Q.reference("x").with_(x=Q.reference("y"), y=1).build(), "unbound"),
    (lambda: Q.template_call("f", 1).with_(f=Q.template(body=Q.from_scalar(1))).build(), "invalid template call"),
    (lambda: Q.reference("f").with_(f=Q.template(body=Q.from_scalar(1))).build(), "invalid template call"),
    (lambda: Q.template(body=Q.from_scalar(1)).build(), "definitions"),
    (lambda: Q.template("x", "x", body=Q.reference("x")), "duplicate"),
    (lambda: Q.reference("x) or up"), "invalid reference"),
    (lambda: Q.reference("x", kind="raw"), "invalid reference type"),
    (lambda: Q.reference("x", kind="string").with_(x=1).build(), "wrong declared type"),
])
def test_invalid_scope_and_syntax_fail_before_producing_a_string(make, error):
    with pytest.raises(ValueError, match=error):
        make()


def test_nested_scope_shadows_outer_binding_without_mutating_it():
    ref = Q.reference("x")
    inner = ref.with_(x=2)
    outer = (ref + inner).with_(x=1)
    assert outer.build() == "WITH (x = 1) ((x + WITH (x = 2) (x)))"
    assert inner.build() == "WITH (x = 2) (x)"


def test_computed_selector_strings_remain_escaped_data():
    prefix = Q.reference("prefix", kind="string")
    selected = Q.from_labels().where_eq("__name__", prefix + 'suffix"} or up').with_(prefix="safe_")
    assert selected.build() == 'WITH (prefix = "safe_") ({__name__=prefix + "suffix\\\"} or up"})'
    assert selected.analyze()["complexity"]["output_bytes"] == len(selected.build().encode())


@pytest.mark.parametrize("name", ['up} or down', '"', '温度', '123', 'Inf', 'NaN', 'WITH'])
def test_metric_names_are_values_and_cannot_introduce_operators(name):
    q = Q.from_metric(name)
    assert q.build("promql") == '{__name__=' + json.dumps(name, ensure_ascii=False) + '}'
    assert q.analyze()["complexity"]["output_bytes"] == len(q.build().encode())


def test_selector_alternatives_keep_each_conjunction_and_shared_base():
    a, b = Q.from_metric("a"), Q.from_metric("b")
    q = a.or_selector(b).where_eq("job", "api")
    assert q.build() == '{__name__="a",job="api" or __name__="b",job="api"}'
    assert a.build() == "a"
    with pytest.raises(ValueError, match="MetricsQL-only"):
        q.build("promql")


@pytest.mark.parametrize("op,value,valid", [
    ("=", "", False), ("!=", "", True), ("!=", "api", False),
    ("=~", ".*", False), ("=~", ".+", True), ("!~", ".*", True),
    ("!~", ".+", False), ("=~", r"\Qapi.+\E", True), ("=~", r"\Q\E", False),
])
def test_prom_selector_excludes_empty_using_re2_quoting(op, value, valid):
    q = Q.from_labels().where("job", op, value)
    assert q.build("metricsql")
    if valid:
        assert q.build("promql")
    else:
        with pytest.raises(ValueError, match="excludes empty"):
            q.build("promql")


def test_duration_features_are_opted_in_per_build():
    q = Q.from_metric("a").range(Q.step() * 2).rate()
    with pytest.raises(ValueError, match="experimental feature"):
        q.build("promql")
    assert q.build("promql", features=DURATION) == "rate(a[(step() * 2)])"
    with pytest.raises(ValueError, match="experimental feature"):
        q.build("promql")
    assert Q.from_duration("1h30m").build() == "5400"
    assert Q.from_numeric_literal("1_000Ki").build() == "1024000"


@pytest.mark.parametrize("duration", [lambda: Q.time(), lambda: Q.from_scalar(float("inf")),
                                      lambda: Q.from_scalar(1).eq(2).bool(), lambda: Q.step() / 0])
def test_duration_expression_rejects_unsupported_nodes(duration):
    with pytest.raises(ValueError, match="duration expressions|must be finite"):
        Q.from_metric("a").range(duration()).rate().build("promql", features=DURATION)


@pytest.mark.parametrize("make,features", [
    (lambda a,b: a.range("5m").anchored().rate(), EXTENDED),
    (lambda a,b: a.range("5m").smoothed().rate(), EXTENDED),
    (lambda a,b: (a+b).fill(0), FILL),
])
def test_experimental_syntax_is_prom_only_and_needs_its_own_flag(make, features):
    q = make(Q.from_metric("a"), Q.from_metric("b"))
    with pytest.raises(ValueError):
        q.build("promql", experimental_functions=True)
    assert q.build("promql", features=features)
    with pytest.raises(ValueError, match="PromQL-only"):
        q.build("metricsql")


def test_time_modifiers_cannot_be_duplicated_across_structured_variants():
    a = Q.from_metric("a")
    for q, operation in [(a.at(Q.end()), lambda q: q.at(1)),
                         (a.at(1), lambda q: q.at(Q.end())),
                         (a.offset(Q.step()), lambda q: q.offset("1m")),
                         (a.offset("1m"), lambda q: q.offset(Q.step()))]:
        with pytest.raises(ValueError, match="already set"):
            operation(q)


def test_sort_overload_and_implicit_types_have_precise_dialects():
    q = Q.from_metric("a").sort_by_label()
    assert q.build("promql", experimental_functions=True) == "sort_by_label(a)"
    with pytest.raises(ValueError, match="PromQL-only"):
        q.build("metricsql")
    q = Q.from_scalar(1).sum()
    assert q.build() == "sum (1)"
    with pytest.raises(ValueError, match="MetricsQL-only"):
        q.build("promql")


def test_histogram_quantiles_fluent_form_selects_the_upstream_argument_order():
    q = Q.from_metric("a").histogram_quantiles("phi", 0.5, 0.9)
    assert q.build() == 'histogram_quantiles("phi", 0.5, 0.9, a)'
    assert q.build("promql", experimental_functions=True) == 'histogram_quantiles(a, "phi", 0.5, 0.9)'
    assert q.analyze()["complexity"]["output_bytes"] == len(q.build())
    with pytest.raises(ValueError, match="experimental_functions"):
        q.build("promql")


@pytest.mark.parametrize("modifier,function", [("anchored", "avg_over_time"), ("smoothed", "resets")])
def test_extended_ranges_reject_functions_without_boundary_semantics(modifier, function):
    q = getattr(Q.from_metric("a").range("5m"), modifier)()
    with pytest.raises(ValueError, match="does not accept"):
        getattr(q, function)()


def test_literal_string_prefixes_and_empty_vm_overloads():
    q = ("prefix_" + Q.reference("s", kind="string")).with_(s="suffix")
    assert q.build() == 'WITH (s = "suffix") ("prefix_" + s)'
    a = Q.from_metric("a")
    for name in ("label_set", "label_keep", "label_del", "union"):
        assert getattr(a, name)().build() == name + "(a)"
    assert Q.function("union").build() == "union()"
    assert Q.function("range_normalize").build() == "range_normalize()"


def test_outliers_iqr_preserves_the_upstream_single_argument_contract():
    a, b = Q.from_metric("a"), Q.from_metric("b")
    assert a.outliers_iqr().build() == "outliers_iqr (a)"
    with pytest.raises(ValueError, match="exactly one"):
        a.aggregate("outliers_iqr", b)
    assert a.build() == "a"


def test_selector_alternatives_distribute_shared_filters_without_changing_branches():
    a, b, c = (Q.from_metric(name) for name in ("a", "b", "c"))
    inner = a.or_selector(b).where_eq("job", "api")
    query = inner.or_selector(c).where_eq("env", "prod")
    assert query.build() == ('{__name__="a",job="api",env="prod" or '
                             '__name__="b",job="api",env="prod" or __name__="c",env="prod"}')
    assert query.analyze()["complexity"]["output_bytes"] == len(query.build())
    assert inner.build() == '{__name__="a",job="api" or __name__="b",job="api"}'
    empty = Q.from_labels().or_selector(a).where_eq("job", "api")
    assert empty.build() == '{job="api" or __name__="a",job="api"}'
    assert empty.analyze()["complexity"]["output_bytes"] == len(empty.build())


def test_computed_filter_bindings_do_not_inherit_outer_selector_filters():
    a, b = Q.from_metric("a"), Q.from_metric("b")
    value = Q.from_string("api").with_(unrelated=a.or_selector(b))
    query = a.or_selector(b).where_eq("job", value)
    assert query.build().count('job=') == 2
    assert query.analyze()["complexity"]["output_bytes"] == len(query.build())


def test_selector_or_exponential_text_is_rejected_before_expansion():
    root = Q.from_metric("a")
    for _ in range(256):
        root = root.or_selector(root)
    filtered = root.where_eq("job", "api")
    with pytest.raises(ValueError, match="max_output_bytes"):
        filtered.build()


@pytest.mark.parametrize("value", [0, -1, float("inf"), float("nan")])
def test_structured_range_rejects_invalid_literal_windows(value):
    with pytest.raises(ValueError, match="positive"):
        Q.from_metric("a").range(Q.from_scalar(value))
