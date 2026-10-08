"""
RangeVectorBuilder for MetricsQL Query Builder.

This module provides the RangeVectorBuilder class for building range expressions
in MetricsQL queries.
"""

from metricraft._legacy.builder.impl.base import MetricsBuilder
from metricraft._legacy.contracts import RangeVectorBuilderBase
from metricraft._legacy.enums import SignState
from metricraft._legacy.tree import (
    RangeExpr,
)
from metricraft._legacy.exceptions import InvalidParameterError
from metricraft._legacy.builder.impl.register import BuilderRegister
from metricraft._legacy.builder.impl.types import BuilderType


class RangeVectorBuilder(MetricsBuilder, RangeVectorBuilderBase):
    """
    Builder for range expressions.

    This builder represents MetricsQL range expressions that apply a time range
    to an expression. Range expressions must be processed by functions and cannot
    be used directly in most operations.

    State transitions:
    - Functions (rate, increase, etc.) -> ProcessedVectorBuilder
    - Over-time functions -> ProcessedVectorBuilder

    Raises:
    - InvalidParameterError: if initialized with a non-RangeExpr AST node.
    """

    def __init__(
            self,
            ast_node: RangeExpr,
            sign_state: SignState = SignState.NONE):
        """Initialize with a range expression AST node.

        Args:
            ast_node: The RangeExpr node representing `[start:end]` style selector.
            sign_state: Internal sign flag for unary +/- propagation.

        Raises:
            InvalidParameterError: If `ast_node` is not a RangeExpr.
        """
        super().__init__(ast_node, sign_state)
        if not isinstance(ast_node, RangeExpr):
            raise InvalidParameterError(
                "RangeVectorBuilder", ast_node, "RangeExpr AST node")

BuilderRegister.register_builder(BuilderType.RANGE_VECTOR, RangeVectorBuilder)
