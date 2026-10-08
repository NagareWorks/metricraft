"""
VM-specific invalid expression error.

This module provides VMInvalidExpressionError for MetricsQL-specific
invalid expression scenarios.
"""

from typing import Optional

from metricraft._legacy.exceptions.positional import VMPositionalError
from metricraft._legacy.ast import Position, ASTNode


class VMInvalidExpressionError(VMPositionalError):
    """
    VM-specific invalid expression error.
    
    Raised when attempting to perform operations without a valid base expression
    in the MetricsQL context.
    """

    def __init__(
            self,
            operation: str,
            suggestion: Optional[str] = None,
            position: Optional['Position'] = None,
            ast_node: Optional['ASTNode'] = None,
            root_node: Optional['ASTNode'] = None):
        message = f"Cannot perform '{operation}' without a base expression."
        if suggestion:
            message += f" {suggestion}"
        else:
            message += " Use one of the initialization methods (from_metric, from_query, etc.) first."

        # Handle legacy position parameter
        if position is not None and ast_node is None:
            class FakeNode:
                def __init__(self, pos):
                    self.pos = pos
                    self.__class__.__name__ = "InvalidExpression"

            ast_node = FakeNode(position)

        super().__init__(message, ast_node=ast_node, root_node=root_node,
                         context=f"Operation: {operation}")