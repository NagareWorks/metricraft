"""Mathematical functions mixin for QueryBuilder."""

from typing import Union, TYPE_CHECKING

from metricraft._legacy.builder.utils import create_unary_function, create_function_with_args
from metricraft._legacy.enums import MathFunction
from metricraft._legacy.contracts import QueryBuilder, MathematicalMixinBase

if TYPE_CHECKING:
    from metricraft._legacy.builder.impl.processed_vector import ProcessedVectorBuilder


class MathematicalMixin(MathematicalMixinBase):
    """
    Mixin providing mathematical functions for QueryBuilder.

    This mixin handles mathematical operations like abs(), ceil(), floor(), round(),
    sqrt(), exp(), ln(), trigonometric functions, etc.
    """

    def abs(self) -> 'ProcessedVectorBuilder':
        """Calculate the absolute value."""
        return create_unary_function(self, MathFunction.ABS)

    def ceil(self) -> 'ProcessedVectorBuilder':
        """Round up to the nearest integer."""
        return create_unary_function(self, MathFunction.CEIL)

    def floor(self) -> 'ProcessedVectorBuilder':
        """Round down to the nearest integer."""
        return create_unary_function(self, MathFunction.FLOOR)

    def round(self, to_nearest: Union[float, 'QueryBuilder'] = 1.0) -> 'ProcessedVectorBuilder':
        """
        Round to the nearest multiple of to_nearest.

        Args:
            to_nearest: The value to round to the nearest multiple of.

        Returns:
            A new ProcessedVectorBuilder with the round function applied.
        """
        if to_nearest == 1.0:
            return create_unary_function(self, MathFunction.ROUND)
        else:
            return create_function_with_args(self, "round", [to_nearest], 1, 1)

    def sqrt(self) -> 'ProcessedVectorBuilder':
        """Calculate the square root."""
        return create_unary_function(self, MathFunction.SQRT)

    def exp(self) -> 'ProcessedVectorBuilder':
        """Calculate e^x."""
        return create_unary_function(self, MathFunction.EXP)

    def ln(self) -> 'ProcessedVectorBuilder':
        """Calculate the natural logarithm."""
        return create_unary_function(self, MathFunction.LN)

    def log2(self) -> 'ProcessedVectorBuilder':
        """Calculate the base-2 logarithm."""
        return create_unary_function(self, MathFunction.LOG2)

    def log10(self) -> 'ProcessedVectorBuilder':
        """Calculate the base-10 logarithm."""
        return create_unary_function(self, MathFunction.LOG10)

    # ===== Trigonometric Functions =====

    def sin(self) -> 'ProcessedVectorBuilder':
        """Calculate the sine."""
        return create_unary_function(self, MathFunction.SIN)

    def cos(self) -> 'ProcessedVectorBuilder':
        """Calculate the cosine."""
        return create_unary_function(self, MathFunction.COS)

    def tan(self) -> 'ProcessedVectorBuilder':
        """Calculate the tangent."""
        return create_unary_function(self, MathFunction.TAN)

    def asin(self) -> 'ProcessedVectorBuilder':
        """Calculate the arcsine."""
        return create_unary_function(self, MathFunction.ASIN)

    def acos(self) -> 'ProcessedVectorBuilder':
        """Calculate the arccosine."""
        return create_unary_function(self, MathFunction.ACOS)

    def atan(self) -> 'ProcessedVectorBuilder':
        """Calculate the arctangent."""
        return create_unary_function(self, MathFunction.ATAN)

    def atan2(self, x: Union[float, 'QueryBuilder']) -> 'ProcessedVectorBuilder':
        """
        Calculate the two-argument arctangent.

        Args:
            x: The x coordinate value or QueryBuilder expression.

        Returns:
            A new ProcessedVectorBuilder with the atan2 function applied.
        """
        return create_function_with_args(self, "atan2", [x], 1, 1)

    # ===== Hyperbolic Functions =====

    def sinh(self) -> 'ProcessedVectorBuilder':
        """Calculate the hyperbolic sine."""
        return create_unary_function(self, MathFunction.SINH)

    def cosh(self) -> 'ProcessedVectorBuilder':
        """Calculate the hyperbolic cosine."""
        return create_unary_function(self, MathFunction.COSH)

    def tanh(self) -> 'ProcessedVectorBuilder':
        """Calculate the hyperbolic tangent."""
        return create_unary_function(self, MathFunction.TANH)

    def asinh(self) -> 'ProcessedVectorBuilder':
        """Calculate the inverse hyperbolic sine."""
        return create_unary_function(self, MathFunction.ASINH)

    def acosh(self) -> 'ProcessedVectorBuilder':
        """Calculate the inverse hyperbolic cosine."""
        return create_unary_function(self, MathFunction.ACOSH)

    def atanh(self) -> 'ProcessedVectorBuilder':
        """Calculate the inverse hyperbolic tangent."""
        return create_unary_function(self, MathFunction.ATANH)

    # ===== Conversion Functions =====

    def deg(self) -> 'ProcessedVectorBuilder':
        """Convert radians to degrees."""
        return create_unary_function(self, "deg")

    def rad(self) -> 'ProcessedVectorBuilder':
        """Convert degrees to radians."""
        return create_unary_function(self, "rad")
