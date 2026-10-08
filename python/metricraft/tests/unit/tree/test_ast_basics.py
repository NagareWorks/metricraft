"""Basic AST tree coverage tests for core classes."""

import pytest
from metricraft._legacy.ast.astnode import ASTNode


class N(ASTNode):
    def accept(self, visitor):
        return "ok"


def test_astnode_pos_and_immutability():
    n = N()
    # can set pos before freeze
    n.pos = None
    # freeze and ensure immutability
    n._freeze_node()
    with pytest.raises(AttributeError):
        n.some_attr = 1  # type: ignore[attr-defined]


def test_astnode_accept_and_str():
    n = N()
    assert n.accept(None) == "ok"
    assert N().__str__().startswith("<N>")
