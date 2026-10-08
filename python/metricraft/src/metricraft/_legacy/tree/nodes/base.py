from abc import ABC, abstractmethod

from metricraft._legacy.ast import ASTNode
from metricraft._legacy.tree.nodes.types import NodeType


class VMASTNode(ASTNode, ABC):
    """Base class for all AST nodes in the VM query language."""

    @property
    @abstractmethod
    def node_type(self) -> NodeType:
        """Return the type of the AST node."""
        pass