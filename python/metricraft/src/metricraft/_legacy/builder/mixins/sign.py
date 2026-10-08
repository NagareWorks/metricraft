"""Sign operations mixin for QueryBuilder."""

from typing import TypeVar, TYPE_CHECKING

from metricraft._legacy.enums import SignState
from metricraft._legacy.exceptions import VMInvalidExpressionError as InvalidExpressionError
from metricraft._legacy.contracts import SignMixinBase

if TYPE_CHECKING:
    from metricraft._legacy.builder.impl.base import MetricsBuilder

T = TypeVar('T', bound='MetricsBuilder')


class SignMixin(SignMixinBase):
    """
    Mixin providing sign operations (positive/negative) for QueryBuilder.

    This mixin handles unary plus and minus operations, managing sign state
    intelligently to avoid unnecessary nesting while preserving semantics.
    """

    def positive(self: T) -> T:
        """
        Apply a positive sign to this expression.

        This method intelligently manages sign state to avoid unnecessary
        symbol stacking while preserving semantic meaning.

        Returns:
            A new QueryBuilder instance of the same type with positive sign applied.

        Examples:
            >>> cpu_usage.positive()  # +cpu_usage
            >>> (-memory_usage).positive()  # +memory_usage (optimized from +(-memory_usage))

        Note:
            - If current state is NONE: changes to POSITIVE
            - If current state is NEGATIVE: remains NEGATIVE (no stacking)
            - If current state is POSITIVE: remains POSITIVE (no stacking)

            The actual UnaryExpr AST node is only created when the expression
            undergoes transformation (function calls, operations, etc.).
        """
        if self._ast_node is None:
            raise InvalidExpressionError("positive sign")

        sign_state = self._sign_state if self._sign_state != SignState.NONE else SignState.POSITIVE

        return self._create_new_builder(self._ast_node, sign_state)

    def negative(self: T) -> T:
        """
        Apply a negative sign to this expression.

        This method intelligently manages sign state to avoid unnecessary
        symbol stacking while preserving semantic meaning.

        Returns:
            A new QueryBuilder instance of the same type with negative sign applied.

        Examples:
            >>> cpu_usage.negative()  # -cpu_usage
            >>> (+memory_usage).negative()  # -memory_usage (optimized from -(+memory_usage))
            >>> (-disk_usage).negative()  # +disk_usage (double negative becomes positive)

        Note:
            - If current state is NONE: changes to NEGATIVE
            - If current state is POSITIVE: changes to NEGATIVE
            - If current state is NEGATIVE: changes to POSITIVE (double negative)

            The actual UnaryExpr AST node is only created when the expression
            undergoes transformation (function calls, operations, etc.).
        """
        if self._ast_node is None:
            raise InvalidExpressionError("negative sign")

        # Calculate new sign state based on current state
        if self._sign_state == SignState.NEGATIVE:
            # Double negative becomes positive
            new_sign_state = SignState.POSITIVE
        else:
            # NONE or POSITIVE becomes NEGATIVE
            new_sign_state = SignState.NEGATIVE

        return self._create_new_builder(self._ast_node, new_sign_state)

    # Magic methods for unary operations
    def __pos__(self: T) -> T:
        """Magic method for the unary + operator."""
        return self.positive()

    def __neg__(self: T) -> T:
        """Magic method for the unary - operator."""
        return self.negative()
