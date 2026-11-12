"""Computed durations use the same native parse/edit boundary as saved queries."""
import pytest

from metricraft import ParseError, QueryBuilder as Q

FEATURES = ("promql-duration-expr",)


@pytest.mark.parametrize("source", [
    "rate(up[5m * 2])", "up[range():step()]", "up[range():]",
    "up[5m:step()]", "up offset -(1h * 2)", "up[(0)]",
])
def test_duration_feature_is_explicit_on_parse_and_build(source):
    with pytest.raises(ParseError):
        Q.parse(source)
    parsed = Q.parse(source, features=FEATURES)
    with pytest.raises(ValueError):
        parsed.build("promql")
    text = parsed.build("promql", features=FEATURES)
    assert Q.parse(text, features=FEATURES).build("promql", features=FEATURES) == text


def test_duration_edit_shares_selector_and_unchanged_operand():
    query = Q.parse("rate(up[5m * 2])", features=FEATURES)
    edited = query.replace_at([0, 1, 1], Q.from_scalar(3), "promql", features=FEATURES)
    assert edited.at_path([0, 0]).shares_node(query.at_path([0, 0]))
    assert edited.at_path([0, 1, 0]).shares_node(query.at_path([0, 1, 0]))
    assert edited.build("promql", features=FEATURES) == "rate(up[(300 * 3)])"
    assert query.build("promql", features=FEATURES) == "rate(up[(300 * 2)])"


def test_duration_error_spans_and_depth_limit_recover():
    source = '{"温度"}[1 + ]'
    with pytest.raises(ParseError) as failure:
        Q.parse(source, features=FEATURES)
    assert failure.value.kind == "syntax"
    assert (failure.value.start, failure.value.end) == (len(source.encode()) - 1, len(source.encode()))
    with pytest.raises(ParseError) as failure:
        Q.parse("up[" + "(" * 20 + "1" + ")" * 20 + "]", features=FEATURES, max_depth=8)
    assert failure.value.kind == "limit"
    assert Q.parse("up[+5m]").build("promql") == "up[5m]"


def test_literal_duration_output_budget_ignores_discarded_numeric_spelling():
    assert Q.parse("up[1118ms]", max_output_bytes=10).build("promql") == "up[1118ms]"
    with pytest.raises(ParseError) as failure:
        Q.parse("up[1118ms]", max_output_bytes=9)
    assert failure.value.kind == "limit"


def test_offset_sample_arithmetic_is_preserved():
    query = Q.parse("up offset step() + 1", features=FEATURES)
    assert query.build("promql", features=FEATURES) == "((up offset (step())) + 1)"
    with pytest.raises(ParseError):
        Q.parse("up offset (1h) + down", features=FEATURES)
