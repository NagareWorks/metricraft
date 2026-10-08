"""
ScalarBuilder for MetricsQL Query Builder.

This module provides the ScalarBuilder class for building scalar expressions
in MetricsQL queries.
"""

from typing import TYPE_CHECKING
from metricraft._legacy.builder.utils import create_unary_function
from metricraft._legacy.builder.impl.base import MetricsBuilder
from metricraft._legacy.contracts import ScalarBuilderBase
from metricraft._legacy.builder.impl.register import BuilderRegister
from metricraft._legacy.builder.impl.types import BuilderType
from metricraft._legacy.enums import SignState, TransformationFunction
from metricraft._legacy.ast import ASTNode

if TYPE_CHECKING:
    from metricraft._legacy.builder.impl.processed_vector import ProcessedVectorBuilder


class ScalarBuilder(MetricsBuilder, ScalarBuilderBase):
    """
    Builder for scalar values and expressions.

    This builder represents MetricsQL scalar values, including:
    - Numeric literals
    - Time functions (time(), now(), start(), end())
    - Scalar results from aggregations or functions

    Scalars can be used in arithmetic operations and comparisons with vectors,
    and support most mathematical functions.
    """

    def __init__(
            self,
            ast_node: ASTNode,
            sign_state: SignState = SignState.NONE):
        """Initialize with any AST node representing a scalar value.

        Args:
            ast_node: AST node that evaluates to a scalar in MetricsQL.
            sign_state: Internal sign flag for unary +/- propagation.
        """
        super().__init__(ast_node, sign_state)

    def vector(self) -> 'ProcessedVectorBuilder':
        """
        Convert this scalar expression to an instant vector.

        This method wraps the scalar in a vector context, allowing it to be
        used where an instant vector is required. The resulting instant vector
        will have a single time series with the scalar value.

        Returns:
            A new ProcessedVectorBuilder representing the instant vector.

        Raises:
            InvalidExpressionError: If the scalar cannot be represented as a vector.
                (Provider may impose additional constraints.)
        """
        return create_unary_function(self, TransformationFunction.VECTOR)

BuilderRegister.register_builder(BuilderType.SCALAR, ScalarBuilder)
