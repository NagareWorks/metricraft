"""Tests for Position dataclass core behavior."""

import pytest
from metricraft._legacy.ast.position import Position
from metricraft._legacy.ast.astnode import ASTNode


class N(ASTNode):
    def accept(self, visitor):
        return None


def test_position_init_and_str():
    p = Position(offset=1, length=2, index_in_parent=0, node_type="X")
    assert "RelPos(" in str(p)


def test_position_negative_values():
    with pytest.raises(ValueError):
        Position(offset=-1)
    with pytest.raises(ValueError):
        Position(length=-1)
    with pytest.raises(ValueError):
        Position(index_in_parent=-1)


def test_position_for_text_and_calculate():
    p = Position.for_text("abcd", offset=3, index=2, node_type="Y")
    assert p.length == 4 and p.offset == 3 and p.index_in_parent == 2
    root = N()
    target = N()
    # default impl returns offset range
    assert p.calculate_absolute_position(root, target) == (3, 7)
