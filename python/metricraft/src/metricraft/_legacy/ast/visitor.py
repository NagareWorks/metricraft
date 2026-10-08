"""
Abstract visitor interface for AST traversal.

This module provides a minimal visitor interface that can be implemented
by specific database providers (VM, InfluxDB, etc.) according to their needs.
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Any

from metricraft._legacy.ast.astnode import ASTNode

T = TypeVar('T')


class ASTVisitor(ABC):
    """
    Minimal abstract visitor interface for AST nodes.
    
    Database-specific implementations should extend this interface and provide
    concrete dispatching logic based on their AST node types.
    """

    @abstractmethod
    def visit(self, node: ASTNode) -> Any:
        """
        Visit an AST node and return the result.
        
        Implementations should provide their own dispatching logic based on
        node types and processing requirements.
        
        Args:
            node: The AST node to visit
            
        Returns:
            The result of visiting the node (implementation-specific)
        """
        pass
