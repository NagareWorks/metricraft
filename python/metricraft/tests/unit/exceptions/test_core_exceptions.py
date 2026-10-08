"""Core exceptions tests for framework-level coverage."""

from unittest.mock import Mock, patch
import pytest

from metricraft._legacy.exceptions import (
    QueryBuilderError, PositionalError, InvalidParameterError,
    UnsupportedOperationError, RangeVectorError, AggregationError,
    ValidationError,
    validate_parameter, validate_numeric_range, validate_labels, validate_duration,
    create_positioned_error, create_validation_error_with_position, require_expression,
    create_error_with_source, create_validation_error_with_source,
)
from metricraft._legacy.ast.astnode import ASTNode


class DummyNode(ASTNode):
    def accept(self, visitor):
        return None


def test_query_builder_error_basic():
    err = QueryBuilderError("msg", context="ctx")
    assert "msg" in str(err) and "ctx" in str(err)


def test_positional_error_formatting_with_source():
    node = DummyNode()
    # fake position information
    node.pos = Mock(offset=2, length=3, index_in_parent=0, node_type="Dummy")
    err = PositionalError("oops", ast_node=node)
    # No absolute calculator, falls back gracefully
    s = err.format_error_with_source("abcde")
    assert "oops" in s


def test_invalid_parameter_and_validators():
    with pytest.raises(InvalidParameterError):
        validate_parameter("p", 1, str)
    validate_parameter("p", 1, (int, float))

    # callable returns False
    with pytest.raises(InvalidParameterError):
        validate_parameter("p", 0, lambda x: x > 0)
    # callable raises
    def bad(x):
        raise ValueError("boom")
    with pytest.raises(InvalidParameterError):
        validate_parameter("p", 1, bad)

    with pytest.raises(InvalidParameterError):
        validate_numeric_range("p", -1, min_value=0)
    with pytest.raises(InvalidParameterError):
        validate_numeric_range("p", 11, max_value=10)
    validate_numeric_range("p", 5, min_value=0, max_value=10)

    with pytest.raises(InvalidParameterError):
        validate_labels("bad")
    with pytest.raises(InvalidParameterError):
        validate_labels([])
    with pytest.raises(InvalidParameterError):
        validate_labels(["a", " "])
    validate_labels(["a", "b"])  # ok

    with pytest.raises(InvalidParameterError):
        validate_duration(123)
    with pytest.raises(InvalidParameterError):
        validate_duration("bad")
    validate_duration("5m")
    validate_duration("1h30m")


def test_other_exception_types():
    e = UnsupportedOperationError("mul", "string", reason="n/a")
    assert "mul" in str(e)
    e = RangeVectorError("rate", "5m")
    assert "rate" in str(e)
    e = AggregationError("sum", "issue", "tip")
    assert "sum" in str(e) and "tip" in str(e)


def test_validation_error_ctors():
    n = DummyNode()
    n.pos = Mock(offset=0, length=1, index_in_parent=0, node_type="Dummy")
    e1 = ValidationError(message="m", ast_node=n)
    assert "m" in str(e1)
    e2 = ValidationError(validation_type="syntax", issue="bad", standard="X")
    assert "syntax" in str(e2)


def test_error_factory_helpers():
    n = DummyNode()
    n.pos = Mock(offset=0, length=1, index_in_parent=0, node_type="Dummy")
    e = create_positioned_error(ValidationError, "x", ast_node=n)
    assert isinstance(e, ValidationError)
    # non-ValidationError class path
    class E(Exception):
        def __init__(self, message, **kw):
            super().__init__(message)
            self.kw = kw
    e2 = create_positioned_error(E, "msg", ast_node=n)
    assert isinstance(e2, E)
    e = create_validation_error_with_position("x", ast_node=n)
    assert isinstance(e, ValidationError)
    e = create_error_with_source(ValidationError, "x", "abc", ast_node=n)
    assert isinstance(e, ValidationError)
    e = create_validation_error_with_source("x", "abc", ast_node=n)
    assert isinstance(e, ValidationError)

    # create_error_with_source using a class without set_source_query
    class SimpleErr(Exception):
        def __init__(self, message, **kw):
            super().__init__(message)
    se = create_error_with_source(SimpleErr, "m", "src")
    assert isinstance(se, SimpleErr)

    with pytest.raises(PositionalError):
        require_expression("op")
