"""Label operations validate the native boundary and preserve reusable inputs."""
import gc
import json

import pytest

from metricraft import QueryBuilder as Q


CASES = [
    ("label_copy", (("job", "service"), ("job", "owner")), ('job', 'service', 'job', 'owner')),
    ("label_move", (("job", "service"),), ('job', 'service')),
    ("label_map", ("job", ("api", "public")), ('job', 'api', 'public')),
    ("label_lowercase", ("job", "instance"), ('job', 'instance')),
    ("label_uppercase", ("job",), ('job',)),
    ("label_match", ("job", "api|worker"), ('job', 'api|worker')),
    ("label_mismatch", ("job", "test.*"), ('job', 'test.*')),
    ("label_transform", ("job", "(api)", "$1-prod"), ('job', '(api)', '$1-prod')),
    ("label_value", ("shard",), ('shard',)),
    ("labels_equal", ("job", "service", "owner"), ('job', 'service', 'owner')),
    ("label_graphite_group", (0, 2), (0, 2)),
    ("drop_common_labels", (), ()),
]


@pytest.mark.parametrize("name,arguments,flat", CASES)
def test_label_functions_share_inputs_and_enforce_nested_dialects(name, arguments, flat):
    source = Q.from_metric("up").where_eq("env", "prod")
    before = source.build("promql")
    derived = getattr(source, name)(*arguments)
    expected = name + "(" + ", ".join([before] + [json.dumps(v) for v in flat]) + ")"
    assert derived.build("metricsql") == expected
    assert Q.function(name, source, *flat).build() == expected
    with pytest.raises(ValueError, match="MetricsQL-only"):
        derived.sum().build("promql")
    assert source.build("promql") == before
    del source
    gc.collect()
    assert derived.build() == expected


@pytest.mark.parametrize("name,arguments", [
    ("label_copy", ("job",)), ("label_move", ("job",)),
    ("label_map", ("job", "api")),
    ("label_lowercase", ()), ("label_uppercase", ()),
    ("label_match", ("job",)), ("label_mismatch", ("job", ".*", "extra")),
    ("label_transform", ("job", ".*")), ("label_value", ("job", "extra")),
    ("labels_equal", ("job",)), ("label_graphite_group", ()),
    ("label_graphite_group", ("0",)),
    ("drop_common_labels", ("up",)),
])
def test_generic_calls_cannot_bypass_arity_and_type_validation(name, arguments):
    with pytest.raises(ValueError):
        Q.function(name, Q.from_metric("up"), *arguments)


@pytest.mark.parametrize("name,arguments,flat", CASES)
def test_functions_allow_vm_numeric_conversions_and_reject_strings(name, arguments, flat):
    for source in (Q.from_scalar(1), Q.from_metric("up").range("5m")):
        query = Q.function(name, source, *flat)
        assert query.build("metricsql")
        with pytest.raises(ValueError, match="MetricsQL-only"):
            query.build("promql")
    with pytest.raises(ValueError, match="requires Instant"):
        Q.function(name, Q.from_string("up"), *flat)


@pytest.mark.parametrize("bad_label", ["", "bad\nlabel", "job\t"])
def test_all_label_name_positions_are_validated(bad_label):
    source = Q.from_metric("up")
    for name, _, flat in CASES:
        # Strings in these positions are label names, not regexes or values.
        positions = range(len(flat)) if name in {
            "label_copy", "label_move", "label_lowercase", "label_uppercase", "labels_equal"
        } else (0,) if name not in {"label_graphite_group", "drop_common_labels"} else ()
        for position in positions:
            args = list(flat)
            args[position] = bad_label
            with pytest.raises(ValueError, match="invalid label name"):
                Q.function(name, source, *args)


@pytest.mark.parametrize("pair", ["ab", ["a", "b"], ("a",), ("a", "b", "c"), ("a", 1)])
def test_mapping_pairs_are_unambiguous(pair):
    source = Q.from_metric("up")
    for method, prefix in [(source.label_copy, ()), (source.label_move, ()), (source.label_map, ("job",))]:
        with pytest.raises(TypeError, match="mapping"):
            method(*prefix, pair)


def test_empty_and_ordered_mappings_and_escaped_values():
    source = Q.from_metric("up")
    assert source.label_copy().build() == "label_copy(up)"
    assert source.label_move().build() == "label_move(up)"
    assert source.label_map("job").build() == 'label_map(up, "job")'
    assert source.label_move(("job", "service"), ("service", "owner")).build() == (
        'label_move(up, "job", "service", "service", "owner")'
    )
    value = 'a"} or up{job="\\\n\r\t'
    encoded = json.dumps(value)
    assert source.label_map("job", (value, value)).build() == f'label_map(up, "job", {encoded}, {encoded})'
    assert source.label_transform("job", value, value).build() == f'label_transform(up, "job", {encoded}, {encoded})'


def test_variadic_vectors_remain_live_after_owner_release():
    a, b = Q.from_metric("a"), Q.from_metric("b")
    query = a.drop_common_labels(b)
    del a, b
    gc.collect()
    assert query.build() == "drop_common_labels(a, b)"
    with pytest.raises(ValueError, match="argument count"):
        Q.function("drop_common_labels")
