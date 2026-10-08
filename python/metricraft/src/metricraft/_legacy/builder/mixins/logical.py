"""Logical operations mixin for QueryBuilder."""

from typing import Union, TYPE_CHECKING

from metricraft._legacy.builder.utils import create_binary_operation
from metricraft._legacy.enums import BinaryOperator
from metricraft._legacy.contracts import QueryBuilder, LogicalMixinBase

if TYPE_CHECKING:
    from metricraft._legacy.builder.impl.processed_vector import ProcessedVectorBuilder


class LogicalMixin(LogicalMixinBase):
    """
    Mixin providing logical operations (AND, OR, UNLESS) for QueryBuilder.

    These operations work as set operations on time series:
    - AND: intersection (keep series present in both)
    - OR: union (keep series from either side, left takes precedence)
    - UNLESS: difference (keep series from left that are not in right)
    """

    def and_(self, other: Union['QueryBuilder', Union[int, float], str]) -> 'ProcessedVectorBuilder':
        """Set intersection (A ∩ B) — logical AND.

        - Keeps series present on both sides; values come from the left side.
        - Label matching semantics follow MetricsQL.
        """
        return create_binary_operation(self, BinaryOperator.AND, other)

    def or_(self, other: Union['QueryBuilder', Union[int, float], str]) -> 'ProcessedVectorBuilder':
        """Set union (A ∪ B) — logical OR. Left-side values take precedence if both exist."""
        return create_binary_operation(self, BinaryOperator.OR, other)

    def unless(self, other: Union['QueryBuilder', Union[int, float], str]) -> 'ProcessedVectorBuilder':
        """Set difference (A - B) — logical UNLESS. Removes series from left that match right."""
        return create_binary_operation(self, BinaryOperator.UNLESS, other)

    # Magic methods for logical operations
    def __and__(self, other):
        """& operator: same as and_()."""
        return self.and_(other)

    def __or__(self, other):
        """| operator: same as or_()."""
        return self.or_(other)
