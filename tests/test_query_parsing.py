"""Public parsing, ownership, explicit budgets and compatibility contracts."""
import copy
import gc
import pickle
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from types import SimpleNamespace

import pytest

from metricraft import ParseError, QueryBuilder as Q


def test_parsed_query_composes_and_owns_its_source():
    source = 'rate(requests_total{job="api"}[5m])'
    parsed = Q.parse(source)
    del source
    gc.collect()
    assert parsed.sum().by("job").build("promql") == 'sum by (job) (rate(requests_total{job="api"}[5m]))'
    assert parsed.build("promql") == 'rate(requests_total{job="api"}[5m])'
    assert copy.copy(parsed) is parsed
    assert copy.deepcopy(parsed) is parsed
    assert not hasattr(parsed, "__dict__")
    with pytest.raises(AttributeError, match="immutable"):
        parsed._handle = None
    assert Q.from_string("up + 1").build() == '"up + 1"'


def test_parse_errors_report_utf8_byte_ranges_and_recover():
    source = '{"温度"} + @'
    with pytest.raises(ParseError) as failure:
        Q.parse(source)
    error = failure.value
    assert isinstance(error, ValueError)
    assert error.kind == "syntax"
    assert (error.start, error.end) == (len(source.encode()) - 1, len(source.encode()))
    assert Q.parse("up").build("promql") == "up"
    assert error.kind == "syntax"  # Retaining an exception does not retain mutable TLS state.


def test_nul_in_source_is_parsed_without_truncation():
    with pytest.raises(ParseError) as failure:
        Q.parse("up\0 + other")
    assert (failure.value.start, failure.value.end) == (2, 3)
    assert Q.parse('up{job="a\0b"}').build("promql") == r'up{job="a\u0000b"}'


def test_parse_error_survives_copy_and_worker_process_propagation():
    with ProcessPoolExecutor(max_workers=1) as pool:
        with pytest.raises(ParseError) as failure:
            pool.submit(Q.parse, "up + @").result(timeout=30)
        assert pool.submit(str.lower, "UP").result(timeout=30) == "up"
    for restored in (copy.copy(failure.value), copy.deepcopy(failure.value),
                     pickle.loads(pickle.dumps(failure.value))):
        assert (restored.kind, restored.start, restored.end) == ("syntax", 5, 6)
        assert str(restored) == str(failure.value)


def test_dialect_and_experimental_features_are_explicit():
    with pytest.raises(ParseError, match="MetricsQL WITH") as failure:
        Q.parse("WITH (x = up) x", "metricsql")
    assert failure.value.kind == "unsupported"
    source = 'sort_by_label(up, "job")'
    with pytest.raises(ParseError, match="experimental_functions"):
        Q.parse(source)
    parsed = Q.parse(source, experimental_functions=True)
    with pytest.raises(ValueError, match="experimental_functions"):
        parsed.build("promql")
    assert parsed.build("promql", experimental_functions=True) == source
    source = "rate(up[5m] smoothed)"
    assert Q.parse(source).build("promql") == source
    parsed = Q.parse(source, features=("promql-extended-range-selectors",))
    assert parsed.build("promql", features=("promql-extended-range-selectors",)) == source


@pytest.mark.parametrize("name,value", [
    ("max_input_bytes", 1), ("max_tokens", 1), ("max_work", 1), ("max_depth", 1),
    ("max_output_bytes", 1), ("max_expanded_nodes", 1), ("max_depth", 129),
])
def test_parser_and_render_budgets_are_enforced(name, value):
    with pytest.raises(ParseError):
        Q.parse("up + other", **{name: value})


@pytest.mark.parametrize("value,error", [(True, TypeError), (1.5, TypeError), (0, ValueError), (-1, ValueError), (2**100, ValueError)])
def test_invalid_python_budgets_are_not_coerced(value, error):
    with pytest.raises(error):
        Q.parse("up", max_tokens=value)


def test_invalid_python_arguments_and_missing_optional_symbol():
    with pytest.raises(TypeError, match="source"):
        Q.parse(1)
    with pytest.raises(TypeError, match="bool"):
        Q.parse("up", experimental_functions=1)
    with pytest.raises(ValueError, match="unknown Prometheus feature"):
        Q.parse("up", features=("unknown",))
    from metricraft import _native, _native_parsing
    _native._check_abi(SimpleNamespace(mc_abi_version=lambda: 4))
    with pytest.raises(RuntimeError, match="does not support query parsing.*matching"):
        _native_parsing._bind(SimpleNamespace())
    assert Q.from_metric("up").build("promql") == "up"


def test_parse_errors_and_results_are_independent_between_threads():
    def run(i):
        source = "up + " + " " * i + "@"
        with pytest.raises(ParseError) as failure:
            Q.parse(source)
        assert failure.value.start == len(source) - 1
        return Q.parse("up").where_eq("worker", str(i)).build("promql")
    with ThreadPoolExecutor(max_workers=8) as executor:
        assert list(executor.map(run, range(32))) == ['up{worker="%s"}' % i for i in range(32)]


def test_metricsql_parse_edit_and_release_share_unchanged_subtrees():
    original = Q.parse('sum by(job)(rate(requests_total)) > 100', 'metricsql')
    query = original.at_path([0])
    edited = original.replace_at([1], Q.from_scalar(200), 'metricsql')
    assert edited.at_path([0]).shares_node(query)
    assert original.build('metricsql').endswith(' > 100)')
    assert edited.build('metricsql').endswith(' > 200)')
    with pytest.raises(ValueError):
        original.build('promql')
    del original
    gc.collect()
    assert query.build('metricsql') == 'sum by (job) (rate(requests_total))'
    assert Q.parse(edited.build('metricsql'), 'metricsql').build('metricsql') == edited.build('metricsql')


@pytest.mark.parametrize('mode', ['promql', 'metricsql'])
def test_parse_budgets_cover_both_dialects(mode):
    with pytest.raises(ParseError) as failure:
        Q.parse('sum(rate(up[5m]))', mode, max_tokens=2)
    assert failure.value.kind == 'limit'
