"""Aggregation functions mixin for QueryBuilder."""

from typing import List, Union, Optional, TYPE_CHECKING

from metricraft._legacy.builder.utils import create_aggregation_function
from metricraft._legacy.enums import SignState
from metricraft._legacy.tree import FunctionCall, NumberLiteral
from metricraft._legacy.enums import AggregationOperator
from metricraft._legacy.exceptions import VMInvalidExpressionError as InvalidExpressionError
from metricraft._legacy.contracts import AggregationMixinBase

if TYPE_CHECKING:
    from metricraft._legacy.builder.impl.base import MetricsBuilder
    from metricraft._legacy.builder.impl.processed_vector import ProcessedVectorBuilder

class AggregationMixin(AggregationMixinBase):
    """
    Mixin providing aggregation functions for QueryBuilder.

    This mixin handles aggregation operations like sum(), avg(), max(), min(),
    count(), topk(), bottomk(), quantile(), etc.
    """

    def sum(self,
            by: Optional[List[str]] = None,
            without: Optional[List[str]] = None) -> 'ProcessedVectorBuilder':
        """
        Calculate the sum across time series.

        Args:
            by: List of label names to group by (preserve these labels).
            without: List of label names to exclude from grouping (remove these labels).

        Returns:
            A new ProcessedVectorBuilder with the sum aggregation applied.

        Examples:
            >>> cpu_usage.sum()  # Sum across all series
            >>> cpu_usage.sum(by=["instance"])  # Sum by instance
            >>> cpu_usage.sum(without=["job"])  # Sum excluding job label

        Note:
            MetricsQL Enhancement: Can be applied to instant vectors, processed vectors,
            and even range vectors (unlike standard PromQL).

            Performance: Generally efficient aggregation operation.
        """
        return create_aggregation_function(self, AggregationOperator.SUM, by=by, without=without)

    def avg(self,
            by: Optional[List[str]] = None,
            without: Optional[List[str]] = None) -> 'ProcessedVectorBuilder':
        """
        Calculate the average across time series.

        Args:
            by: List of label names to group by (preserve these labels).
            without: List of label names to exclude from grouping (remove these labels).

        Returns:
            A new ProcessedVectorBuilder with the avg aggregation applied.

        Examples:
            >>> cpu_usage.avg()  # Average across all series
            >>> cpu_usage.avg(by=["region"])  # Average by region
            >>> response_time.avg(without=["instance"])  # Average excluding instance

        Note:
            MetricsQL Enhancement: Can be applied to any expression type.
        """
        return create_aggregation_function(self, AggregationOperator.AVG, by=by, without=without)

    def min(self,
            by: Optional[List[str]] = None,
            without: Optional[List[str]] = None) -> 'ProcessedVectorBuilder':
        """
        Calculate the minimum value across time series.

        Args:
            by: List of label names to group by (preserve these labels).
            without: List of label names to exclude from grouping (remove these labels).

        Returns:
            A new ProcessedVectorBuilder with the min aggregation applied.

        Examples:
            >>> cpu_usage.min()  # Minimum across all series
            >>> cpu_usage.min(by=["datacenter"])  # Minimum by datacenter
            >>> memory_usage.min(without=["instance"])  # Min excluding instance

        Note:
            MetricsQL Enhancement: Can be applied to any expression type.
        """
        return create_aggregation_function(self, AggregationOperator.MIN, by=by, without=without)

    def max(self,
            by: Optional[List[str]] = None,
            without: Optional[List[str]] = None) -> 'ProcessedVectorBuilder':
        """
        Calculate the maximum value across time series.

        Args:
            by: List of label names to group by (preserve these labels).
            without: List of label names to exclude from grouping (remove these labels).

        Returns:
            A new ProcessedVectorBuilder with the max aggregation applied.

        Examples:
            >>> cpu_usage.max()  # Maximum across all series
            >>> cpu_usage.max(by=["service"])  # Maximum by service
            >>> disk_usage.max(without=["device"])  # Max excluding device

        Note:
            MetricsQL Enhancement: Can be applied to any expression type.
        """
        return create_aggregation_function(self, AggregationOperator.MAX, by=by, without=without)

    def count(self,
              by: Optional[List[str]] = None,
              without: Optional[List[str]] = None) -> 'ProcessedVectorBuilder':
        """
        Count the number of time series.

        Args:
            by: List of label names to group by (preserve these labels).
            without: List of label names to exclude from grouping (remove these labels).

        Returns:
            A new ProcessedVectorBuilder with the count aggregation applied.

        Examples:
            >>> cpu_usage.count()  # Total number of series
            >>> cpu_usage.count(by=["job"])  # Count by job
            >>> alerts.count(without=["instance"])  # Count excluding instance

        Note:
            MetricsQL Enhancement: Can be applied to any expression type.

            Use Case: Useful for counting active instances, services, or alert conditions.
        """
        return create_aggregation_function(self, AggregationOperator.COUNT, by=by, without=without)

    def stddev(self,
               by: Optional[List[str]] = None,
               without: Optional[List[str]] = None) -> 'ProcessedVectorBuilder':
        """
        Calculate the standard deviation across time series.

        Args:
            by: List of label names to group by (preserve these labels).
            without: List of label names to exclude from grouping (remove these labels).

        Returns:
            A new ProcessedVectorBuilder with the stddev aggregation applied.

        Examples:
            >>> response_time.stddev()  # Standard deviation across all series
            >>> cpu_usage.stddev(by=["datacenter"])  # Std dev by datacenter
            >>> memory_usage.stddev(without=["instance"])  # Std dev excluding instance

        Note:
            MetricsQL Enhancement: Can be applied to any expression type.

            Performance Warning: Standard deviation calculations can be computationally
            intensive with many time series. Consider using smaller groups or sampling.
        """
        return create_aggregation_function(self, AggregationOperator.STDDEV, by=by, without=without)

    def stdvar(self,
               by: Optional[List[str]] = None,
               without: Optional[List[str]] = None) -> 'ProcessedVectorBuilder':
        """
        Calculate the standard variance across time series.

        Args:
            by: List of label names to group by (preserve these labels).
            without: List of label names to exclude from grouping (remove these labels).

        Returns:
            A new ProcessedVectorBuilder with the stdvar aggregation applied.

        Examples:
            >>> response_time.stdvar()  # Variance across all series
            >>> cpu_usage.stdvar(by=["region"])  # Variance by region
            >>> memory_usage.stdvar(without=["instance"])  # Variance excluding instance

        Note:
            MetricsQL Enhancement: Can be applied to any expression type.

            Performance Warning: Variance calculations can be computationally intensive
            with many time series. Consider using smaller groups or sampling.
        """
        return create_aggregation_function(self, AggregationOperator.STDVAR, by=by, without=without)

    def topk(self,
             k: Union[int,
             'MetricsBuilder'],
             by: Optional[List[str]] = None,
             without: Optional[List[str]] = None) -> 'ProcessedVectorBuilder':
        """
        Get the top k time series with the largest values.

        Args:
            k: Number of top elements to return, or a MetricsBuilder expression.
            by: List of label names to group by (preserve these labels).
            without: List of label names to exclude from grouping (remove these labels).

        Returns:
            A new ProcessedVectorBuilder with the topk aggregation applied.

        Examples:
            >>> cpu_usage.topk(5)  # Top 5 series with highest CPU usage
            >>> memory_usage.topk(3, by=["service"])  # Top 3 by service
            >>> disk_usage.topk(10, without=["device"])  # Top 10 excluding device

        Note:
            MetricsQL Enhancement: Can be applied to any expression type.

            Performance: Relatively efficient, but performance depends on the total
            number of time series and the value of k.
        """
        return create_aggregation_function(self, AggregationOperator.TOPK, param=k, by=by, without=without)

    def bottomk(self,
                k: Union[int,
                'MetricsBuilder'],
                by: Optional[List[str]] = None,
                without: Optional[List[str]] = None) -> 'ProcessedVectorBuilder':
        """
        Get the bottom k time series with the smallest values.

        Args:
            k: Number of bottom elements to return, or a MetricsBuilder expression.
            by: List of label names to group by (preserve these labels).
            without: List of label names to exclude from grouping (remove these labels).

        Returns:
            A new ProcessedVectorBuilder with the bottomk aggregation applied.

        Examples:
            >>> cpu_usage.bottomk(5)  # Bottom 5 series with lowest CPU usage
            >>> memory_usage.bottomk(3, by=["service"])  # Bottom 3 by service
            >>> response_time.bottomk(10, without=["instance"])  # Bottom 10 excluding instance

        Note:
            MetricsQL Enhancement: Can be applied to any expression type.

            Performance: Similar to topk, relatively efficient operation.
        """
        return create_aggregation_function(self, AggregationOperator.BOTTOMK, param=k, by=by, without=without)

    def quantile(self,
                 q: Union[float,
                 'MetricsBuilder'],
                 by: Optional[List[str]] = None,
                 without: Optional[List[str]] = None) -> 'ProcessedVectorBuilder':
        """
        Calculate the specified quantile across time series.

        Args:
            q: Quantile value (0.0-1.0) or a MetricsBuilder expression.
            by: List of label names to group by (preserve these labels).
            without: List of label names to exclude from grouping (remove these labels).

        Returns:
            A new ProcessedVectorBuilder with the quantile aggregation applied.

        Examples:
            >>> response_time.quantile(0.95)  # 95th percentile across all series
            >>> cpu_usage.quantile(0.5, by=["datacenter"])  # Median by datacenter
            >>> memory_usage.quantile(0.99, without=["instance"])  # 99th percentile excluding instance

        Note:
            MetricsQL Enhancement: Can be applied to any expression type.

            Performance Warning: Quantile calculations can be computationally intensive,
            especially for high quantiles (>0.9) and many time series. Consider using
            histogram_quantile for histogram metrics when possible.
        """
        return create_aggregation_function(self, AggregationOperator.QUANTILE, param=q, by=by, without=without)

    def histogram_quantile(
            self: 'MetricsBuilder', q: Union[float, 'MetricsBuilder']) -> 'ProcessedVectorBuilder':
        """
        Calculate the quantile from histogram buckets.

        This function calculates quantiles from histogram data where the input
        should be histogram buckets (typically ending with _bucket).

        Args:
            q: Quantile value (0.0-1.0) or a MetricsBuilder expression.

        Returns:
            A new ProcessedVectorBuilder with the histogram_quantile function applied.

        Examples:
            >>> # Calculate 95th percentile from histogram buckets
            >>> request_duration_buckets.histogram_quantile(0.95)

            >>> # Calculate median from histogram, typically used with rate and sum by le
            >>> rate_buckets = (QueryBuilder.from_metric("http_request_duration_bucket")
            ...                .rate("5m")
            ...                .sum(by=["le"]))
            >>> rate_buckets.histogram_quantile(0.5)

        Note:
            MetricsQL Enhancement: Can be applied to any expression type, but typically
            used with histogram bucket metrics.

            Performance: Generally efficient as it operates on pre-aggregated histogram data.
            Much faster than quantile() for large datasets.

            Use Case: This is the preferred method for calculating quantiles from
            Prometheus histogram metrics (those with _bucket suffix).
        """
        if self._ast_node is None:
            raise InvalidExpressionError("histogram_quantile")

        # Handle q parameter
        if isinstance(q, type(self)):
            if q._ast_node is None:
                raise ValueError("q parameter builder has no expression")
            q_node = q._ast_node
        else:
            if not (0.0 <= q <= 1.0):
                raise ValueError("quantile must be between 0.0 and 1.0")
            q_node = NumberLiteral(q)

        # histogram_quantile takes quantile as first parameter, histogram as
        # second
        func_call = FunctionCall("histogram_quantile", [q_node, self.ast_node])
        return self._create_new_builder(func_call, SignState.NONE)

    def count_values(self,
                     label_name: str,
                     by: Optional[List[str]] = None,
                     without: Optional[List[str]] = None) -> 'ProcessedVectorBuilder':
        """
        Count the number of time series with the same value, creating new series with the value as a label.

        Args:
            label_name: Name of the label to store the value.
            by: List of labels to group by.
            without: List of labels to exclude from grouping.

        Returns:
            A new ProcessedVectorBuilder with the count_values aggregation applied.

        Examples:
            >>> http_status.count_values("status")  # Count occurrences of each status code
            >>> errors.count_values("error_type", by=["service"])  # Count by service

        Note:
            PromQL Standard: Available in both PromQL and MetricsQL.

            Use Case: Counting occurrences of categorical values across time series.
        """
        return create_aggregation_function(self, AggregationOperator.COUNT_VALUES, param=label_name, by=by,
                                           without=without)

    def group(self,
              by: Optional[List[str]] = None,
              without: Optional[List[str]] = None) -> 'ProcessedVectorBuilder':
        """
        Group time series, returning 1 for any group with at least one element.

        Args:
            by: List of labels to group by.
            without: List of labels to exclude from grouping.

        Returns:
            A new ProcessedVectorBuilder with the group aggregation applied.

        Examples:
            >>> metrics.group(by=["instance"])  # Group by instance, return 1 for each
            >>> alerts.group(without=["alertname"])  # Check if any alerts exist per group

        Note:
            PromQL Standard: Available in both PromQL and MetricsQL.

            Use Case: Checking for the existence of time series in groups.
        """
        return create_aggregation_function(self, AggregationOperator.GROUP, by=by, without=without)

    def any(self,
            by: Optional[List[str]] = None,
            without: Optional[List[str]] = None) -> 'ProcessedVectorBuilder':
        """
        Return 1 if any values in the group are non-zero, 0 otherwise.

        Args:
            by: List of labels to group by.
            without: List of labels to exclude from grouping.

        Returns:
            A new ProcessedVectorBuilder with the any aggregation applied.

        Examples:
            >>> error_flags.any(by=["service"])  # Check if any errors per service
            >>> alerts.any()  # Check if any alerts are active

        Note:
            MetricsQL Extension: This function is specific to MetricsQL and not available in PromQL.

            Use Case: Boolean aggregation for alert conditions.
        """
        return create_aggregation_function(self, AggregationOperator.ANY, by=by, without=without)

    def median(self,
               by: Optional[List[str]] = None,
               without: Optional[List[str]] = None) -> 'ProcessedVectorBuilder':
        """
        Calculate the median value across time series.

        Args:
            by: List of labels to group by.
            without: List of labels to exclude from grouping.

        Returns:
            A new ProcessedVectorBuilder with the median aggregation applied.

        Examples:
            >>> response_times.median(by=["service"])  # Median response time per service
            >>> cpu_usage.median()  # Overall median CPU usage

        Note:
            MetricsQL Extension: This function is specific to MetricsQL and not available in PromQL.

            Performance: More computationally intensive than avg().
            Use Case: Better central tendency measure when data has outliers.
        """
        return create_aggregation_function(self, AggregationOperator.MEDIAN, by=by, without=without)

    def mode(self,
             by: Optional[List[str]] = None,
             without: Optional[List[str]] = None) -> 'ProcessedVectorBuilder':
        """
        Calculate the mode (most frequent value) across time series.

        Args:
            by: List of labels to group by.
            without: List of labels to exclude from grouping.

        Returns:
            A new ProcessedVectorBuilder with the mode aggregation applied.

        Examples:
            >>> status_codes.mode(by=["service"])  # Most common status per service
            >>> error_levels.mode()  # Most frequent error level

        Note:
            MetricsQL Extension: This function is specific to MetricsQL and not available in PromQL.

            Performance Warning: Can be computationally intensive with many unique values.
            Use Case: Finding the most common categorical values.
        """
        return create_aggregation_function(self, AggregationOperator.MODE, by=by, without=without)

    def mad(self,
            by: Optional[List[str]] = None,
            without: Optional[List[str]] = None) -> 'ProcessedVectorBuilder':
        """
        Calculate the median absolute deviation across time series.

        MAD is a robust measure of variability that is less sensitive to outliers
        than standard deviation.

        Args:
            by: List of labels to group by.
            without: List of labels to exclude from grouping.

        Returns:
            A new ProcessedVectorBuilder with the mad aggregation applied.

        Examples:
            >>> response_times.mad(by=["service"])  # MAD of response times per service
            >>> cpu_usage.mad()  # Overall CPU usage variability

        Note:
            MetricsQL Extension: This function is specific to MetricsQL and not available in PromQL.

            Performance: More computationally intensive than stddev but more robust to outliers.
            Use Case: Better variability measure when data contains outliers.
        """
        return create_aggregation_function(self, AggregationOperator.MAD, by=by, without=without)
