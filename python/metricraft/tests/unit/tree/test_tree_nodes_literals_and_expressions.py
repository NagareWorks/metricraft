import math

from metricraft._legacy.tree import NumberLiteral, StringLiteral, DurationLiteral
from metricraft._legacy.visitor import QueryToStringVisitor


def test_number_literal_str_and_position_specials():
    # int formatting
    n1 = NumberLiteral(2.0)
    assert str(n1) == "NumberLiteral(2.0)"
    s1 = QueryToStringVisitor().visit(n1)
    assert s1 == "2"
    assert n1.pos.length >= 1

    # float formatting
    n2 = NumberLiteral(2.5)
    assert QueryToStringVisitor().visit(n2) == "2.5"

    # NaN/Inf edge branches in _calculate_relative_position
    n3 = NumberLiteral(float("inf"))
    assert n3.pos.length == 3  # "Inf"
    n4 = NumberLiteral(float("-inf"))
    assert n4.pos.length == 4  # "-Inf"

    n5 = NumberLiteral(math.nan)
    # str() equality for NaN can't be used; just length for "NaN"
    assert n5.pos.length == 3


def test_string_and_duration_literal_codegen_and_pos():
    s = StringLiteral("a\n\t\"b")
    out = QueryToStringVisitor().visit(s)
    # check escaping behavior in codegen
    assert out == '"a\\n\\t\\"b"'
    assert s.pos.length == len('"a\n\t\"b"')

    d = DurationLiteral("10m")
    assert QueryToStringVisitor().visit(d) == "10m"
    # Duration pos is raw length
    assert d.node_type.name == "DURATION_LITERAL"
