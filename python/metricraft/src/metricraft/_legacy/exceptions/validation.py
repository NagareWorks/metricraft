"""
VM-specific validation error.

This module provides VMValidationError for MetricsQL-specific
query validation scenarios.
"""

from typing import Optional, TYPE_CHECKING
from metricraft._legacy.exceptions.positional import VMPositionalError

if TYPE_CHECKING:
    from metricraft._legacy.ast.astnode import ASTNode


class VMValidationError(VMPositionalError):
    """
    VM-specific validation error with MetricsQL context.
    
    Raised when query validation fails in MetricsQL-specific scenarios.
    """

    def __init__(
            self,
            validation_type: Optional[str] = None,
            issue: Optional[str] = None,
            standard: Optional[str] = None,
            message: Optional[str] = None,
            ast_node: Optional['ASTNode'] = None,
            root_node: Optional['ASTNode'] = None,
            context: Optional[str] = None):

        # Support new message-based constructor
        if message is not None:
            actual_message = message
            # Only use context if explicitly provided
            actual_context = context
        else:
            # Support legacy constructor
            actual_message = f"{validation_type} validation failed: {issue}"
            context_parts = [f"Validation type: {validation_type}"]
            if standard:
                context_parts.append(f"Standard: {standard}")
            actual_context = ", ".join(context_parts)

        super().__init__(actual_message, ast_node=ast_node, root_node=root_node,
                         context=actual_context)
        self.context = actual_context
        self.validation_type = validation_type
        self.issue = issue
        self.standard = standard