"""Base AST node implementation for time series query languages."""

from abc import ABC, abstractmethod
from typing import Any, Optional, TypeVar, TYPE_CHECKING

from metricraft._legacy.ast.position import Position

if TYPE_CHECKING:  # pragma: no cover
    from .visitor import ASTVisitor

T = TypeVar('T')


class ASTNode(ABC):
    """
    Base class for all AST nodes in time series query languages.
    
    This provides the generic interface that can be implemented by
    specific database query language AST nodes (MetricsQL, InfluxQL, etc.).
    """

    def __init__(self):
        self._position: Optional[Position] = None
        # Defer freezing to allow subclasses to set position
        self._init_complete = False

    @property
    def pos(self) -> Optional[Position]:
        """Get the position information for this node."""
        return self._position
    
    @pos.setter  
    def pos(self, pos: Optional[Position]) -> None:
        """Set the position information for this node."""
        self._position = pos

    def _freeze_node(self) -> None:
        """Freeze the node after initialization is complete."""
        object.__setattr__(self, '_frozen', True)
        object.__setattr__(self, '_init_complete', True)

    def __setattr__(self, name: str, value: Any) -> None:
        """Prevent modification of attributes after initialization."""
        # Allow setting attributes during initialization and position updates
        if (not hasattr(self, '_frozen') or 
            name in ('_frozen', '_position', '_init_complete') or
            not getattr(self, '_init_complete', False)):
            super().__setattr__(name, value)
        else:
            raise AttributeError(
                f"Cannot modify immutable AST node attribute '{name}' "
                f"on {self.__class__.__name__} after initialization"
            )

    @abstractmethod
    def accept(self, visitor: 'ASTVisitor') -> Any:
        """
        Accept a visitor for AST traversal.
        
        This implements the visitor pattern, allowing different operations
        to be performed on AST nodes without modifying the node classes.
        
        Args:
            visitor: The visitor to accept
            
        Returns:
            The result of the visitor operation
        """
        pass
    
    def __str__(self) -> str:
        """String representation of the AST node."""
        return f"<{self.__class__.__name__}>"
