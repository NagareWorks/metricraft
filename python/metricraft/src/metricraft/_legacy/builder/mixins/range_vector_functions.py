"""Range vector functions mixin for QueryBuilder."""

from typing import TYPE_CHECKING

from metricraft._legacy.builder.utils import create_range_vector_function, create_simple_over_time_function
from metricraft._legacy.enums import SignState, RangeVectorFunction
from metricraft._legacy.tree import RangeExpr, FunctionCall, UnaryExpr, UnaryOperator, DurationLiteral, NumberLiteral
from metricraft._legacy.exceptions import VMInvalidExpressionError as InvalidExpressionError
from metricraft._legacy.exceptions import (
    RangeVectorError,
    validate_numeric_range
)
from metricraft._legacy.tree.nodes.types import NodeType
from metricraft._legacy.contracts import RangeVectorFunctionsMixinBase

if TYPE_CHECKING:
    from metricraft._legacy.builder.impl.base import MetricsBuilder
    from metricraft._legacy.builder.impl.range_vector import RangeVectorBuilder
    from metricraft._legacy.builder.impl.processed_vector import ProcessedVectorBuilder


class RangeVectorFunctionsMixin(RangeVectorFunctionsMixinBase):
    """Range-vector functions for QueryBuilder.

    Handles functions that operate on range vectors (rate/increase/*_over_time, etc.).
    Inputs that are not range vectors are automatically converted via ``range(...)``
    as a MetricsQL enhancement.

    Contract
    - Inputs: instant/processed/scalar builders (auto-converted), or range vectors
    - Output: ProcessedVectorBuilder unless otherwise specified
    - Validation: certain parameters are range-checked and may raise errors
    - Immutability: functions return new builders; the original is not mutated
    """

    def range(self: 'MetricsBuilder', duration: str = "5m") -> 'RangeVectorBuilder':
        """
        Convert this expression to a range vector with the specified duration.

        In MetricsQL, instant vectors, processed vectors, and scalars can be directly
        converted to range vectors for use with range vector functions. This is a
        MetricsQL extension not available in standard PromQL.

        Args:
            duration: The time range duration (e.g., "5m", "1h", "30s"). Defaults to "5m".

        Returns:
            A new RangeVectorBuilder with the range selector.

        Examples:
            >>> cpu_usage.range("5m")  # Instant vector to range vector
            >>> (cpu_usage + 10).range("1h")  # Processed vector to range vector
            >>> QueryBuilder.from_scalar(100).range("30m")  # Scalar to range vector

        Note:
            This is a MetricsQL-specific feature. In PromQL, only instant vector selectors
            can be converted to range vectors directly.

        Raises:
            InvalidExpressionError: If called without a base expression.
        """
        if self._ast_node is None:
            error = InvalidExpressionError("range")
            error.set_source_query("<no expression>")
            raise error

        if self._ast_node.node_type == NodeType.RANGE_EXPR:
            inner_expr = self._ast_node.expr
            if self._sign_state != SignState.NONE:
                inner_expr = UnaryExpr(UnaryOperator.PLUS
                                       if self._sign_state == SignState.POSITIVE
                                       else UnaryOperator.MINUS, inner_expr)
            range_expr = RangeExpr(
                expr=inner_expr,
                range_duration=DurationLiteral(duration)
            )
        else:
            range_expr = RangeExpr(
                expr=self.ast_node,
                range_duration=DurationLiteral(duration)
            )
        return self._create_new_builder(range_expr)

    def rate(self, duration: str = "5m") -> 'ProcessedVectorBuilder':
        """
        Calculate the per-second average rate of increase over the specified time range.

        In MetricsQL, this function can be applied to instant vectors, processed vectors,
        and scalars by automatically converting them to range vectors first.

        Args:
            duration: The time range duration (e.g., "5m", "1h", "30s"). Defaults to "5m".

        Returns:
            A new ProcessedVectorBuilder with the rate function applied.

        Examples:
            >>> cpu_usage.rate("5m")  # rate(cpu_usage[5m])
            >>> (memory_used / memory_total).rate("1h")  # rate((memory_used / memory_total)[1h])

        Note:
            MetricsQL Enhancement: Unlike PromQL, this can be applied to any expression type,
            not just range vectors. The expression is automatically converted to a range vector.

            Performance: Rate calculations are generally efficient and recommended for counter metrics.
        """
        return create_range_vector_function(self, RangeVectorFunction.RATE, duration)

    def irate(self, duration: str = "5m") -> 'ProcessedVectorBuilder':
        """
        Calculate the instantaneous rate based on the last two data points over the time range.

        Args:
            duration: The time range duration (e.g., "5m", "1h", "30s"). Defaults to "5m".

        Returns:
            ProcessedVectorBuilder: Result of applying ``irate`` to the range vector.

        Note:
            MetricsQL Enhancement: Can be applied to any expression type.

            Performance Warning: irate is more sensitive to temporary spikes and may be less
            stable than rate() for alerting. Use with caution in production alerts.
        """
        return create_range_vector_function(self, RangeVectorFunction.IRATE, duration)

    def idelta(self, duration: str = "5m") -> 'ProcessedVectorBuilder':
        """
        Calculate the instant delta (difference based on last two data points).

        Args:
            duration: The time range duration (e.g., "5m", "1h", "30s"). Defaults to "5m".

        Returns:
            A new ProcessedVectorBuilder with the idelta function applied.

        Examples:
            >>> temperature.idelta("5m")  # idelta(temperature[5m])

        Note:
            MetricsQL Enhancement: Can be applied to any expression type.
        """
        return create_range_vector_function(self, RangeVectorFunction.IDELTA, duration)

    def increase(self, duration: str = "5m") -> 'ProcessedVectorBuilder':
        """
        Calculate the total increase over the specified time range.

        Args:
            duration: The time range duration (e.g., "5m", "1h", "30s"). Defaults to "5m".

        Returns:
            A new ProcessedVectorBuilder with the increase function applied.

        Examples:
            >>> requests_total.increase("1h")  # Total requests in the last hour

        Note:
            MetricsQL Enhancement: Can be applied to any expression type.

            Performance: Generally efficient, similar to rate() but returns total change.
        """
        return create_range_vector_function(self, RangeVectorFunction.INCREASE, duration)

    def delta(self, duration: str = "5m") -> 'ProcessedVectorBuilder':
        """
        Calculate the difference between the first and last value over the time range.

        Args:
            duration: The time range duration (e.g., "5m", "1h", "30s"). Defaults to "5m".

        Returns:
            A new ProcessedVectorBuilder with the delta function applied.

        Examples:
            >>> temperature.delta("1h")  # Temperature change over the last hour

        Note:
            MetricsQL Enhancement: Can be applied to any expression type.

            Use Case: Best for gauge metrics to see the change over time.
        """
        return create_range_vector_function(self, RangeVectorFunction.DELTA, duration)

    def changes(self, duration: str = "5m") -> 'ProcessedVectorBuilder':
        """
        Count the number of times the value changed.

        Args:
            duration: The time range duration (e.g., "5m", "1h", "30s"). Defaults to "5m".

        Returns:
            A new ProcessedVectorBuilder with the changes function applied.

        Examples:
            >>> status_code.changes("1h")  # Number of status code changes in the last hour

        Note:
            MetricsQL Enhancement: Can be applied to any expression type.

            Use Case: Useful for tracking state changes in discrete metrics.
        """
        return create_range_vector_function(self, RangeVectorFunction.CHANGES, duration)

    def resets(self, duration: str = "5m") -> 'ProcessedVectorBuilder':
        """
        Count the number of counter resets over the specified time range.

        Args:
            duration: The time range duration (e.g., "5m", "1h", "30s"). Defaults to "5m".

        Returns:
            A new ProcessedVectorBuilder with the resets function applied.

        Examples:
            >>> counter_metric.resets("1h")  # Number of resets in the last hour

        Note:
            MetricsQL Enhancement: Can be applied to any expression type.

            Use Case: Useful for detecting counter resets due to application restarts.
        """
        return create_range_vector_function(self, RangeVectorFunction.RESETS, duration)

    def holt_winters(self: 'MetricsBuilder', duration: str = "5m", smoothing_factor: float = 0.3,
                     trend_factor: float = 0.3) -> 'ProcessedVectorBuilder':
        """
        Apply Holt-Winters exponential smoothing for prediction over the time range.

        Args:
            duration: The time range duration (e.g., "5m", "1h", "30s"). Defaults to "5m".
            smoothing_factor: The smoothing factor for level (0.0-1.0). Defaults to 0.3.
            trend_factor: The smoothing factor for trend (0.0-1.0). Defaults to 0.3.

        Returns:
            A new ProcessedVectorBuilder with the holt_winters function applied.

        Examples:
            >>> cpu_usage.holt_winters("30m", 0.5, 0.5)  # Predict CPU usage trends

        Note:
            MetricsQL Enhancement: Can be applied to any expression type.

            Performance Warning: Holt-Winters is computationally intensive and may impact
            query performance with large time ranges or many series.

        Raises:
            InvalidExpressionError: If called without a base expression.
            InvalidParameterError: If smoothing/trend factors are out of [0.0, 1.0].
            RangeVectorError: If converting to range vector fails.
        """
        if self._ast_node is None:
            error = InvalidExpressionError("holt_winters")
            error.set_source_query("<no expression>")
            raise error

        validate_numeric_range(
            "smoothing_factor",
            smoothing_factor,
            0.0,
            1.0,
            "holt_winters")
        validate_numeric_range(
            "trend_factor",
            trend_factor,
            0.0,
            1.0,
            "holt_winters")

        range_builder = self.range(duration)
        if hasattr(range_builder, '_ast_node') and range_builder._ast_node:
            smoothing_node = NumberLiteral(smoothing_factor)
            trend_node = NumberLiteral(trend_factor)
            func_call = FunctionCall(
                "holt_winters", [
                    range_builder._ast_node, smoothing_node, trend_node])
            return self._create_new_builder(func_call)
        else:
            raise RangeVectorError(
                "holt_winters",
                duration,
                "Failed to create range vector")

    def avg_over_time(self, duration: str = "5m") -> 'ProcessedVectorBuilder':
        """
        Calculate the average value over the specified time range.

        Args:
            duration: The time range duration (e.g., "5m", "1h", "30s"). Defaults to "5m".

        Returns:
            ProcessedVectorBuilder: Result of applying ``avg_over_time``.

        Examples:
            >>> cpu_usage.avg_over_time("1h")  # Average CPU usage over the last hour

        Note:
            MetricsQL Enhancement: Can be applied to any expression type, not just range vectors.

        Raises:
            InvalidExpressionError: If called without a base expression.
            RangeVectorError: If converting to range vector fails.
        """
        return create_simple_over_time_function(self, RangeVectorFunction.AVG_OVER_TIME, duration)

    def max_over_time(self, duration: str = "5m") -> 'ProcessedVectorBuilder':
        """
        Calculate the maximum value over the specified time range.

        Args:
            duration: The time range duration (e.g., "5m", "1h", "30s"). Defaults to "5m".

        Returns:
            ProcessedVectorBuilder: Result of applying ``max_over_time``.

        Examples:
            >>> cpu_usage.max_over_time("1h")  # Peak CPU usage in the last hour

        Note:
            MetricsQL Enhancement: Can be applied to any expression type.
        Raises:
            InvalidExpressionError: If called without a base expression.
            RangeVectorError: If converting to range vector fails.
        """
        return create_simple_over_time_function(self, RangeVectorFunction.MAX_OVER_TIME, duration)

    def min_over_time(self, duration: str = "5m") -> 'ProcessedVectorBuilder':
        """
        Calculate the minimum value over the specified time range.

        Args:
            duration: The time range duration (e.g., "5m", "1h", "30s"). Defaults to "5m".

        Returns:
            ProcessedVectorBuilder: Result of applying ``min_over_time``.

        Examples:
            >>> cpu_usage.min_over_time("1h")  # Minimum CPU usage in the last hour

        Note:
            MetricsQL Enhancement: Can be applied to any expression type.
        Raises:
            InvalidExpressionError: If called without a base expression.
            RangeVectorError: If converting to range vector fails.
        """
        return create_simple_over_time_function(self, RangeVectorFunction.MIN_OVER_TIME, duration)

    def sum_over_time(self, duration: str = "5m") -> 'ProcessedVectorBuilder':
        """
        Calculate the sum of all values over the specified time range.

        Args:
            duration: The time range duration (e.g., "5m", "1h", "30s"). Defaults to "5m".

        Returns:
            ProcessedVectorBuilder: Result of applying ``sum_over_time``.

        Examples:
            >>> request_count.sum_over_time("1h")  # Total requests in the last hour

        Note:
            MetricsQL Enhancement: Can be applied to any expression type.
        Raises:
            InvalidExpressionError: If called without a base expression.
            RangeVectorError: If converting to range vector fails.
        """
        return create_simple_over_time_function(self, RangeVectorFunction.SUM_OVER_TIME, duration)

    def count_over_time(
            self,
            duration: str = "5m") -> 'ProcessedVectorBuilder':
        """
        Count the number of samples over the specified time range.

        Args:
            duration: The time range duration (e.g., "5m", "1h", "30s"). Defaults to "5m".

        Returns:
            ProcessedVectorBuilder: Result of applying ``count_over_time``.

        Examples:
            >>> metric.count_over_time("1h")  # Number of data points in the last hour

        Note:
            MetricsQL Enhancement: Can be applied to any expression type.
        Raises:
            InvalidExpressionError: If called without a base expression.
            RangeVectorError: If converting to range vector fails.
        """
        return create_simple_over_time_function(self, RangeVectorFunction.COUNT_OVER_TIME, duration)

    def stddev_over_time(
            self,
            duration: str = "5m") -> 'ProcessedVectorBuilder':
        """
        Calculate the standard deviation over the specified time range.

        Args:
            duration: The time range duration (e.g., "5m", "1h", "30s"). Defaults to "5m".

        Returns:
            ProcessedVectorBuilder: Result of applying ``stddev_over_time``.

        Examples:
            >>> response_time.stddev_over_time("1h")  # Response time variability

        Note:
            MetricsQL Enhancement: Can be applied to any expression type.

            Performance Warning: Standard deviation calculations can be computationally
            intensive with large time ranges or many data points.
        Raises:
            InvalidExpressionError: If called without a base expression.
            RangeVectorError: If converting to range vector fails.
        """
        return create_simple_over_time_function(self, "stddev_over_time", duration)

    def stdvar_over_time(
            self,
            duration: str = "5m") -> 'ProcessedVectorBuilder':
        """
        Calculate the standard variance over the specified time range.

        Args:
            duration: The time range duration (e.g., "5m", "1h", "30s"). Defaults to "5m".

        Returns:
            ProcessedVectorBuilder: Result of applying ``stdvar_over_time``.

        Examples:
            >>> response_time.stdvar_over_time("1h")  # Response time variance

        Note:
            MetricsQL Enhancement: Can be applied to any expression type.

            Performance Warning: Variance calculations can be computationally intensive
            with large time ranges or many data points.
        Raises:
            InvalidExpressionError: If called without a base expression.
            RangeVectorError: If converting to range vector fails.
        """
        return create_simple_over_time_function(self, "stdvar_over_time", duration)

    def last_over_time(self, duration: str = "5m") -> 'ProcessedVectorBuilder':
        """
        Get the last (most recent) sample value over the specified time range.

        Args:
            duration: The time range duration (e.g., "5m", "1h", "30s"). Defaults to "5m".

        Returns:
            ProcessedVectorBuilder: Result of applying ``last_over_time``.

        Examples:
            >>> metric.last_over_time("5m")  # Most recent value in the last 5 minutes

        Note:
            MetricsQL Enhancement: Can be applied to any expression type.
        Raises:
            InvalidExpressionError: If called without a base expression.
            RangeVectorError: If converting to range vector fails.
        """
        return create_simple_over_time_function(self, "last_over_time", duration)

    def present_over_time(
            self,
            duration: str = "5m") -> 'ProcessedVectorBuilder':
        """
        Return 1 if any samples exist over the time range, 0 otherwise.

        Args:
            duration: The time range duration (e.g., "5m", "1h", "30s"). Defaults to "5m".

        Returns:
            ProcessedVectorBuilder: Result of applying ``present_over_time``.

        Examples:
            >>> metric.present_over_time("5m")  # 1 if data exists in last 5 minutes

        Note:
            MetricsQL Enhancement: Can be applied to any expression type.

            Use Case: Useful for detecting data gaps or service availability.
        Raises:
            InvalidExpressionError: If called without a base expression.
            RangeVectorError: If converting to range vector fails.
        """
        return create_simple_over_time_function(self, "present_over_time", duration)

    def deriv(self, duration: str = "5m") -> 'ProcessedVectorBuilder':
        """
        Calculate the per-second derivative (rate of change) over the time range.

        Args:
            duration: The time range duration (e.g., "5m", "1h", "30s"). Defaults to "5m".

        Returns:
            ProcessedVectorBuilder: Result of applying ``deriv``.

        Examples:
            >>> temperature.deriv("10m")  # Rate of temperature change per second

        Note:
            MetricsQL Enhancement: Can be applied to any expression type.

            Use Case: Best for gauge metrics to understand the rate of change.
        Raises:
            InvalidExpressionError: If called without a base expression.
            RangeVectorError: If converting to range vector fails.
        """
        return create_simple_over_time_function(self, "deriv", duration)

    def predict_linear(
            self: 'MetricsBuilder',
            prediction_seconds: float,
            duration: str = "5m") -> 'ProcessedVectorBuilder':
        """
        Predict future values using linear regression over the time range.

        Args:
            prediction_seconds: How many seconds into the future to predict
            duration: The time range for historical data (e.g., "5m", "1h") - default: "5m"

        Returns:
            A new ProcessedVectorBuilder with the predict_linear function applied.

        Examples:
            >>> cpu_usage.predict_linear(1800)  # Predict CPU in 30 minutes based on last 5m
            >>> disk_usage.predict_linear(3600, "1h")  # Predict disk usage in 1 hour based on 1h data

        Note:
            MetricsQL Enhancement: Can be applied to any expression type.

            Performance Warning: Linear prediction can be computationally intensive
            with large time ranges. Use reasonable time windows for better performance.

        Raises:
            InvalidExpressionError: If called without a base expression.
            RangeVectorError: If converting to range vector fails.
        """
        if self._ast_node is None:
            error = InvalidExpressionError("predict_linear")
            error.set_source_query("<no expression>")
            raise error

        range_builder = self.range(duration)
        if hasattr(range_builder, '_ast_node') and range_builder._ast_node:
            prediction_seconds_node = NumberLiteral(prediction_seconds)
            func_call = FunctionCall(
                "predict_linear", [
                    range_builder._ast_node, prediction_seconds_node])
            return self._create_new_builder(func_call)
        else:
            raise RangeVectorError(
                "predict_linear",
                duration,
                "Failed to create range vector")

    def quantile_over_time(
            self: 'MetricsBuilder',
            quantile: float,
            duration: str = "5m") -> 'ProcessedVectorBuilder':
        """
        Calculate the specified quantile over the time range.

        Args:
            quantile: The quantile to calculate (0.0-1.0).
            duration: The time range duration (e.g., "5m", "1h", "30s"). Defaults to "5m".

        Returns:
            A new ProcessedVectorBuilder with the quantile_over_time function applied.

        Examples:
            >>> response_time.quantile_over_time(0.95, "1h")  # 95th percentile response time
            >>> cpu_usage.quantile_over_time(0.5, "30m")     # Median CPU usage

        Note:
            MetricsQL Enhancement: Can be applied to any expression type.

            Performance Warning: Quantile calculations can be computationally intensive
            with large time ranges or many data points, especially for high quantiles.

        Raises:
            InvalidExpressionError: If called without a base expression.
            InvalidParameterError: If quantile is outside [0.0, 1.0].
            RangeVectorError: If converting to range vector fails.
        """
        if self._ast_node is None:
            error = InvalidExpressionError("quantile_over_time")
            error.set_source_query("<no expression>")
            raise error

        validate_numeric_range("quantile", quantile, 0.0, 1.0, "holt_winters")

        range_builder = self.range(duration)
        if hasattr(range_builder, '_ast_node') and range_builder._ast_node:
            quantile_node = NumberLiteral(quantile)
            func_call = FunctionCall(
                "quantile_over_time", [
                    quantile_node, range_builder._ast_node])
            return self._create_new_builder(func_call)
        else:
            raise RangeVectorError(
                "quantile_over_time",
                duration,
                "Failed to create range vector")

    def mad_over_time(self, duration: str = "5m") -> 'ProcessedVectorBuilder':
        """
        Calculate the median absolute deviation over the specified time range.

        MAD is a robust measure of variability that is less sensitive to outliers
        than standard deviation.

        Args:
            duration: The time range duration (e.g., "5m", "1h", "30s"). Defaults to "5m".

        Returns:
            ProcessedVectorBuilder: Result of applying ``mad_over_time``.

        Examples:
            >>> cpu_usage.mad_over_time("1h")  # MAD of CPU usage over 1 hour
            >>> latency.mad_over_time("30m")  # Robust variability measure for latency

        Note:
            MetricsQL Extension: This function is specific to MetricsQL and not available in PromQL.

            Performance: More computationally intensive than stddev but more robust to outliers.
            Use Case: Better for detecting anomalies when data contains outliers.
        Raises:
            InvalidExpressionError: If called without a base expression.
            RangeVectorError: If converting to range vector fails.
        """
        return create_range_vector_function(self, RangeVectorFunction.MAD_OVER_TIME, duration)

    def median_over_time(
            self,
            duration: str = "5m") -> 'ProcessedVectorBuilder':
        """
        Calculate the median value over the specified time range.

        Args:
            duration: The time range duration (e.g., "5m", "1h", "30s"). Defaults to "5m".

        Returns:
            ProcessedVectorBuilder: Result of applying ``median_over_time``.

        Examples:
            >>> response_time.median_over_time("1h")  # Median response time
            >>> cpu_usage.median_over_time("30m")  # Median CPU usage

        Note:
            MetricsQL Extension: This function is specific to MetricsQL and not available in PromQL.

            Performance: More computationally intensive than avg_over_time.
            Use Case: Better central tendency measure when data has outliers.
        Raises:
            InvalidExpressionError: If called without a base expression.
            RangeVectorError: If converting to range vector fails.
        """
        return create_range_vector_function(self, RangeVectorFunction.MEDIAN_OVER_TIME, duration)

    def mode_over_time(self, duration: str = "5m") -> 'ProcessedVectorBuilder':
        """
        Calculate the mode (most frequent value) over the specified time range.

        Args:
            duration: The time range duration (e.g., "5m", "1h", "30s"). Defaults to "5m".

        Returns:
            ProcessedVectorBuilder: Result of applying ``mode_over_time``.

        Examples:
            >>> status_code.mode_over_time("1h")  # Most common status code
            >>> error_level.mode_over_time("30m")  # Most frequent error level

        Note:
            MetricsQL Extension: This function is specific to MetricsQL and not available in PromQL.

            Performance Warning: Can be computationally intensive with many unique values.
            Use Case: Finding the most common categorical values.
        Raises:
            InvalidExpressionError: If called without a base expression.
            RangeVectorError: If converting to range vector fails.
        """
        return create_range_vector_function(self, RangeVectorFunction.MODE_OVER_TIME, duration)

    def rate_over_sum(self, duration: str = "5m") -> 'ProcessedVectorBuilder':
        """
        Calculate rate() over sum_over_time() - useful for calculating average rates.

        This MetricsQL-specific function is equivalent to rate()/sum_over_time() but
        more efficient as a single operation.

        Args:
            duration: The time range duration (e.g., "5m", "1h", "30s"). Defaults to "5m".

        Returns:
            ProcessedVectorBuilder: Result of applying ``rate_over_sum``.

        Examples:
            >>> requests_total.rate_over_sum("5m")  # Efficient average request rate

        Note:
            MetricsQL Extension: This function is specific to MetricsQL and not available in PromQL.

            Performance: More efficient than separate rate() and sum_over_time() operations.
        Raises:
            InvalidExpressionError: If called without a base expression.
            RangeVectorError: If converting to range vector fails.
        """
        return create_range_vector_function(self, RangeVectorFunction.RATE_OVER_SUM, duration)

    def zscore_over_time(
            self,
            duration: str = "5m") -> 'ProcessedVectorBuilder':
        """
        Calculate z-score over the specified time range.

        Z-score indicates how many standard deviations a value is from the mean,
        useful for outlier detection and normalization.

        Args:
            duration: The time range duration (e.g., "5m", "1h", "30s"). Defaults to "5m".

        Returns:
            ProcessedVectorBuilder: Result of applying ``zscore_over_time``.

        Examples:
            >>> cpu_usage.zscore_over_time("1h")  # Z-score for anomaly detection
            >>> latency.zscore_over_time("30m")  # Standardized latency values

        Note:
            MetricsQL Extension: This function is specific to MetricsQL and not available in PromQL.

            Use Case: Anomaly detection, data normalization, and statistical analysis.
        Raises:
            InvalidExpressionError: If called without a base expression.
            RangeVectorError: If converting to range vector fails.
        """
        return create_range_vector_function(self, RangeVectorFunction.ZSCORE_OVER_TIME, duration)

    def rollup(
            self,
            func: str,
            duration: str = "5m") -> 'ProcessedVectorBuilder':
        """
        Apply a custom rollup function over the specified time range.

        This MetricsQL-specific function allows applying arbitrary rollup functions
        that may not have dedicated function names.

        Args:
            func: The rollup function name (e.g., "avg", "max", "sum", etc.).
            duration: The time range duration (e.g., "5m", "1h", "30s"). Defaults to "5m".

        Returns:
            ProcessedVectorBuilder: Result of applying ``rollup(func, duration)``.

        Examples:
            >>> cpu_usage.rollup("avg", "1h")  # Custom average rollup
            >>> memory.rollup("p95", "30m")  # 95th percentile rollup

        Note:
            MetricsQL Extension: This function is specific to MetricsQL and not available in PromQL.

            Use Case: When you need rollup functions not covered by standard *_over_time functions.
        Raises:
            InvalidExpressionError: If called without a base expression.
            RangeVectorError: If converting to range vector fails.
        """
        return create_range_vector_function(self, RangeVectorFunction.ROLLUP, duration, [func])

    def rollup_rate(self, duration: str = "5m") -> 'ProcessedVectorBuilder':
        """
        Calculate rollup rate over the specified time range.

        This MetricsQL-specific function provides more advanced rate calculations
        with better handling of counter resets and gaps.

        Args:
            duration: The time range duration (e.g., "5m", "1h", "30s"). Defaults to "5m".

        Returns:
            ProcessedVectorBuilder: Result of applying ``rollup_rate``.

        Examples:
            >>> requests_total.rollup_rate("5m")  # Advanced rate calculation

        Note:
            MetricsQL Extension: This function is specific to MetricsQL and not available in PromQL.

            Performance: Better handling of edge cases compared to standard rate().
        Raises:
            InvalidExpressionError: If called without a base expression.
            RangeVectorError: If converting to range vector fails.
        """
        return create_range_vector_function(self, RangeVectorFunction.ROLLUP_RATE, duration)
