"""
ProcessedVectorBuilder for MetricsQL Query Builder.

This module provides the ProcessedVectorBuilder class for building processed vector
expressions in MetricsQL queries.
"""

from metricraft._legacy.builder.impl.base import MetricsBuilder
from metricraft._legacy.contracts import ProcessedVectorBuilderBase
from metricraft._legacy.enums import SignState
from metricraft._legacy.tree import (
    BinaryExpr,
    BinaryModifier,
    AggregationExpr,
    GroupModifier,
)
from metricraft._legacy.exceptions import VMInvalidExpressionError as InvalidExpressionError
from metricraft._legacy.ast import ASTNode
from metricraft._legacy.exceptions import UnsupportedOperationError, validate_labels
from metricraft._legacy.tree.nodes.types import NodeType
from metricraft._legacy.builder.impl.register import BuilderRegister
from metricraft._legacy.builder.impl.types import BuilderType


class ProcessedVectorBuilder(MetricsBuilder, ProcessedVectorBuilderBase):
    """
    Builder for processed vector expressions.

    This builder represents MetricsQL expressions that have been processed
    by functions, operations, or aggregations. These typically have more
    limited operations available compared to raw instant vectors.

    Available operations:
    - Mathematical operations (inherited from QueryBuilder)
    - Comparison operations (inherited from QueryBuilder)
    - Additional functions that work on any vector type
    - Aggregation functions
    """

    def __init__(
            self,
            ast_node: ASTNode,
            sign_state: SignState = SignState.NONE):
        """Initialize with any AST node representing a processed expression."""
        super().__init__(ast_node, sign_state)

    # ===== Vector Matching Modifiers for Logical Operations =====

    def on(self, *labels: str) -> 'ProcessedVectorBuilder':
        """
        Add an 'on' modifier to the last binary operation (if applicable).

        This method works with logical operations (and, or, unless) and comparison
        operations to specify which labels should be considered for matching.

        Args:
            *labels: Label names to match on.

        Returns:
            A new ProcessedVectorBuilder with the 'on' modifier applied.

        Raises:
            InvalidExpressionError: If there is no current expression to modify.
            UnsupportedOperationError: If the current expression is not a binary expression.
            InvalidParameterError: If any label name is invalid (empty, non-string, etc.).

        Examples:
            >>> cpu_usage.and_(memory_usage).on("instance", "job")
            >>> errors.or_(warnings).on("service")
            >>> all_metrics.unless(blacklisted).on("__name__")

        Note:
            Only works if the current expression is a binary operation.
        """
        if self._ast_node is None:
            error = InvalidExpressionError("on modifier")
            error.set_source_query("<no expression>")
            raise error

        # Validate labels
        validate_labels(list(labels), "on")

        # Check if current node is a binary expression
        if self._ast_node.node_type == NodeType.BINARY_EXPR:
            # Create a copy of the binary expression with the modifier
            new_node = BinaryExpr(
                left=self._ast_node.left,
                operator=self._ast_node.operator,
                right=self._ast_node.right,
                modifier=BinaryModifier(
                    matching_type="on",
                    labels=list(labels)),
                return_bool=self._ast_node.return_bool)
            return ProcessedVectorBuilder(new_node, self._sign_state)
        else:
            raise UnsupportedOperationError(
                "on modifier", "non-binary expressions")

    def ignoring(self, *labels: str) -> 'ProcessedVectorBuilder':
        """
        Add an 'ignoring' modifier to the last binary operation (if applicable).

        This method works with logical operations (and, or, unless) and comparison
        operations to specify which labels should be ignored for matching.

        Args:
            *labels: Label names to ignore during matching.

        Returns:
            A new ProcessedVectorBuilder with the 'ignoring' modifier applied.

        Raises:
            InvalidExpressionError: If there is no current expression to modify.
            UnsupportedOperationError: If the current expression is not a binary expression.
            InvalidParameterError: If any label name is invalid (empty, non-string, etc.).

        Examples:
            >>> cpu_usage.and_(memory_usage).ignoring("instance")
            >>> primary.or_(backup).ignoring("pod", "container")
            >>> metrics.unless(excluded).ignoring("job")

        Note:
            Only works if the current expression is a binary operation.
        """
        if self._ast_node is None:
            error = InvalidExpressionError("ignoring modifier")
            error.set_source_query("<no expression>")
            raise error

        # Validate labels
        validate_labels(list(labels), "ignoring")

        # Check if current node is a binary expression
        if self._ast_node.node_type == NodeType.BINARY_EXPR:
            # Create a copy of the binary expression with the modifier
            new_node = BinaryExpr(
                left=self._ast_node.left,
                operator=self._ast_node.operator,
                right=self._ast_node.right,
                modifier=BinaryModifier(
                    matching_type="ignoring",
                    labels=list(labels)),
                return_bool=self._ast_node.return_bool)
            return ProcessedVectorBuilder(new_node, self._sign_state)
        else:
            raise UnsupportedOperationError(
                "ignoring modifier", "non-binary expressions")

    def group_left(self, *labels: str) -> 'ProcessedVectorBuilder':
        """
        Add a 'group_left' modifier to the last binary operation (if applicable).

        This is used for many-to-one and one-to-many vector matching in logical operations.

        Args:
            *labels: Additional labels to include from the left side.

        Returns:
            A new ProcessedVectorBuilder with the 'group_left' modifier applied.

        Raises:
            InvalidExpressionError: If there is no current expression to modify.
            UnsupportedOperationError: If the current expression is not a binary expression.

        Examples:
            >>> info_metrics.and_(values).group_left("version", "build")
            >>> labels_left.or_(labels_right).group_left()

        Note:
            Only works if the current expression is a binary operation.
        """
        if self._ast_node is None:
            error = InvalidExpressionError("group_left modifier")
            error.set_source_query("<no expression>")
            raise error

        # Check if current node is a binary expression
        if self._ast_node.node_type == NodeType.BINARY_EXPR:
            # Create or update the modifier
            existing_modifier = self._ast_node.modifier
            if existing_modifier:
                # Update existing modifier
                new_modifier = BinaryModifier(
                    matching_type=existing_modifier.matching_type,
                    labels=existing_modifier.labels,
                    group_type="group_left",
                    group_labels=list(labels)
                )
            else:
                # Create new modifier
                new_modifier = BinaryModifier(
                    group_type="group_left", group_labels=list(labels))

            new_node = BinaryExpr(
                left=self._ast_node.left,
                operator=self._ast_node.operator,
                right=self._ast_node.right,
                modifier=new_modifier,
                return_bool=self._ast_node.return_bool
            )
            return ProcessedVectorBuilder(new_node, self._sign_state)
        else:
            raise UnsupportedOperationError(
                "group_left modifier", "non-binary expressions")

    def group_right(self, *labels: str) -> 'ProcessedVectorBuilder':
        """
        Add a 'group_right' modifier to the last binary operation (if applicable).

        This is used for many-to-one and one-to-many vector matching in logical operations.

        Args:
            *labels: Additional labels to include from the right side.

        Returns:
            A new ProcessedVectorBuilder with the 'group_right' modifier applied.

        Raises:
            InvalidExpressionError: If there is no current expression to modify.
            UnsupportedOperationError: If the current expression is not a binary expression.

        Examples:
            >>> values.and_(info_metrics).group_right("version", "build")
            >>> labels_left.or_(labels_right).group_right()

        Note:
            Only works if the current expression is a binary operation.
        """
        if self._ast_node is None:
            error = InvalidExpressionError("group_right modifier")
            error.set_source_query("<no expression>")
            raise error

        # Check if current node is a binary expression
        if self._ast_node.node_type == NodeType.BINARY_EXPR:
            # Create or update the modifier
            existing_modifier = self._ast_node.modifier
            if existing_modifier:
                # Update existing modifier
                new_modifier = BinaryModifier(
                    matching_type=existing_modifier.matching_type,
                    labels=existing_modifier.labels,
                    group_type="group_right",
                    group_labels=list(labels)
                )
            else:
                # Create new modifier
                new_modifier = BinaryModifier(
                    group_type="group_right", group_labels=list(labels))

            new_node = BinaryExpr(
                left=self._ast_node.left,
                operator=self._ast_node.operator,
                right=self._ast_node.right,
                modifier=new_modifier,
                return_bool=self._ast_node.return_bool
            )
            return ProcessedVectorBuilder(new_node, self._sign_state)
        else:
            raise UnsupportedOperationError(
                "group_right modifier", "non-binary expressions")

    # ===== Grouping Modifiers (Only for Aggregations) =====

    def by(self, *labels: str) -> 'ProcessedVectorBuilder':
        """
        Add a 'by' grouping modifier to an aggregation expression.

        This method can only be called on aggregation expressions (sum, avg, min, max, etc.).
        It specifies which labels to preserve when performing the aggregation.

        Args:
            *labels: Variable number of label names to group by

        Returns:
            ProcessedVectorBuilder with the 'by' modifier applied

        Raises:
            UnsupportedOperationError: If called on a non-aggregation expression
            InvalidParameterError: If any label name is invalid (empty, non-string, etc.)

        Examples:
            >>> QueryBuilder.from_metric("cpu_usage").sum().by("instance", "job")
            >>> QueryBuilder.from_metric("memory_usage").avg().by("datacenter")

        Note:
            This is equivalent to PromQL's 'by (label1, label2, ...)' clause.
        """
        if not self._ast_node or self._ast_node.node_type is not NodeType.AGGREGATION_EXPR:
            raise UnsupportedOperationError(
                "by() modifier",
                f"non-aggregation expressions (current: {type(self._ast_node).__name__})",
                "Use an aggregation function (sum, avg, min, max, etc.) first"
            )

        # Validate labels
        validate_labels(list(labels), "by")

        # Create a new AggregationExpr with the by grouping instead of mutating
        new_grouping = GroupModifier(is_without=False, labels=list(labels))
        new_node = AggregationExpr(
            operator=self._ast_node.operator,
            expr=self._ast_node.expr,
            parameter=self._ast_node.parameter,
            grouping=new_grouping
        )
        return ProcessedVectorBuilder(new_node, self._sign_state)

    def without(self, *labels: str) -> 'ProcessedVectorBuilder':
        """
        Add a 'without' grouping modifier to an aggregation expression.

        This method can only be called on aggregation expressions (sum, avg, min, max, etc.).
        It specifies which labels to exclude when performing the aggregation.

        Args:
            *labels: Variable number of label names to exclude from grouping

        Returns:
            ProcessedVectorBuilder with the 'without' modifier applied

        Raises:
            UnsupportedOperationError: If called on a non-aggregation expression
            InvalidParameterError: If any label name is invalid (empty, non-string, etc.)

        Examples:
            >>> QueryBuilder.from_metric("cpu_usage").sum().without("instance")
            >>> QueryBuilder.from_metric("memory_usage").avg().without("__name__", "job")

        Note:
            This is equivalent to PromQL's 'without (label1, label2, ...)' clause.
        """
        if not self._ast_node or self._ast_node.node_type is not NodeType.AGGREGATION_EXPR:
            raise UnsupportedOperationError(
                "without() modifier",
                f"non-aggregation expressions (current: {type(self._ast_node).__name__})",
                "Use an aggregation function (sum, avg, min, max, etc.) first"
            )

        # Validate labels
        validate_labels(list(labels), "without")

        # Create a new AggregationExpr with the without grouping instead of
        # mutating
        new_grouping = GroupModifier(is_without=True, labels=list(labels))
        new_node = AggregationExpr(
            operator=self._ast_node.operator,
            expr=self._ast_node.expr,
            parameter=self._ast_node.parameter,
            grouping=new_grouping
        )
        return ProcessedVectorBuilder(new_node, self._sign_state)

BuilderRegister.register_builder(BuilderType.PROCESSED_VECTOR, ProcessedVectorBuilder)
