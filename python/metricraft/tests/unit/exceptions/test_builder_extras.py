"""Extra coverage for exceptions.builder advanced branches."""

from unittest.mock import Mock
import pytest

from metricraft._legacy.exceptions.builder import PositionalError, ValidationError
from metricraft._legacy.ast.astnode import ASTNode


class N(ASTNode):
    def accept(self, v):
        return None


def test_positional_error_get_position_info():
    n = N()
    n.pos = Mock(offset=5, length=3, index_in_parent=1, node_type="Type")
    e = PositionalError("m", ast_node=n)
    info = e.get_position_info()
    assert info and info["offset"] == 5 and info["node_type"] == "Type"


def test_format_error_with_source_absolute_and_oob():
    n = N()
    n.pos = Mock(offset=2, length=2, index_in_parent=0, node_type="T")
    e = PositionalError("m", ast_node=n)

    # monkeypatch absolute calculator to within bounds
    e.calculate_absolute_position = lambda: (1, 3)  # type: ignore[assignment]
    out = e.format_error_with_source("abcdef")
    assert "Line" in out and "^" in out

    # out of bounds fallback
    e.calculate_absolute_position = lambda: (100, 105)  # type: ignore[assignment]
    out2 = e.format_error_with_source("abc")
    assert "Absolute position" in out2 or "m" in out2


def test_format_error_with_arrows_relative_and_invalid():
    n = N()
    n.pos = Mock(offset=1, length=3, index_in_parent=0, node_type="T")
    e = PositionalError("m", ast_node=n)

    # prefer absolute when provided
    e.calculate_absolute_position = lambda: (0, 2)  # type: ignore[assignment]
    s = e._format_error_with_arrows("base", "abcd")
    assert "^" in s

    # invalid offset path
    n.pos.offset = 999
    e.calculate_absolute_position = lambda: None  # type: ignore[assignment]
    s2 = e._format_error_with_arrows("base", "short")
    assert s2 == "base"


def test_create_arrow_display_multiline_and_invalid_start():
    n = N()
    e = PositionalError("m", ast_node=n)
    src = "a\nbcdef\nxyz"
    out = e._create_arrow_display("base", src, 2, 5)
    assert "Line 2" in out and "^" in out

    # invalid start
    out2 = e._create_arrow_display("base", src, -1, 0)
    assert out2 == "base"


def test_validation_error_legacy_and_message_paths():
    n = N()
    n.pos = Mock(offset=0, length=1, index_in_parent=0, node_type="T")
    e1 = ValidationError(validation_type="syntax", issue="bad", standard="S")
    assert "syntax" in str(e1)
    e2 = ValidationError(message="msg", ast_node=n)
    assert "msg" in str(e2)


def test_positional_error_enhanced_context_building():
    class P(PositionalError):
        def calculate_absolute_position(self):
            return (4, 7)

    n = N()
    n.pos = Mock(offset=1, length=2, index_in_parent=0, node_type="Node")
    root = N()
    e = P("m", ast_node=n, root_node=root, context="ctx")
    # context was enhanced with abs position and node type
    assert "at chars 4-6" in str(e) or (hasattr(e, "context") and "chars" in e.context)
