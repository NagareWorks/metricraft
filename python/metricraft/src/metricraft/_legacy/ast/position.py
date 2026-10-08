"""Position information for AST nodes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .astnode import ASTNode


@dataclass(frozen=True)
class Position:
    """
    Relative position information for AST nodes.
    
    This class represents the relative position of an AST node within its parent,
    allowing for immutable AST structures while enabling precise error reporting
    by calculating absolute positions on demand.
    """
    offset: int = 0  # Offset within parent node
    length: int = 0  # Length of this node's text representation
    index_in_parent: int = 0  # Index among sibling nodes (for lists)
    node_type: Optional[str] = None  # Type hint for position calculation

    def __str__(self) -> str:
        return f"RelPos(offset={self.offset}, length={self.length}, index={self.index_in_parent})"

    def __post_init__(self):
        if self.offset < 0:
            raise ValueError("Position offset cannot be negative")
        if self.length < 0:
            raise ValueError("Position length cannot be negative")
        if self.index_in_parent < 0:
            raise ValueError("Index in parent cannot be negative")

    @classmethod
    def for_text(
        cls, 
        text: str, 
        offset: int = 0, 
        index: int = 0, 
        node_type: Optional[str] = None
    ) -> 'Position':
        """
        Create a Position for the given text.
        
        Args:
            text: The text representation of the node
            offset: Offset within parent node (default: 0)
            index: Index among sibling nodes (default: 0)  
            node_type: Optional type hint for position calculation
            
        Returns:
            Position instance with calculated length
        """
        return cls(
            offset=offset,
            length=len(text),
            index_in_parent=index,
            node_type=node_type
        )

    def calculate_absolute_position(self, root_node: 'ASTNode', target_node: 'ASTNode') -> tuple[int, int]:
        """
        Calculate absolute position by traversing AST from root to target node.
        
        Args:
            root_node: Root AST node to start traversal from
            target_node: Target node to find position for
            
        Returns:
            Tuple of (start, end) absolute positions in generated query
        """
        # Implementation would traverse AST and calculate positions
        # For now, return simple offset-based position
        return (self.offset, self.offset + self.length)
