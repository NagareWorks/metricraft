"""Factory methods for creating QueryBuilder instances."""

from typing import Union, TYPE_CHECKING

from metricraft._legacy.enums import SignState, TransformationFunction, DateTimeFunction, MetricsQLFunction
from metricraft._legacy.tree import (
    MetricSelector,
    NumberLiteral,
    StringLiteral,
    FunctionCall
)
from metricraft._legacy.builder.impl.types import BuilderType
from metricraft._legacy.builder.impl.register import BuilderRegister as Register

if TYPE_CHECKING:
    from metricraft._legacy.builder.impl.instant_vector import InstantVectorBuilder
    from metricraft._legacy.builder.impl.scalar import ScalarBuilder
    from metricraft._legacy.builder.impl.processed_vector import ProcessedVectorBuilder


from metricraft._legacy.contracts import FactoryMixinBase


class FactoryMixin(FactoryMixinBase):
    """
    Mixin providing static factory methods for creating QueryBuilder instances.
    """

    @staticmethod
    def from_metric(name: str) -> 'InstantVectorBuilder':
        """
        Create a new query builder instance based on a metric name.

        This is the most common way to start building a MetricsQL query,
        beginning with a specific metric.

        Args:
            name: The metric name to query.

        Returns:
            An InstantVectorBuilder configured with the specified metric.

        Examples:
            >>> cpu_usage = QueryBuilder.from_metric("cpu_usage")
            >>> memory_total = QueryBuilder.from_metric("memory_total")
        """
        metric_selector = MetricSelector(name)
        return Register.get_builder(
            BuilderType.INSTANT_VECTOR,
            ast_node=metric_selector,
            sign_state=SignState.NONE,
        )

    @staticmethod
    def from_string(value: str) -> 'ScalarBuilder':
        """
        Create a scalar query builder from a string value.

        String literals in MetricsQL are primarily used for label matching
        and as parameters to functions that expect string arguments.

        Args:
            value: The string value.

        Returns:
            A ScalarBuilder with the string literal.
        """
        string_literal = StringLiteral(value)
        return Register.get_builder(
            BuilderType.SCALAR,
            ast_node=string_literal,
            sign_state=SignState.NONE,
        )

    @staticmethod
    def from_scalar(value: Union[int, float]) -> 'ScalarBuilder':
        """
        Create a scalar query builder from a numeric value.

        Scalar values can be used in arithmetic operations, comparisons,
        and as parameters to functions.

        Args:
            value: The numeric value (int or float).

        Returns:
            A ScalarBuilder with the numeric literal.

        Examples:
            >>> ten = QueryBuilder.from_scalar(10)
            >>> pi = QueryBuilder.from_scalar(3.14159)
        """
        numeric_literal = NumberLiteral(float(value))
        return Register.get_builder(
            BuilderType.SCALAR,
            ast_node=numeric_literal,
            sign_state=SignState.NONE,
        )

    @staticmethod
    def from_expr(expr: str) -> 'ProcessedVectorBuilder':
        """
        Create a query builder from a raw MetricsQL expression string.

        This is useful for incorporating existing query fragments or
        complex expressions that are easier to write directly.

        Args:
            expr: A valid MetricsQL expression string.

        Returns:
            A ProcessedVectorBuilder with the raw expression.

        Examples:
            >>> custom = QueryBuilder.from_expr("sum(rate(http_requests[5m]))")
            >>> complex_expr = QueryBuilder.from_expr("histogram_quantile(0.95, rate(response_time[5m]))")

        Warning:
            The expression string is not validated until query execution.
            Prefer using the fluent API methods when possible.
        """
        ast_node = StringLiteral(expr)
        return Register.get_builder(
            BuilderType.PROCESSED_VECTOR,
            ast_node=ast_node,
            sign_state=SignState.NONE,
        )

    @staticmethod
    def from_time() -> 'ScalarBuilder':
        """
        Create a scalar representing the current evaluation time.

        Returns the current evaluation timestamp as a Unix timestamp in seconds.
        Equivalent to the time() function in MetricsQL/PromQL.

        Returns:
            A ScalarBuilder representing the current time.

        Examples:
            >>> current_time = QueryBuilder.from_time()
            >>> time_diff = current_time - QueryBuilder.from_scalar(3600)  # 1 hour ago
        """
        time_call = FunctionCall(DateTimeFunction.TIME, [])
        return Register.get_builder(
            BuilderType.SCALAR,
            ast_node=time_call,
            sign_state=SignState.NONE,
        )

    @staticmethod
    def from_now() -> 'ScalarBuilder':
        """
        Create a scalar representing the current wall clock time.

        Returns the current wall clock time as a Unix timestamp in seconds.
        This is a MetricsQL-specific function that differs from time() during
        range queries where time() varies but now() remains constant.

        Returns:
            A ScalarBuilder representing the current wall clock time.

        Examples:
            >>> wall_time = QueryBuilder.from_now()

        Note:
            This is a MetricsQL-specific function not available in standard PromQL.
        """
        now_call = FunctionCall(DateTimeFunction.NOW, [])
        return Register.get_builder(
            BuilderType.SCALAR,
            ast_node=now_call,
            sign_state=SignState.NONE,
        )

    @staticmethod
    def from_start() -> 'ScalarBuilder':
        """
        Create a scalar representing the start time of the query range.

        Returns the start timestamp of the current query evaluation range.
        This is a MetricsQL-specific function.

        Returns:
            A ScalarBuilder representing the query start time.

        Examples:
            >>> range_start = QueryBuilder.from_start()
            >>> duration = QueryBuilder.from_end() - range_start

        Note:
            This is a MetricsQL-specific function not available in standard PromQL.
        """
        start_call = FunctionCall(MetricsQLFunction.START, [])
        return Register.get_builder(
            BuilderType.SCALAR,
            ast_node=start_call,
            sign_state=SignState.NONE,
        )

    @staticmethod
    def from_end() -> 'ScalarBuilder':
        """
        Create a scalar representing the end time of the query range.

        Returns the end timestamp of the current query evaluation range.
        This is a MetricsQL-specific function.

        Returns:
            A ScalarBuilder representing the query end time.

        Examples:
            >>> range_end = QueryBuilder.from_end()
            >>> total_duration = range_end - QueryBuilder.from_start()

        Note:
            This is a MetricsQL-specific function not available in standard PromQL.
        """
        end_call = FunctionCall(MetricsQLFunction.END, [])
        return Register.get_builder(
            BuilderType.SCALAR,
            ast_node=end_call,
            sign_state=SignState.NONE,
        )
