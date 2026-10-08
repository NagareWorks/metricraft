"""Comparison operations mixin for QueryBuilder."""

from typing import Union, TYPE_CHECKING

from metricraft._legacy.builder.utils import create_binary_operation, maybe_parenthesize
from metricraft._legacy.tree import BinaryExpr, BinaryOperator, NumberLiteral
from metricraft._legacy.exceptions import VMInvalidExpressionError as InvalidExpressionError
from metricraft._legacy.exceptions import InvalidParameterError, validate_numeric_range

if TYPE_CHECKING:
    from metricraft._legacy.builder.impl.base import MetricsBuilder
    from metricraft._legacy.builder.impl.processed_vector import ProcessedVectorBuilder


from metricraft._legacy.contracts import ComparisonMixinBase


class ComparisonMixin(ComparisonMixinBase):
    """
    Mixin providing comparison operations for MetricsBuilder.

    This mixin handles comparison operations (greater than, less than, equal, etc.)
    and includes helper methods for range comparisons.
    """

    def gt(self, other: Union['MetricsBuilder', Union[int, float], str]) -> 'ProcessedVectorBuilder':
        """Greater-than comparison (self > other)."""
        return create_binary_operation(self, BinaryOperator.GT, other)

    def lt(self, other: Union['MetricsBuilder', Union[int, float], str]) -> 'ProcessedVectorBuilder':
        """Less-than comparison (self < other)."""
        return create_binary_operation(self, BinaryOperator.LT, other)

    def ge(self, other: Union['MetricsBuilder', Union[int, float], str]) -> 'ProcessedVectorBuilder':
        """Greater-or-equal comparison (self >= other)."""
        return create_binary_operation(self, BinaryOperator.GE, other)

    def le(self, other: Union['MetricsBuilder', Union[int, float], str]) -> 'ProcessedVectorBuilder':
        """Less-or-equal comparison (self <= other)."""
        return create_binary_operation(self, BinaryOperator.LE, other)

    def eq(self, other: Union['MetricsBuilder', Union[int, float], str]) -> 'ProcessedVectorBuilder':
        """Equality comparison (self == other)."""
        return create_binary_operation(self, BinaryOperator.EQ, other)

    def ne(self, other: Union['MetricsBuilder', Union[int, float], str]) -> 'ProcessedVectorBuilder':
        """Non-equality comparison (self != other)."""
        return create_binary_operation(self, BinaryOperator.NE, other)

    def between(self: 'MetricsBuilder',
                min_value: Union[int,
                float],
                max_value: Union[int,
                float]) -> 'ProcessedVectorBuilder':
        """
        Check if values are between min and max (inclusive).

        This creates a chained comparison expression: expr >= min_value < max_value
        This is more efficient than (expr >= min_value) AND (expr <= max_value)
        as it avoids duplicate evaluation of the expression.

        Args:
            min_value: The minimum value (inclusive).
            max_value: The maximum value (inclusive).

        Returns:
            A ProcessedVectorBuilder instance with the chained comparison expression.

        Examples:
            >>> temperature.between(20, 30)  # 20 <= temperature <= 30
            >>> cpu_usage.between(0.5, 0.8)  # 0.5 <= cpu_usage <= 0.8

        Note:
            Generates optimized PromQL: expr >= min_value <= max_value
            Instead of: (expr >= min_value) AND (expr <= max_value)

        Raises:
            InvalidExpressionError: If base expression is missing.
            InvalidParameterError: If min_value > max_value; or parameters fail numeric checks.
        """
        if self._ast_node is None:
            raise InvalidExpressionError("between comparison")

        # Validate parameters
        validate_numeric_range("min_value", min_value, method="between")
        validate_numeric_range("max_value", max_value, method="between")

        if min_value > max_value:
            raise InvalidParameterError(
                "min_value", min_value,
                f"value <= max_value ({max_value})",
                "between"
            )

        # Parenthesize the expression if needed
        expr_node = maybe_parenthesize(self.ast_node)

        min_node = NumberLiteral(float(min_value))
        max_node = NumberLiteral(float(max_value))

        # Create chained comparison: expr >= min_value <= max_value
        # First: expr >= min_value
        ge_expr = BinaryExpr(expr_node, BinaryOperator.GE, min_node)

        # Then: (expr >= min_value) <= max_value
        # This creates the chained comparison
        chained_expr = BinaryExpr(ge_expr, BinaryOperator.LE, max_node)

        return self._create_new_builder(chained_expr)

    # Magic methods for comparison operations
    def __gt__(self, other):
        return self.gt(other)

    def __lt__(self, other):
        return self.lt(other)

    def __ge__(self, other):
        return self.ge(other)

    def __le__(self, other):
        return self.le(other)

    def __eq__(self, other):
        return self.eq(other)

    def __ne__(self, other):
        return self.ne(other)
