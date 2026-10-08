"""
InstantVectorBuilder for MetricsQL Query Builder.

This module provides the InstantVectorBuilder class for building instant vector
selectors in MetricsQL queries.
"""

from typing import Optional
from metricraft._legacy.builder.impl.base import MetricsBuilder
from metricraft._legacy.contracts import InstantVectorBuilderBase
from metricraft._legacy.enums import SignState, MatchType
from metricraft._legacy.tree import (
    MetricSelector,
    LabelMatcher,
)
from metricraft._legacy.tree.nodes.types import NodeType
from metricraft._legacy.visitor import get_query_visitor
from metricraft._legacy.tree.utils.validation import validate_ast_node, escape_promql_string
from metricraft._legacy.builder.impl.register import BuilderRegister
from metricraft._legacy.builder.impl.types import BuilderType


class InstantVectorBuilder(MetricsBuilder, InstantVectorBuilderBase):
    """
    Builder for instant vector selectors.

    This builder represents raw MetricsQL instant vector selectors that can
    be filtered by labels and converted to range vectors. It provides methods
    for adding label filters and time range specifications.

    State transitions:
    - where() methods -> InstantVectorBuilder (more filtered)
    - range() methods -> RangeVectorBuilder
    - Functions/operations -> ProcessedVectorBuilder
    - Arithmetic/comparisons -> ProcessedVectorBuilder
    """

    def __init__(self, ast_node: MetricSelector,
                 sign_state: SignState = SignState.NONE):
        """Initialize with an instant vector selector AST node."""
        super().__init__(ast_node, sign_state)
        if ast_node is not None and ast_node.node_type != NodeType.METRIC_SELECTOR:
            raise TypeError(
                "InstantVectorBuilder requires an MetricSelector AST node")

    def metric(self, name: str) -> 'InstantVectorBuilder':
        """
        Set or replace the metric name while preserving existing label filters.

        If there's already an MetricSelector with label filters, this method
        preserves those filters and only changes the metric name. For other expression
        types, it replaces the entire expression.

        Args:
            name: The metric name to query.

        Returns:
            A new InstantVectorBuilder instance with the updated metric selector.

        Examples:
            >>> builder.metric("cpu_usage")
            >>> builder.where_eq("job", "api").metric("memory_usage")  # Preserves job filter
        """
        # Always create a new MetricSelector to maintain immutability
        if self._ast_node and self._ast_node.node_type is NodeType.METRIC_SELECTOR:
            # Preserve existing label matchers
            new_matchers = [
                LabelMatcher(matcher.name, matcher.op, matcher.value)
                for matcher in self._ast_node.label_matchers
            ]
            ast_node = MetricSelector(
                metric_name=name,
                label_matchers=new_matchers
            )
        else:
            # Create new selector
            ast_node = MetricSelector(metric_name=name)

        return InstantVectorBuilder(ast_node, self._sign_state)

    # ===== Label Filtering Methods =====

    def where(self, label_name: str, operator: str,
              value: Optional[str]) -> 'InstantVectorBuilder':
        """
        Add or replace a label filter for the current expression.

        This is the most flexible filtering method that supports all label matching operators.
        If a filter for the same label name already exists, it will be replaced with the new one.

        Args:
            label_name: The label name to filter on.
            operator: The matching operator ("=", "!=", "=~", "!~").
            value: The label value or regex pattern to match.

        Returns:
            A new InstantVectorBuilder instance with the added or replaced filter.

        Examples:
            >>> builder.where("job", "=", "api-server")
            >>> builder.where("instance", "!=", "localhost")
            >>> builder.where("service", "=~", "web.*")
            >>> builder.where("status", "!~", "5..")

            # Replacing existing filters:
            >>> builder = builder.where("job", "=", "api").where("job", "=", "worker")
            # Result: job="worker" (not both job="api" and job="worker")

        Raises:
            ValueError: If the operator is not supported or if no base expression exists.
            ValidationError: If label name doesn't follow Prometheus conventions.
        """
        if self._ast_node is None:
            raise ValueError(
                "Cannot add label filter without a base expression. Use a from_* method first.")

        # Create the LabelMatcher AST node first
        
        # Map string operators to MatchType enum
        operator_map = {
            "=": MatchType.EQUAL,
            "!=": MatchType.NOT_EQUAL,
            "=~": MatchType.REGEX_MATCH,
            "!~": MatchType.REGEX_NOT_MATCH,
        }

        if operator not in operator_map:
            raise ValueError(
                f"Unsupported operator '{operator}'. Use one of: =, !=, =~, !~")

        match_type = operator_map[operator]

        # Convert None to empty string to support PromQL syntax
        if value is None:
            value = ""

        # Escape special characters early to prevent injection and validation failures
        # This prevents problematic queries from reaching VM and causing DB load
        if match_type in [MatchType.EQUAL, MatchType.NOT_EQUAL]:
            value = escape_promql_string(value)

        # Create the new LabelMatcher - this is what we're validating
        new_matcher = LabelMatcher(label_name, match_type, value)

        # Validate the LabelMatcher AST node with current AST as root context
        # Import here to keep tests' patching of builder.ast.validation effective and avoid cycles
        validation_errors = validate_ast_node(new_matcher, self._ast_node, enable_complexity_validation=False)

        if validation_errors:
            # Build a temporary AST that includes the new (invalid) matcher
            if self._ast_node and self._ast_node.node_type is NodeType.METRIC_SELECTOR:
                temp_matchers = list(self._ast_node.label_matchers or [])
                temp_matchers.append(new_matcher)
                temp_node = MetricSelector(
                    self._ast_node.metric_name,
                    temp_matchers
                )
            else:
                # If base is not a selector, show error within the current AST context as best-effort
                temp_node = self._ast_node

            # Prepare source query for better error rendering
            try:
                source_query = get_query_visitor().visit(temp_node)
            except Exception:
                source_query = None

            # Ensure the error's ast_node/root_node are in the same tree for precise position mapping
            err = validation_errors[0]
            try:
                # If this error is about label value, point to the value StringLiteral we attached
                if hasattr(err, 'message') and "label value" in str(err.message) and hasattr(new_matcher, "_value_string_literal"):
                    err.ast_node = new_matcher._value_string_literal
                # Root should be the temp tree containing the matcher
                err.root_node = temp_node
                if source_query:
                    err.set_source_query(source_query)
            except Exception:
                # If anything goes wrong, still raise original error
                if source_query:
                    try:
                        err.set_source_query(source_query)
                    except Exception:
                        pass
            # Raise with corrected context
            raise err

        # If current node is already a vector selector, add or replace the
        # matcher
        if self._ast_node and self._ast_node.node_type is NodeType.METRIC_SELECTOR:
            new_matchers = []
            found_existing = False

            # Check if label already exists and replace it, otherwise keep
            # existing matchers
            for existing_matcher in self._ast_node.label_matchers:
                if existing_matcher.name == label_name:
                    # Replace the existing matcher with the new validated one
                    new_matchers.append(new_matcher)
                    found_existing = True
                else:
                    # Keep the existing matcher
                    new_matchers.append(existing_matcher)

            # If label doesn't exist, add the new validated matcher
            if not found_existing:
                new_matchers.append(new_matcher)

            new_node = MetricSelector(
                metric_name=self._ast_node.metric_name,
                label_matchers=new_matchers
            )
            return InstantVectorBuilder(new_node, self._sign_state)
        else:
            # For other expressions, this might need different handling
            # For now, we'll wrap it in a more complex structure
            raise NotImplementedError(
                "Adding label filters to non-selector expressions not yet implemented")

    def where_eq(self, label_name: str, value: Optional[str]) -> 'InstantVectorBuilder':
        """
        Add or replace an exact match label filter for the current expression.

        Adds a label matcher with the '=' operator to filter time series
        that have the exact label value specified. If a filter for the same
        label name already exists, it will be replaced.

        Args:
            label_name: The label name to filter on.
            value: The exact value to match.

        Returns:
            A new InstantVectorBuilder instance with the added or replaced filter.

        Examples:
            >>> builder.where_eq("instance", "localhost")
            >>> builder.where_eq("job", "api-server")
            >>> builder.where_eq("status", "200")

            # Replacing existing filter:
            >>> builder = builder.where_eq("job", "api").where_eq("job", "worker")
            # Result: job="worker" (replaces job="api")
        """
        return self.where(label_name, "=", value)

    def where_ne(self, label_name: str, value: Optional[str]) -> 'InstantVectorBuilder':
        """
        Add or replace a not-equal label filter for the current expression.

        Adds a label matcher with the '!=' operator to filter out time series
        that have the specified label value. If a filter for the same
        label name already exists, it will be replaced.

        Args:
            label_name: The label name to filter on.
            value: The value to exclude.

        Returns:
            A new InstantVectorBuilder instance with the added or replaced filter.

        Examples:
            >>> builder.where_ne("instance", "localhost")
            >>> builder.where_ne("status", "404")

            # Replacing existing filter:
            >>> builder = builder.where_eq("status", "200").where_ne("status", "500")
            # Result: status!="500" (replaces status="200")
        """
        return self.where(label_name, "!=", value)

    def where_regex(
            self,
            label_name: str,
            pattern: Optional[str]) -> 'InstantVectorBuilder':
        """
        Add or replace a regex match label filter for the current expression.

        Adds a label matcher with the '=~' operator to filter time series
        whose label values match the specified regular expression. If a filter
        for the same label name already exists, it will be replaced.

        Args:
            label_name: The label name to filter on.
            pattern: The regular expression pattern to match.

        Returns:
            A new InstantVectorBuilder instance with the added or replaced filter.

        Examples:
            >>> builder.where_regex("instance", "web.*")
            >>> builder.where_regex("job", "api-(server|worker)")
            >>> builder.where_regex("status", "2..")

            # Replacing existing filter:
            >>> builder = builder.where_eq("instance", "web01").where_regex("instance", "web.*")
            # Result: instance=~"web.*" (replaces instance="web01")

        Note:
            Performance Warning: Complex regex patterns or patterns that don't anchor
            at the beginning (e.g., ".*pattern") can be slow, especially with many
            time series. Use anchored patterns like "^prefix.*" when possible.
        """
        return self.where(label_name, "=~", pattern)

    def where_not_regex(
            self,
            label_name: str,
            pattern: Optional[str]) -> 'InstantVectorBuilder':
        """
        Add or replace a regex non-match label filter for the current expression.

        Adds a label matcher with the '!~' operator to filter out time series
        whose label values match the specified regular expression. If a filter
        for the same label name already exists, it will be replaced.

        Args:
            label_name: The label name to filter on.
            pattern: The regular expression pattern to exclude.

        Returns:
            A new InstantVectorBuilder instance with the added or replaced filter.

        Examples:
            >>> builder.where_not_regex("instance", "test.*")
            >>> builder.where_not_regex("status", "5..")

            # Replacing existing filter:
            >>> builder = builder.where_regex("status", "2..").where_not_regex("status", "5..")
            # Result: status!~"5.." (replaces status=~"2..")

        Note:
            Performance Warning: Complex regex patterns can impact query performance.
            Use simple patterns and avoid unanchored regex when possible.
        """
        return self.where(label_name, "!~", pattern)


BuilderRegister.register_builder(BuilderType.INSTANT_VECTOR, InstantVectorBuilder)
