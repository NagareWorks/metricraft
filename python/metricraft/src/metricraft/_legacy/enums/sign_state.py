"""
Type definitions and enums for QueryBuilder.

This module contains shared types and enums that are used across
the QueryBuilder implementation to avoid circular imports.
"""

from enum import Enum


class SignState(Enum):
    """Represents the sign state of an expression."""
    NONE = None  # No sign applied
    POSITIVE = "+"  # Positive sign applied
    NEGATIVE = "-"  # Negative sign applied
