"""Metrics family (PromQL/MetricsQL) mixin skeletons for Core.

Providers like VM/Prometheus should inherit these mixins and implement
concrete behaviors. The method signatures and return types mirror the
provider implementations but point to Core "Base" builder types to avoid
reverse dependencies.

Notes
- All methods here raise ``NotImplementedError`` by design.
- Return type hints are precise and reference the base builder classes
    (e.g., ``RangeVectorBuilderBase``), which improves IDE hints without
    leaking provider classes.
"""

from __future__ import annotations

from typing import Any, List, Optional, Union, TYPE_CHECKING

# Type-only imports to satisfy static analysis while avoiding runtime cycles
if TYPE_CHECKING:
    from typing_extensions import Self
    from metricraft._legacy.families.metrics.states import (
        InstantVectorBuilderBase,
        RangeVectorBuilderBase,
        ProcessedVectorBuilderBase,
        ScalarBuilderBase,
    )


class FactoryMixinBase:
    @staticmethod
    def from_metric(name: str) -> 'InstantVectorBuilderBase':
        """Create an instant-vector builder from a metric name."""
        raise NotImplementedError

    @staticmethod
    def from_string(value: str) -> 'ScalarBuilderBase':
        """Create a scalar builder from a string literal."""
        raise NotImplementedError

    @staticmethod
    def from_scalar(value: Union[int, float]) -> 'ScalarBuilderBase':
        """Create a scalar builder from a numeric literal."""
        raise NotImplementedError

    @staticmethod
    def from_expr(expr: str) -> 'ProcessedVectorBuilderBase':
        """Create a processed-vector builder from a raw expression string."""
        raise NotImplementedError

    @staticmethod
    def from_time() -> 'ScalarBuilderBase':
        """Create a scalar builder representing the current eval time (``time()``)."""
        raise NotImplementedError

    @staticmethod
    def from_now() -> 'ScalarBuilderBase':
        """Create a scalar builder representing current wall-clock time (``now()``)."""
        raise NotImplementedError

    @staticmethod
    def from_start() -> 'ScalarBuilderBase':
        """Create a scalar builder for the start of the query range (``start()``)."""
        raise NotImplementedError

    @staticmethod
    def from_end() -> 'ScalarBuilderBase':
        """Create a scalar builder for the end of the query range (``end()``)."""
        raise NotImplementedError


class SignMixinBase:
    def positive(self) -> Self:
        """Apply a unary plus to the expression and return same-type builder."""
        raise NotImplementedError

    def negative(self) -> Self:
        """Apply a unary minus to the expression and return same-type builder."""
        raise NotImplementedError

    # Operator overloads for hinting/convenience
    def __pos__(self) -> Self:  # type: ignore[override]
        return self.positive()

    def __neg__(self) -> Self:  # type: ignore[override]
        return self.negative()


class ArithmeticMixinBase:
    def add(self, other: Any) -> 'ProcessedVectorBuilderBase':
        """Return a processed vector for binary ``+`` operation."""
        raise NotImplementedError
    def sub(self, other: Any) -> 'ProcessedVectorBuilderBase':
        """Return a processed vector for binary ``-`` operation."""
        raise NotImplementedError
    def mul(self, other: Any) -> 'ProcessedVectorBuilderBase':
        """Return a processed vector for binary ``*`` operation."""
        raise NotImplementedError
    def div(self, other: Any) -> 'ProcessedVectorBuilderBase':
        """Return a processed vector for binary ``/`` operation."""
        raise NotImplementedError
    def mod(self, other: Any) -> 'ProcessedVectorBuilderBase':
        """Return a processed vector for binary modulus operation."""
        raise NotImplementedError
    def pow(self, other: Any) -> 'ProcessedVectorBuilderBase':
        """Return a processed vector for exponentiation operation."""
        raise NotImplementedError

    # Operator overloads mapping to named methods
    def __add__(self, other: Any) -> ProcessedVectorBuilderBase:  # type: ignore[override]
        return self.add(other)  # type: ignore[return-value]
    def __sub__(self, other: Any) -> ProcessedVectorBuilderBase:  # type: ignore[override]
        return self.sub(other)  # type: ignore[return-value]
    def __mul__(self, other: Any) -> ProcessedVectorBuilderBase:  # type: ignore[override]
        return self.mul(other)  # type: ignore[return-value]
    def __truediv__(self, other: Any) -> ProcessedVectorBuilderBase:  # type: ignore[override]
        return self.div(other)  # type: ignore[return-value]
    def __mod__(self, other: Any) -> ProcessedVectorBuilderBase:  # type: ignore[override]
        return self.mod(other)  # type: ignore[return-value]
    def __pow__(self, other: Any) -> ProcessedVectorBuilderBase:  # type: ignore[override]
        return self.pow(other)  # type: ignore[return-value]

    # Reflected operators are provider-specific; keep signatures for typing
    def __radd__(self, other: Any) -> 'ProcessedVectorBuilderBase':  # type: ignore[override]
        raise NotImplementedError
    def __rsub__(self, other: Any) -> 'ProcessedVectorBuilderBase':  # type: ignore[override]
        raise NotImplementedError
    def __rmul__(self, other: Any) -> 'ProcessedVectorBuilderBase':  # type: ignore[override]
        raise NotImplementedError
    def __rtruediv__(self, other: Any) -> 'ProcessedVectorBuilderBase':  # type: ignore[override]
        raise NotImplementedError


class ComparisonMixinBase:
    def gt(self, other: Any) -> 'ProcessedVectorBuilderBase':
        """Return processed vector for ``>`` comparison."""
        raise NotImplementedError
    def lt(self, other: Any) -> 'ProcessedVectorBuilderBase':
        """Return processed vector for ``<`` comparison."""
        raise NotImplementedError
    def ge(self, other: Any) -> 'ProcessedVectorBuilderBase':
        """Return processed vector for ``>=`` comparison."""
        raise NotImplementedError
    def le(self, other: Any) -> 'ProcessedVectorBuilderBase':
        """Return processed vector for ``<=`` comparison."""
        raise NotImplementedError
    def eq(self, other: Any) -> 'ProcessedVectorBuilderBase':
        """Return processed vector for equality comparison."""
        raise NotImplementedError
    def ne(self, other: Any) -> 'ProcessedVectorBuilderBase':
        """Return processed vector for inequality comparison."""
        raise NotImplementedError
    def between(self, min_value: Union[int, float], max_value: Union[int, float]) -> 'ProcessedVectorBuilderBase':
        """Return processed vector for inclusive range comparison."""
        raise NotImplementedError

    # Operator overloads mapping to named comparison methods
    def __gt__(self, other: Any) -> ProcessedVectorBuilderBase:  # type: ignore[override]
        return self.gt(other)  # type: ignore[return-value]
    def __lt__(self, other: Any) -> ProcessedVectorBuilderBase:  # type: ignore[override]
        return self.lt(other)  # type: ignore[return-value]
    def __ge__(self, other: Any) -> ProcessedVectorBuilderBase:  # type: ignore[override]
        return self.ge(other)  # type: ignore[return-value]
    def __le__(self, other: Any) -> ProcessedVectorBuilderBase:  # type: ignore[override]
        return self.le(other)  # type: ignore[return-value]
    def __eq__(self, other: Any) -> ProcessedVectorBuilderBase:  # type: ignore[override]
        return self.eq(other)  # type: ignore[return-value]
    def __ne__(self, other: Any) -> ProcessedVectorBuilderBase:  # type: ignore[override]
        return self.ne(other)  # type: ignore[return-value]


class LogicalMixinBase:
    def and_(self, other: Any) -> 'ProcessedVectorBuilderBase':
        """Logical AND between vectors (set intersection semantics)."""
        raise NotImplementedError
    def or_(self, other: Any) -> 'ProcessedVectorBuilderBase':
        """Logical OR between vectors (set union semantics)."""
        raise NotImplementedError
    def unless(self, other: Any) -> 'ProcessedVectorBuilderBase':
        """Set difference: left unless right."""
        raise NotImplementedError

    # Operator overloads mapping to logical ops
    def __and__(self, other: Any) -> 'ProcessedVectorBuilderBase':  # type: ignore[override]
        return self.and_(other)  # type: ignore[return-value]
    def __or__(self, other: Any) -> 'ProcessedVectorBuilderBase':  # type: ignore[override]
        return self.or_(other)  # type: ignore[return-value]


class TimeRangeMixinBase:
    def offset(self, duration: str) -> Self:
        """Apply offset modifier (evaluate at ``now - duration``)."""
        raise NotImplementedError
    def at(self, timestamp: Any) -> Self:
        """Apply ``@`` modifier (evaluate at absolute time)."""
        raise NotImplementedError


class RangeVectorFunctionsMixinBase:
    def range(self, duration: str = "5m") -> 'RangeVectorBuilderBase':
        """Convert current expression to a range vector with given duration."""
        raise NotImplementedError
    def rate(self, duration: str = "5m") -> 'ProcessedVectorBuilderBase':
        """Per-second average rate of increase over the given window."""
        raise NotImplementedError
    def irate(self, duration: str = "5m") -> 'ProcessedVectorBuilderBase':
        """Instantaneous rate based on the last two samples."""
        raise NotImplementedError
    def idelta(self, duration: str = "5m") -> 'ProcessedVectorBuilderBase':
        """Instant delta (last two samples)."""
        raise NotImplementedError
    def increase(self, duration: str = "5m") -> 'ProcessedVectorBuilderBase':
        """Total increase over time window."""
        raise NotImplementedError
    def delta(self, duration: str = "5m") -> 'ProcessedVectorBuilderBase':
        """Difference between first and last sample in window."""
        raise NotImplementedError
    def changes(self, duration: str = "5m") -> 'ProcessedVectorBuilderBase':
        """Number of value changes over the time window."""
        raise NotImplementedError
    def resets(self, duration: str = "5m") -> 'ProcessedVectorBuilderBase':
        """Number of counter resets over the time window."""
        raise NotImplementedError
    def holt_winters(self, duration: str = "5m", smoothing_factor: float = 0.3, trend_factor: float = 0.3) -> 'ProcessedVectorBuilderBase':
        """Holt–Winters smoothing over the time window."""
        raise NotImplementedError
    def avg_over_time(self, duration: str = "5m") -> 'ProcessedVectorBuilderBase':
        """Average value over time window."""
        raise NotImplementedError
    def max_over_time(self, duration: str = "5m") -> 'ProcessedVectorBuilderBase':
        """Maximum value over time window."""
        raise NotImplementedError
    def min_over_time(self, duration: str = "5m") -> 'ProcessedVectorBuilderBase':
        """Minimum value over time window."""
        raise NotImplementedError
    def sum_over_time(self, duration: str = "5m") -> 'ProcessedVectorBuilderBase':
        """Sum over time window."""
        raise NotImplementedError
    def count_over_time(self, duration: str = "5m") -> 'ProcessedVectorBuilderBase':
        """Sample count over time window."""
        raise NotImplementedError
    def stddev_over_time(self, duration: str = "5m") -> 'ProcessedVectorBuilderBase':
        """Standard deviation over time window."""
        raise NotImplementedError
    def stdvar_over_time(self, duration: str = "5m") -> 'ProcessedVectorBuilderBase':
        """Variance over time window."""
        raise NotImplementedError
    def last_over_time(self, duration: str = "5m") -> 'ProcessedVectorBuilderBase':
        """Last (most recent) value over time window."""
        raise NotImplementedError
    def present_over_time(self, duration: str = "5m") -> 'ProcessedVectorBuilderBase':
        """1 if any samples exist in window, else 0."""
        raise NotImplementedError
    def deriv(self, duration: str = "5m") -> 'ProcessedVectorBuilderBase':
        """Per-second derivative over time window."""
        raise NotImplementedError
    def predict_linear(self, prediction_seconds: float, duration: str = "5m") -> 'ProcessedVectorBuilderBase':
        """Linear prediction of future values based on time window."""
        raise NotImplementedError
    def quantile_over_time(self, quantile: float, duration: str = "5m") -> 'ProcessedVectorBuilderBase':
        """Specified quantile over time window."""
        raise NotImplementedError
    def mad_over_time(self, duration: str = "5m") -> 'ProcessedVectorBuilderBase':
        """Median absolute deviation over time window."""
        raise NotImplementedError
    def median_over_time(self, duration: str = "5m") -> 'ProcessedVectorBuilderBase':
        """Median over time window."""
        raise NotImplementedError
    def mode_over_time(self, duration: str = "5m") -> 'ProcessedVectorBuilderBase':
        """Mode (most frequent value) over time window."""
        raise NotImplementedError
    def rate_over_sum(self, duration: str = "5m") -> 'ProcessedVectorBuilderBase':
        """rate()/sum_over_time() combined helper."""
        raise NotImplementedError
    def zscore_over_time(self, duration: str = "5m") -> 'ProcessedVectorBuilderBase':
        """Z-score over time window."""
        raise NotImplementedError
    def rollup(self, func: str, duration: str = "5m") -> 'ProcessedVectorBuilderBase':
        """Apply custom rollup function over time window."""
        raise NotImplementedError
    def rollup_rate(self, duration: str = "5m") -> 'ProcessedVectorBuilderBase':
        """Advanced rate calculation over time window."""
        raise NotImplementedError


class AggregationMixinBase:
    def sum(self, by: Optional[List[str]] = None, without: Optional[List[str]] = None) -> 'ProcessedVectorBuilderBase':
        """Sum aggregation with optional by/without labels."""
        raise NotImplementedError
    def avg(self, by: Optional[List[str]] = None, without: Optional[List[str]] = None) -> 'ProcessedVectorBuilderBase':
        """Average aggregation with optional by/without labels."""
        raise NotImplementedError
    def min(self, by: Optional[List[str]] = None, without: Optional[List[str]] = None) -> 'ProcessedVectorBuilderBase':
        """Minimum aggregation with optional by/without labels."""
        raise NotImplementedError
    def max(self, by: Optional[List[str]] = None, without: Optional[List[str]] = None) -> 'ProcessedVectorBuilderBase':
        """Maximum aggregation with optional by/without labels."""
        raise NotImplementedError
    def count(self, by: Optional[List[str]] = None, without: Optional[List[str]] = None) -> 'ProcessedVectorBuilderBase':
        """Count aggregation with optional by/without labels."""
        raise NotImplementedError
    def stddev(self, by: Optional[List[str]] = None, without: Optional[List[str]] = None) -> 'ProcessedVectorBuilderBase':
        """Standard deviation aggregation."""
        raise NotImplementedError
    def stdvar(self, by: Optional[List[str]] = None, without: Optional[List[str]] = None) -> 'ProcessedVectorBuilderBase':
        """Variance aggregation."""
        raise NotImplementedError
    def topk(self, k: Any, by: Optional[List[str]] = None, without: Optional[List[str]] = None) -> 'ProcessedVectorBuilderBase':
        """Top-k selection with optional grouping."""
        raise NotImplementedError
    def bottomk(self, k: Any, by: Optional[List[str]] = None, without: Optional[List[str]] = None) -> 'ProcessedVectorBuilderBase':
        """Bottom-k selection with optional grouping."""
        raise NotImplementedError
    def quantile(self, q: Any, by: Optional[List[str]] = None, without: Optional[List[str]] = None) -> 'ProcessedVectorBuilderBase':
        """Quantile aggregation with optional grouping."""
        raise NotImplementedError
    def histogram_quantile(self, q: Any) -> 'ProcessedVectorBuilderBase':
        """Histogram quantile aggregation."""
        raise NotImplementedError
    def count_values(self, label_name: str, by: Optional[List[str]] = None, without: Optional[List[str]] = None) -> 'ProcessedVectorBuilderBase':
        """Count of values grouped by a label."""
        raise NotImplementedError
    def group(self, by: Optional[List[str]] = None, without: Optional[List[str]] = None) -> 'ProcessedVectorBuilderBase':
        """Group modifier with by/without labels."""
        raise NotImplementedError
    def any(self, by: Optional[List[str]] = None, without: Optional[List[str]] = None) -> 'ProcessedVectorBuilderBase':
        """Any-value aggregation with optional grouping."""
        raise NotImplementedError
    def median(self, by: Optional[List[str]] = None, without: Optional[List[str]] = None) -> 'ProcessedVectorBuilderBase':
        """Median aggregation with optional grouping."""
        raise NotImplementedError
    def mode(self, by: Optional[List[str]] = None, without: Optional[List[str]] = None) -> 'ProcessedVectorBuilderBase':
        """Mode aggregation with optional grouping."""
        raise NotImplementedError
    def mad(self, by: Optional[List[str]] = None, without: Optional[List[str]] = None) -> 'ProcessedVectorBuilderBase':
        """Median absolute deviation aggregation."""
        raise NotImplementedError


class TransformationMixinBase:
    def parenthesize(self) -> 'ProcessedVectorBuilderBase':
        """Wrap current expression in parentheses."""
        raise NotImplementedError
    def bool(self) -> 'ProcessedVectorBuilderBase':
        """Convert expression to boolean (0/1)."""
        raise NotImplementedError
    def clamp_min(self, min_threshold: Any) -> 'ProcessedVectorBuilderBase':
        """Clamp values below threshold to the threshold."""
        raise NotImplementedError
    def clamp_max(self, max_threshold: Any) -> 'ProcessedVectorBuilderBase':
        """Clamp values above threshold to the threshold."""
        raise NotImplementedError
    def timestamp(self) -> 'ProcessedVectorBuilderBase':
        """Map samples to their timestamps."""
        raise NotImplementedError
    def label_replace(self, target_label: str, replacement: str, source_label: str, regex: str) -> 'ProcessedVectorBuilderBase':
        """Replace or create labels using regex captures."""
        raise NotImplementedError
    def label_join(self, target_label: str, separator: str, *source_labels: str) -> 'ProcessedVectorBuilderBase':
        """Join multiple label values into a target label."""
        raise NotImplementedError
    def label_set(self, **labels: str) -> 'ProcessedVectorBuilderBase':
        """Set labels to constant values (MetricsQL extension)."""
        raise NotImplementedError
    def label_del(self, *labels: str) -> 'ProcessedVectorBuilderBase':
        """Delete one or more labels from the current series set (MetricsQL extension)."""
        raise NotImplementedError
    def alias(self, name: str) -> 'ProcessedVectorBuilderBase':
        """Rename metric/series (MetricsQL extension)."""
        raise NotImplementedError
    def sort(self, direction: str = "asc") -> 'ProcessedVectorBuilderBase':
        """Sort time series by values (asc/desc)."""
        raise NotImplementedError
    def sort_desc(self) -> 'ProcessedVectorBuilderBase':
        """Sort time series by values in descending order."""
        raise NotImplementedError
    def sort_by_label(self, *label_names: str) -> 'ProcessedVectorBuilderBase':
        """Sort time series by the specified label values (MetricsQL extension)."""
        raise NotImplementedError
    def sort_by_label_desc(self, *label_names: str) -> 'ProcessedVectorBuilderBase':
        """Sort time series by the specified label values in descending order (MetricsQL extension)."""
        raise NotImplementedError
    def sort_by_label_numeric(self, *label_names: str) -> 'ProcessedVectorBuilderBase':
        """Sort time series by numeric interpretation of the labels (MetricsQL extension)."""
        raise NotImplementedError
    def sort_by_label_numeric_desc(self, *label_names: str) -> 'ProcessedVectorBuilderBase':
        """Sort time series by numeric interpretation of the labels in descending order (MetricsQL extension)."""
        raise NotImplementedError
    def day_of_week(self) -> 'ProcessedVectorBuilderBase':
        """Convert timestamp to day of week (0-6)."""
        raise NotImplementedError
    def day_of_month(self) -> 'ProcessedVectorBuilderBase':
        """Convert timestamp to day of month (1-31)."""
        raise NotImplementedError
    def day_of_year(self) -> 'ProcessedVectorBuilderBase':
        """Convert timestamp to day of year (1-366)."""
        raise NotImplementedError
    def hour(self) -> 'ProcessedVectorBuilderBase':
        """Extract hour from timestamp (0-23)."""
        raise NotImplementedError
    def minute(self) -> 'ProcessedVectorBuilderBase':
        """Extract minute from timestamp (0-59)."""
        raise NotImplementedError
    def month(self) -> 'ProcessedVectorBuilderBase':
        """Extract month from timestamp (1-12)."""
        raise NotImplementedError
    def year(self) -> 'ProcessedVectorBuilderBase':
        """Extract year from timestamp."""
        raise NotImplementedError
    def dedup(self) -> 'ProcessedVectorBuilderBase':
        """Remove duplicate series (MetricsQL extension)."""
        raise NotImplementedError
    def moving_average(self, duration: str = "5m") -> 'ProcessedVectorBuilderBase':
        """Moving average over duration (MetricsQL extension)."""
        raise NotImplementedError
    def smooth_exponential(self, smoothing_factor: float) -> 'ProcessedVectorBuilderBase':
        """Exponential smoothing (MetricsQL extension)."""
        raise NotImplementedError
    def keep_metric_names(self) -> 'ProcessedVectorBuilderBase':
        """Keep metric names after binary ops (VictoriaMetrics-specific)."""
        raise NotImplementedError
    def union(self, *others: Any) -> 'ProcessedVectorBuilderBase':
        """Union of multiple vector sets (MetricsQL extension)."""
        raise NotImplementedError
    def limitk(self, k: Any) -> 'ProcessedVectorBuilderBase':
        """Limit result to at most k series (MetricsQL extension)."""
        raise NotImplementedError
    def outliersk(self, k: Any) -> 'ProcessedVectorBuilderBase':
        """Return k outlier series (MetricsQL extension)."""
        raise NotImplementedError
    def subquery(self, range_duration: str, resolution: Optional[str] = None) -> 'ProcessedVectorBuilderBase':
        """Create a subquery over a range with optional resolution."""
        raise NotImplementedError
    def default(self, value: Union[int, float]) -> 'ProcessedVectorBuilderBase':
        """Fill gaps in time series with the specified default value (MetricsQL extension)."""
        raise NotImplementedError


class MathematicalMixinBase:
    def abs(self) -> 'ProcessedVectorBuilderBase':
        """Absolute value."""
        raise NotImplementedError
    def ceil(self) -> 'ProcessedVectorBuilderBase':
        """Ceiling function."""
        raise NotImplementedError
    def floor(self) -> 'ProcessedVectorBuilderBase':
        """Floor function."""
        raise NotImplementedError
    def round(self, to_nearest: Union[float, Any] = 1.0) -> 'ProcessedVectorBuilderBase':
        """Round to nearest value (or by another series)."""
        raise NotImplementedError
    def sqrt(self) -> 'ProcessedVectorBuilderBase':
        """Square root."""
        raise NotImplementedError
    def exp(self) -> 'ProcessedVectorBuilderBase':
        """Exponential function."""
        raise NotImplementedError
    def ln(self) -> 'ProcessedVectorBuilderBase':
        """Natural logarithm."""
        raise NotImplementedError
    def log2(self) -> 'ProcessedVectorBuilderBase':
        """Base-2 logarithm."""
        raise NotImplementedError
    def log10(self) -> 'ProcessedVectorBuilderBase':
        """Base-10 logarithm."""
        raise NotImplementedError
    def sin(self) -> 'ProcessedVectorBuilderBase':
        """Sine."""
        raise NotImplementedError
    def cos(self) -> 'ProcessedVectorBuilderBase':
        """Cosine."""
        raise NotImplementedError
    def tan(self) -> 'ProcessedVectorBuilderBase':
        """Tangent."""
        raise NotImplementedError
    def asin(self) -> 'ProcessedVectorBuilderBase':
        """Arcsine."""
        raise NotImplementedError
    def acos(self) -> 'ProcessedVectorBuilderBase':
        """Arccosine."""
        raise NotImplementedError
    def atan(self) -> 'ProcessedVectorBuilderBase':
        """Arctangent."""
        raise NotImplementedError
    def atan2(self, x: Union[float, Any]) -> 'ProcessedVectorBuilderBase':
        """Arctangent of y/x handling quadrants."""
        raise NotImplementedError
    def sinh(self) -> 'ProcessedVectorBuilderBase':
        """Hyperbolic sine."""
        raise NotImplementedError
    def cosh(self) -> 'ProcessedVectorBuilderBase':
        """Hyperbolic cosine."""
        raise NotImplementedError
    def tanh(self) -> 'ProcessedVectorBuilderBase':
        """Hyperbolic tangent."""
        raise NotImplementedError
    def asinh(self) -> 'ProcessedVectorBuilderBase':
        """Area hyperbolic sine."""
        raise NotImplementedError
    def acosh(self) -> 'ProcessedVectorBuilderBase':
        """Area hyperbolic cosine."""
        raise NotImplementedError
    def atanh(self) -> 'ProcessedVectorBuilderBase':
        """Area hyperbolic tangent."""
        raise NotImplementedError
    def deg(self) -> 'ProcessedVectorBuilderBase':
        """Convert radians to degrees."""
        raise NotImplementedError
    def rad(self) -> 'ProcessedVectorBuilderBase':
        """Convert degrees to radians."""
        raise NotImplementedError


class ValidationMixinBase:
    def validate(self, standard: str = "MetricsQL", strict: bool = True) -> str:
        """Validate built query against a standard; return normalized string."""
        raise NotImplementedError
    def _validate_promql_compatibility(self, query_string: str) -> str:
        """Best-effort PromQL compatibility validation; return diagnostics."""
        raise NotImplementedError
    def debug(self) -> str:
        """Return a human-readable debug representation of the query/AST."""
        raise NotImplementedError
    def _format_ast_tree(self, node: Any, indent: int = 0) -> str:
        """Format an AST subtree for debugging purposes."""
        raise NotImplementedError
    def analyze(self) -> dict:
        """Return analysis metadata such as functions used, label sets, etc."""
        raise NotImplementedError
    def visualize_positions(self, source_code: str) -> str:
        """Visualize AST node positions mapped onto given source code."""
        raise NotImplementedError
    def to_debug_json(self) -> str:
        """Return a JSON representation suitable for debugging tools."""
        raise NotImplementedError
    def debug_positions(self) -> str:
        """Return a textual dump of node positions for diagnostics."""
        raise NotImplementedError
