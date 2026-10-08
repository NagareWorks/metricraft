"""Arithmetic operations mixin for QueryBuilder."""

from typing import Union, TYPE_CHECKING

from metricraft._legacy.builder.utils import create_binary_operation, create_reverse_binary_operation
from metricraft._legacy.enums import SignState
from metricraft._legacy.enums import BinaryOperator
from metricraft._legacy.contracts import QueryBuilder, ArithmeticMixinBase

if TYPE_CHECKING:
    from metricraft._legacy.builder.impl.processed_vector import ProcessedVectorBuilder


class ArithmeticMixin(ArithmeticMixinBase):
    """Arithmetic operations for QueryBuilder.

    Provides standard arithmetic operators and their reverse (r-ops). Operands
    can be other builder expressions, numeric scalars, or string literals.

    Behavior
    - Inputs: Metrics builder | int | float | str (interpreted as scalar/string literal)
    - Output: ProcessedVectorBuilder wrapping a BinaryExpr
    - Parentheses: Handled automatically to preserve precedence
    - Immutability: Returns new builder instances; does not mutate self
    """

    def add(self,
            other: Union['QueryBuilder', Union[int, float], str]) -> 'ProcessedVectorBuilder':
        """Add this expression to another value.

        Args:
            other: Right-hand operand. Accepts builder, number, or string.

        Returns:
            ProcessedVectorBuilder: New expression representing ``self + other``.

        Examples:
            >>> a.add(1)
            >>> a + 1  # same as add
        """
        return create_binary_operation(self, BinaryOperator.ADD, other, SignState.NONE)

    def sub(self,
            other: Union['QueryBuilder', Union[int, float], str]) -> 'ProcessedVectorBuilder':
        """Subtract another value from this expression.

        Returns a new builder for ``self - other``.
        """
        return create_binary_operation(self, BinaryOperator.SUB, other, SignState.NONE)

    def mul(self,
            other: Union['QueryBuilder', Union[int, float], str]) -> 'ProcessedVectorBuilder':
        """Multiply this expression by another value.

        Returns a new builder for ``self * other``.
        """
        return create_binary_operation(self, BinaryOperator.MUL, other, SignState.NONE)

    def div(self,
            other: Union['QueryBuilder', Union[int, float], str]) -> 'ProcessedVectorBuilder':
        """Divide this expression by another value.

        Returns a new builder for ``self / other``.
        """
        return create_binary_operation(self, BinaryOperator.DIV, other, SignState.NONE)

    def mod(self,
            other: Union['QueryBuilder', Union[int, float], str]) -> 'ProcessedVectorBuilder':
        """Apply modulo operation with another value.

        Returns a new builder for ``self % other``.
        """
        return create_binary_operation(self, BinaryOperator.MOD, other, SignState.NONE)

    def pow(self,
            other: Union['QueryBuilder', Union[int, float], str]) -> 'ProcessedVectorBuilder':
        """Raise this expression to the power of another value.

        Returns a new builder for ``self ** other``.
        """
        return create_binary_operation(self, BinaryOperator.POW, other, SignState.NONE)

    # Magic methods for arithmetic operations
    def __add__(self, other):
        return self.add(other)

    def __sub__(self, other):
        return self.sub(other)

    def __mul__(self, other):
        return self.mul(other)

    def __truediv__(self, other):
        return self.div(other)

    def __mod__(self, other):
        return self.mod(other)

    def __pow__(self, other):
        return self.pow(other)

    # Reverse operations
    def __radd__(self, other):
        return create_reverse_binary_operation(self, BinaryOperator.ADD, other)

    def __rsub__(self, other):
        return create_reverse_binary_operation(self, BinaryOperator.SUB, other)

    def __rmul__(self, other):
        return create_reverse_binary_operation(self, BinaryOperator.MUL, other)

    def __rtruediv__(self, other):
        return create_reverse_binary_operation(self, BinaryOperator.DIV, other)
