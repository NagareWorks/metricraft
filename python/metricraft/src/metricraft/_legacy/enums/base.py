"""
Base classes for function and operator enumerations.

This module provides base functionality for all enumeration classes
to support better error reporting and type safety.
"""

from enum import Enum


class OperationEnum(Enum):
    """Base class for all operation enumerations with error message support."""

    @property
    def operation_name(self) -> str:
        """Get a human-readable name for this operation for error messages."""
        # Default implementation that subclasses should override
        return f"operation ({self.value})"

    @property
    def error_context(self) -> str:
        """Get error context string for this operation."""
        return f"{self.operation_name} operation"


class FunctionEnum(Enum):
    """Base class for all function enumerations with error message support."""

    @property
    def function_name(self) -> str:
        """Get the function name (same as value for functions)."""
        return self.value

    @property
    def error_context(self) -> str:
        """Get error context string for this function."""
        return f"{self.function_name}() function"


class ModifierEnum(Enum):
    """Base class for modifier enumerations with error message support."""

    @property
    def modifier_name(self) -> str:
        """Get the modifier name (same as value for modifiers)."""
        return self.value

    @property
    def error_context(self) -> str:
        """Get error context string for this modifier."""
        return f"{self.modifier_name} modifier"
