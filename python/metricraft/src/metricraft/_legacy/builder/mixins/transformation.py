"""Transformation functions mixin for QueryBuilder."""

from typing import Union, Optional, TYPE_CHECKING

from metricraft._legacy.builder.utils import (
    create_unary_function,
    create_transformation_function,
    create_label_function,
    create_function_with_args,
)
from metricraft._legacy.enums import SignState, TransformationFunction, DateTimeFunction
from metricraft._legacy.tree import FunctionCall, ParenthesizedExpr, StringLiteral, NumberLiteral, KeepMetricNames, DurationLiteral, SubqueryExpr
from metricraft._legacy.exceptions import VMInvalidExpressionError as InvalidExpressionError
from metricraft._legacy.exceptions import InvalidParameterError, RangeVectorError, validate_numeric_range, validate_labels
from metricraft._legacy.contracts import TransformationMixinBase

if TYPE_CHECKING:
    from metricraft._legacy.builder.impl.base import MetricsBuilder
    from metricraft._legacy.builder.impl.processed_vector import ProcessedVectorBuilder


class TransformationMixin(TransformationMixinBase):
    """
    Mixin providing transformation functions for QueryBuilder.

    This mixin handles various transformation operations like label manipulation,
    sorting, clamping, boolean conversion, etc.
    """

    def parenthesize(self: 'MetricsBuilder') -> 'ProcessedVectorBuilder':
        """
        Wrap the current expression in parentheses.

        This is useful for controlling operator precedence in complex expressions.

        Returns:
            A new QueryBuilder instance of the same type with the parenthesized expression.

        Examples:
            >>> builder.add(other).parenthesize().mul(factor)
            # Results in: (expression + other) * factor
        """
        if self._ast_node is None:
            error = InvalidExpressionError("parenthesize")
            error.set_source_query("<no expression>")
            raise error

        new_node = ParenthesizedExpr(self._ast_node)
        return self._create_new_builder(new_node, self._sign_state)

    def bool(self) -> 'ProcessedVectorBuilder':
        """
        Apply boolean modifier to convert expression to 0 or 1.

        This function converts the expression result to boolean values:
        - Non-zero values become 1
        - Zero values become 0
        - NaN values become 0

        Returns:
            A new ProcessedVectorBuilder with the bool function applied.

        Examples:
            >>> cpu_usage.gt(0.8).bool()  # 1 if cpu > 0.8, 0 otherwise
            >>> (errors.gt(0)).bool()  # 1 if errors > 0, 0 otherwise

        Note:
            This is a PromQL standard function for boolean conversion.
        """
        return create_unary_function(self, TransformationFunction.BOOL)

    def clamp_min(self: 'MetricsBuilder', min_threshold: Union[float, 'MetricsBuilder']) -> 'ProcessedVectorBuilder':
        """
        Set minimum value threshold - replace all values below threshold with threshold.

        Args:
            min_threshold: The minimum threshold value or QueryBuilder expression.

        Returns:
            A new ProcessedVectorBuilder with the clamp_min function applied.

        Examples:
            >>> cpu_usage.clamp_min(0.1)  # Ensure CPU usage is at least 10%
            >>> temperature.clamp_min(freezing_point)  # Use dynamic threshold

        Note:
            PromQL standard function for value clamping.
        Raises:
            InvalidExpressionError: If called without a base expression.
        """
        return create_transformation_function(self, "clamp_min", min_threshold)

    def clamp_max(self: 'MetricsBuilder', max_threshold: Union[float, 'MetricsBuilder']) -> 'ProcessedVectorBuilder':
        """
        Set maximum value threshold - replace all values above threshold with threshold.

        Args:
            max_threshold: The maximum threshold value or QueryBuilder expression.

        Returns:
            A new ProcessedVectorBuilder with the clamp_max function applied.

        Examples:
            >>> cpu_usage.clamp_max(1.0)  # Cap CPU usage at 100%
            >>> response_time.clamp_max(max_acceptable_time)  # Use dynamic threshold

        Note:
            PromQL standard function for value clamping.
        Raises:
            InvalidExpressionError: If called without a base expression.
        """
        return create_transformation_function(self, "clamp_max", max_threshold)

    def timestamp(self) -> 'ProcessedVectorBuilder':
        """
        Convert each sample in the vector to its timestamp.

        Returns the Unix timestamp (seconds since epoch) for each sample point.

        Returns:
            A new ProcessedVectorBuilder with the timestamp function applied.

        Examples:
            >>> cpu_usage.timestamp()  # Get timestamps of CPU usage samples
            >>> alerts.timestamp()  # Get when alerts were triggered

        Note:
            PromQL standard function. Useful for time-based calculations and analysis.
        """
        return create_unary_function(self, TransformationFunction.TIMESTAMP)

    def label_replace(
            self: 'MetricsBuilder',
            target_label: str,
            replacement: str,
            source_label: str,
            regex: str) -> 'ProcessedVectorBuilder':
        """
        Replace or create labels based on regex matching.

        Args:
            target_label: The label name to create or modify.
            replacement: The replacement value, can reference regex capture groups with $1, $2, etc.
            source_label: The source label to match against (empty string to add new label).
            regex: Regular expression with capture groups () to extract parts for replacement.

        Returns:
            A new ProcessedVectorBuilder with the label_replace function applied.

        Examples:
            >>> # Extract port from instance label
            >>> metrics.label_replace("port", "$1", "instance", r".*:(\\d+)")

            >>> # Create environment label from job
            >>> metrics.label_replace("env", "$1", "job", r"(\\w+)-.*")

            >>> # Add constant label
            >>> metrics.label_replace("team", "backend", "", ".*")

        Note:
            PromQL standard function for dynamic label manipulation.
            Performance Warning: Label operations can be expensive with many time series.
        """
        return create_label_function(
            self,
            "label_replace",
            target_label,
            replacement,
            source_label,
            regex)

    def label_join(self: 'MetricsBuilder', target_label: str, separator: str, *source_labels: str) -> 'ProcessedVectorBuilder':
        """
        Join multiple label values into a new label.

        Args:
            target_label: The name of the label to create or modify.
            separator: The separator string to use between joined values.
            *source_labels: Variable number of source label names to join.

        Returns:
            A new ProcessedVectorBuilder with the label_join function applied.

        Examples:
            >>> # Join instance and job into a unique identifier
            >>> metrics.label_join("instance_job", "_", "instance", "job")

            >>> # Create a full service name
            >>> metrics.label_join("full_service", "-", "team", "service", "env")

        Note:
            PromQL standard function for label concatenation.
            Performance Warning: Label operations can be expensive with many time series.
        """
        if not source_labels:
            raise ValueError("At least one source label must be provided")

        return create_label_function(self, "label_join", target_label, separator, *source_labels)

    def label_set(self: 'MetricsBuilder', **labels: str) -> 'ProcessedVectorBuilder':
        """
        Create or modify labels with specified values.

        Args:
            **labels: Keyword arguments where key is label name and value is label value.

        Returns:
            A new ProcessedVectorBuilder with label_set calls applied.

        Examples:
            >>> # Add team and environment labels
            >>> metrics.label_set(team="backend", env="production")

            >>> # Set version label
            >>> metrics.label_set(version="1.0.0")

        Note:
            MetricsQL extension function for simple label assignment.
            Performance Warning: Label operations can be expensive with many time series.
        """
        if self._ast_node is None:
            error = InvalidExpressionError("label_set")
            error.set_source_query("<no expression>")
            raise error

        if not labels:
            raise InvalidParameterError("label", [], "non-empty list")

        result_node = self.ast_node

        # Apply label_set for each label
        for label_name, label_value in labels.items():
            label_name_node = StringLiteral(label_name)
            label_value_node = StringLiteral(label_value)
            result_node = FunctionCall(
                "label_set", [
                    result_node, label_name_node, label_value_node])

        return self._create_new_builder(result_node, self._sign_state)

    def label_del(self: 'MetricsBuilder', *labels: str) -> 'ProcessedVectorBuilder':
        """
        Remove one or more labels from every matching time series.

        Args:
            *labels: Label names to delete from the result set.

        Returns:
            A new ProcessedVectorBuilder with the label_del function applied.

        Examples:
            >>> metrics.label_del("job", "instance")
            >>> metrics.label_del("__name__")

        Note:
            MetricsQL extension specific to VictoriaMetrics. PromQL users should
            avoid calling this function or validate with ``standard=\"PromQL\"``.
        """
        validate_labels(list(labels), "label_del()")
        return create_label_function(self, "label_del", *labels)

    def alias(self, name: str) -> 'ProcessedVectorBuilder':
        """
        Set the time series name (rename the metric).

        Args:
            name: The new metric name.

        Returns:
            A new ProcessedVectorBuilder with the alias function applied.

        Examples:
            >>> cpu_usage.alias("cpu_utilization")
            >>> complicated_expression.alias("simplified_name")

        Note:
            MetricsQL extension function for metric renaming.
        Raises:
            InvalidExpressionError: If called without a base expression.
        """
        return create_label_function(self, "alias", name)

    def sort(self, direction: str = "asc") -> 'ProcessedVectorBuilder':
        """
        Sort time series by their values.

        Args:
            direction: Sort direction, either "asc" (ascending) or "desc" (descending).
                      Defaults to "asc".

        Returns:
            A new ProcessedVectorBuilder with the sort function applied.

        Examples:
            >>> cpu_usage.sort()  # Sort ascending
            >>> cpu_usage.sort("desc")  # Sort descending
            >>> errors.sort("desc")  # Show highest errors first

        Note:
            PromQL standard functions (sort/sort_desc).
        Raises:
            InvalidExpressionError: If called without a base expression.
            InvalidParameterError: If direction is not 'asc' or 'desc'.
        """
        if self._ast_node is None:
            raise InvalidExpressionError("sort")

        if direction not in ("asc", "desc"):
            raise InvalidParameterError(
                "direction", direction, "\'asc\' or \'desc\'")

        function_name = "sort" if direction == "asc" else "sort_desc"
        func_call = FunctionCall(function_name, [self.ast_node])
        return self._create_new_builder(func_call, SignState.NONE)

    def sort_desc(self) -> 'ProcessedVectorBuilder':
        """
        Sort time series by their values in descending order.

        Returns:
            A new ProcessedVectorBuilder with the sort_desc function applied.

        Examples:
            >>> cpu_usage.sort_desc()  # Show highest CPU usage first
            >>> errors.sort_desc()  # Show most errors first

        Note:
            PromQL standard function, equivalent to sort("desc").
        """
        return self.sort("desc")

    def sort_by_label(self: 'MetricsBuilder', *label_names: str) -> 'ProcessedVectorBuilder':
        """
        Sort time series ascending based on the specified label values.

        Args:
            *label_names: One or more label names to sort by. Multiple labels
                         are used as tie-breakers in order.

        Note:
            MetricsQL extension not available in PromQL.

        Examples:
            >>> metrics.sort_by_label("job")
            >>> metrics.sort_by_label("job", "instance")
            >>> metrics.sort_by_label("env", "service", "version")
        """
        if not label_names:
            raise InvalidParameterError("label_names", label_names, "at least one label name", "sort_by_label")

        normalized = [self._normalize_sort_label(label, "sort_by_label") for label in label_names]
        return create_label_function(self, "sort_by_label", *normalized)

    def sort_by_label_desc(self: 'MetricsBuilder', *label_names: str) -> 'ProcessedVectorBuilder':
        """
        Sort time series descending based on the specified label values.

        Args:
            *label_names: One or more label names to sort by. Multiple labels
                         are used as tie-breakers in order.

        Note:
            MetricsQL extension not available in PromQL.

        Examples:
            >>> metrics.sort_by_label_desc("job")
            >>> metrics.sort_by_label_desc("job", "instance")
            >>> metrics.sort_by_label_desc("env", "service", "version")
        """
        if not label_names:
            raise InvalidParameterError("label_names", label_names, "at least one label name", "sort_by_label_desc")

        normalized = [self._normalize_sort_label(label, "sort_by_label_desc") for label in label_names]
        return create_label_function(self, "sort_by_label_desc", *normalized)

    def sort_by_label_numeric(self: 'MetricsBuilder', *label_names: str) -> 'ProcessedVectorBuilder':
        """
        Sort time series ascending by interpreting the label values as numeric.

        Args:
            *label_names: One or more label names to sort by. Multiple labels
                         are used as tie-breakers in order.

        Note:
            MetricsQL extension not available in PromQL.

        Examples:
            >>> metrics.sort_by_label_numeric("port")
            >>> metrics.sort_by_label_numeric("port", "instance")
            >>> metrics.sort_by_label_numeric("priority", "service")
        """
        if not label_names:
            raise InvalidParameterError("label_names", label_names, "at least one label name", "sort_by_label_numeric")

        normalized = [self._normalize_sort_label(label, "sort_by_label_numeric") for label in label_names]
        return create_label_function(self, "sort_by_label_numeric", *normalized)

    def sort_by_label_numeric_desc(self: 'MetricsBuilder', *label_names: str) -> 'ProcessedVectorBuilder':
        """
        Sort time series descending by interpreting the label values as numeric.

        Args:
            *label_names: One or more label names to sort by. Multiple labels
                         are used as tie-breakers in order.

        Note:
            MetricsQL extension not available in PromQL.

        Examples:
            >>> metrics.sort_by_label_numeric_desc("port")
            >>> metrics.sort_by_label_numeric_desc("port", "instance")
            >>> metrics.sort_by_label_numeric_desc("priority", "service")
        """
        if not label_names:
            raise InvalidParameterError("label_names", label_names, "at least one label name", "sort_by_label_numeric_desc")

        normalized = [self._normalize_sort_label(label, "sort_by_label_numeric_desc") for label in label_names]
        return create_label_function(self, "sort_by_label_numeric_desc", *normalized)

    @staticmethod
    def _normalize_sort_label(label_name: str, function_name: str) -> str:
        if not isinstance(label_name, str):
            raise InvalidParameterError(
                "label_name", label_name, "non-empty string", function_name)
        normalized = label_name.strip()
        if not normalized:
            raise InvalidParameterError(
                "label_name", label_name, "non-empty string", function_name)
        return normalized

    def day_of_week(self) -> 'ProcessedVectorBuilder':
        """
        Convert timestamp to day of week (0=Sunday, 6=Saturday).

        Returns:
            A new ProcessedVectorBuilder with the day_of_week function applied.

        Examples:
            >>> QueryBuilder.from_time().day_of_week()  # Current day of week
            >>> metrics.timestamp().day_of_week()  # Day of week for metric timestamps

        Note:
            MetricsQL extension function for time analysis.
        """
        return create_unary_function(self, DateTimeFunction.DAY_OF_WEEK)

    def day_of_month(self) -> 'ProcessedVectorBuilder':
        """
        Convert timestamp to day of month (1-31).

        Returns:
            A new ProcessedVectorBuilder with the day_of_month function applied.

        Examples:
            >>> QueryBuilder.from_time().day_of_month()  # Current day of month
            >>> alerts.timestamp().day_of_month()  # Day of month for alerts

        Note:
            MetricsQL extension function for time analysis.
        """
        return create_unary_function(self, DateTimeFunction.DAY_OF_MONTH)

    def day_of_year(self) -> 'ProcessedVectorBuilder':
        """
        Convert timestamp to day of year (1-366).

        Returns:
            A new ProcessedVectorBuilder with the day_of_year function applied.

        Examples:
            >>> QueryBuilder.from_time().day_of_year()  # Current day of year
            >>> metrics.timestamp().day_of_year()  # Day of year for metrics

        Note:
            MetricsQL extension function for time analysis.
        """
        return create_unary_function(self, DateTimeFunction.DAY_OF_YEAR)

    def hour(self) -> 'ProcessedVectorBuilder':
        """
        Get the hour (0-23) for timestamp values.

        Returns:
            A new ProcessedVectorBuilder with the hour function applied.

        Examples:
            >>> timestamp().hour()  # Current hour
            >>> metric.timestamp().hour()  # Hour for metric timestamps

        Note:
            PromQL Standard: Available in both PromQL and MetricsQL.
        """
        return create_unary_function(self, DateTimeFunction.HOUR)

    def minute(self) -> 'ProcessedVectorBuilder':
        """
        Get the minute (0-59) for timestamp values.

        Returns:
            A new ProcessedVectorBuilder with the minute function applied.

        Examples:
            >>> timestamp().minute()  # Current minute
            >>> metric.timestamp().minute()  # Minute for metric timestamps

        Note:
            PromQL Standard: Available in both PromQL and MetricsQL.
        """
        return create_unary_function(self, DateTimeFunction.MINUTE)

    def month(self) -> 'ProcessedVectorBuilder':
        """
        Get the month (1-12) for timestamp values.

        Returns:
            A new ProcessedVectorBuilder with the month function applied.

        Examples:
            >>> timestamp().month()  # Current month
            >>> metric.timestamp().month()  # Month for metric timestamps

        Note:
            PromQL Standard: Available in both PromQL and MetricsQL.
        """
        return create_unary_function(self, DateTimeFunction.MONTH)

    def year(self) -> 'ProcessedVectorBuilder':
        """
        Get the year for timestamp values.

        Returns:
            A new ProcessedVectorBuilder with the year function applied.

        Examples:
            >>> timestamp().year()  # Current year
            >>> metric.timestamp().year()  # Year for metric timestamps

        Note:
            PromQL Standard: Available in both PromQL and MetricsQL.
        """
        return create_unary_function(self, DateTimeFunction.YEAR)

    def dedup(self) -> 'ProcessedVectorBuilder':
        """
        Remove duplicate time series from the result.

        Returns:
            A new ProcessedVectorBuilder with the dedup function applied.

        Examples:
            >>> metrics.dedup()  # Remove duplicate series
            >>> union_result.dedup()  # Clean up after union operations

        Note:
            MetricsQL extension function for result deduplication.
            Performance Warning: Can be expensive with large result sets.
        Raises:
            InvalidExpressionError: If called without a base expression.
        """
        return create_unary_function(self, TransformationFunction.DEDUP)

    def moving_average(self, duration: str = "5m") -> 'ProcessedVectorBuilder':
        """
        Calculate moving average over the specified time window.

        Args:
            duration: Time range for the moving average (e.g., "5m", "1h"). Defaults to "5m".

        Returns:
            A new ProcessedVectorBuilder with the moving_average function applied.

        Examples:
            >>> cpu_usage.moving_average("10m")  # 10-minute moving average
            >>> response_time.moving_average("1h")  # 1-hour moving average

        Note:
            MetricsQL extension function for smoothing time series data.
            Performance Warning: Can be computationally intensive with large time ranges.
        """
        if self._ast_node is None:
            raise InvalidExpressionError("moving_average")

        # First convert to range vector, then apply moving_average
        range_expr = self.range(duration)
        if not hasattr(
                range_expr,
                '_ast_node') or range_expr._ast_node is None:
            raise RangeVectorError(
                "moving_average",
                duration if "duration" in locals() else "unknown",
                "Failed to create range vector")

        func_call = FunctionCall("moving_average", [range_expr._ast_node])
        return self._create_new_builder(func_call, SignState.NONE)

    def smooth_exponential(
            self,
            smoothing_factor: float) -> 'ProcessedVectorBuilder':
        """
        Apply exponential smoothing to the time series.

        Args:
            smoothing_factor: The smoothing factor (0-1). Higher values give more weight to recent values.

        Returns:
            A new ProcessedVectorBuilder with the smooth_exponential function applied.

        Examples:
            >>> cpu_usage.smooth_exponential(0.3)  # Light smoothing
            >>> noisy_metric.smooth_exponential(0.7)  # Heavy smoothing

        Note:
            MetricsQL extension function for exponential smoothing.
            Performance Warning: Can be computationally intensive.
        """
        if self._ast_node is None:
            raise InvalidExpressionError("smooth_exponential")

        if not (0.0 <= smoothing_factor <= 1.0):
            validate_numeric_range(
                "smoothing_factor", smoothing_factor, 0.0, 1.0)

        sf_node = NumberLiteral(smoothing_factor)
        func_call = FunctionCall(
            "smooth_exponential", [
                self.ast_node, sf_node])
        return self._create_new_builder(func_call, SignState.NONE)

    def keep_metric_names(self) -> 'ProcessedVectorBuilder':
        """
        Keep the original metric names after a binary operation.

        Returns:
            A new ProcessedVectorBuilder with the keep_metric_names modifier.

        Note:
            This is a VictoriaMetrics-specific function.
        """
        if self._ast_node is None:
            raise InvalidExpressionError("keep_metric_names")

        keep_names = KeepMetricNames(self.ast_node)
        return self._create_new_builder(keep_names, self._sign_state)

    def union(self, *others: 'MetricsBuilder') -> 'ProcessedVectorBuilder':
        """
        Return the union of multiple time series sets.

        This MetricsQL-specific function combines multiple vector expressions,
        similar to OR but specifically designed for set operations.

        Args:
            *others: Additional QueryBuilder expressions to union with.

        Returns:
            A new ProcessedVectorBuilder with the union operation applied.

        Examples:
            >>> errors.union(warnings, info_logs)  # Combine multiple log types
            >>> cpu_usage.union(memory_usage)  # Combine different metrics

        Note:
            MetricsQL Extension: This function is specific to MetricsQL and not available in PromQL.

            Performance: More efficient than multiple OR operations for large datasets.
        """
        return create_function_with_args(self, "union", list(others), min_args=1)

    def limitk(self, k: Union[int, 'MetricsBuilder']) -> 'ProcessedVectorBuilder':
        """
        Limit the number of time series to k.

        This MetricsQL-specific function limits the result to at most k time series,
        useful for performance optimization and data sampling.

        Args:
            k: Maximum number of time series to return.

        Returns:
            A new ProcessedVectorBuilder limited to k time series.

        Examples:
            >>> cpu_usage.limitk(10)  # Limit to 10 time series
            >>> errors.limitk(100)  # Sample up to 100 error series

        Note:
            MetricsQL Extension: This function is specific to MetricsQL and not available in PromQL.

            Performance: Very useful for limiting large result sets and improving query performance.
        """
        return create_function_with_args(self, "limitk", [k], min_args=1, max_args=1)

    def outliersk(self, k: Union[int, 'MetricsBuilder']) -> 'ProcessedVectorBuilder':
        """
        Return k outlier time series based on their values.

        This MetricsQL-specific function identifies and returns the k most extreme
        (outlier) time series based on statistical analysis.

        Args:
            k: Number of outlier time series to return.

        Returns:
            A new ProcessedVectorBuilder with k outlier time series.

        Examples:
            >>> cpu_usage.outliersk(5)  # Find 5 most unusual CPU patterns
            >>> response_time.outliersk(3)  # Identify 3 outlier response times

        Note:
            MetricsQL Extension: This function is specific to MetricsQL and not available in PromQL.

            Performance Warning: Computationally intensive for large datasets.
            Use Case: Anomaly detection and performance troubleshooting.
        """
        return create_function_with_args(self, "outliersk", [k], min_args=1, max_args=1)

    def subquery(
            self: 'MetricsBuilder',
            range_duration: str,
            resolution: Optional[str] = None) -> 'ProcessedVectorBuilder':
        """
        Create a subquery expression.

        Subqueries allow executing a query over a range of time and evaluating
        it at regular intervals. This is useful for applying range vector functions
        to instant vector queries over time.

        Args:
            range_duration: The time range for the subquery (e.g., "5m", "1h")
            resolution: Optional step size for evaluation (e.g., "1m", "30s")
                       If not provided, Prometheus will use a default step size

        Returns:
            ProcessedVectorBuilder with the subquery expression applied

        Examples:
            rate(cpu_usage[5m]).subquery("10m", "1m")  # rate over 5m, evaluated every 1m for 10m
            max_over_time(http_requests[5m]).subquery("1h")  # max over 5m, for the past hour

        Note:
            MetricsQL supports subqueries with additional optimizations for better performance.

            Performance Warning: Subqueries can be expensive as they execute the inner query
            multiple times. Use appropriate time ranges and resolution values.
        """
        if self._ast_node is None:
            raise InvalidExpressionError("subquery")

        if not range_duration or not range_duration.strip():
            raise InvalidParameterError(
                "range_duration", range_duration, "non-empty string")

        if resolution is not None and not resolution.strip():
            if resolution is not None:
                raise InvalidParameterError(
                    "resolution", resolution, "non-empty string")

        # Create duration literals
        range_duration_literal = DurationLiteral(range_duration)
        step_literal = DurationLiteral(resolution) if resolution else None

        # Create subquery expression
        subquery_expr = SubqueryExpr(
            expr=self.ast_node,  # Apply sign state before aggregation
            range_duration=range_duration_literal,
            step=step_literal
        )

        return self._create_new_builder(subquery_expr, self._sign_state)

    def default(self, value: Union[int, float, 'MetricsBuilder']) -> 'ProcessedVectorBuilder':
        """
        Fill gaps in time series with the specified default value.

        This operator replaces NaN (Not a Number) values and missing data points
        in the time series with the provided default value. It uses the MetricsQL
        'default' binary operator: `<expr> default <value>`.

        Args:
            value: The default value to use for filling gaps. Can be a numeric value
                   or another MetricsBuilder expression.

        Returns:
            A new ProcessedVectorBuilder with gaps filled with the default value.

        Examples:
            >>> cpu_usage.default(0)  # Replace missing CPU data with 0
            >>> response_time.default(100)  # Use 100ms as default for missing response times
            >>> error_rate.default(0.0)  # Assume 0 error rate when data is missing
            >>> metric_a.default(metric_b)  # Use metric_b values as default for metric_a

        Note:
            MetricsQL Extension: This operator is specific to VictoriaMetrics MetricsQL
            and is NOT available in standard Prometheus PromQL.

            When validating for PromQL compatibility, this will trigger a validation error.

            Use Cases:
            - Ensure continuous graphs without gaps
            - Provide fallback values for alerting rules
            - Handle missing data in aggregations
            - Merge metrics with fallback behavior

        Raises:
            InvalidExpressionError: If called without a base expression.
            InvalidParameterError: If value parameter is invalid.
        """
        from metricraft._legacy.builder.utils import create_binary_operation
        from metricraft._legacy.tree import BinaryOperator

        return create_binary_operation(self, BinaryOperator.DEFAULT, value)
