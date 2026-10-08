"""
Function enumerations for PromQL/MetricsQL.

This module contains all function name enumerations organized by category.
This provides type safety and centralized management of function names.
"""

from metricraft._legacy.enums.base import FunctionEnum


class RangeVectorFunction(FunctionEnum):
    """Range vector function names for functions that operate on range vectors."""

    # Basic rate and increase functions
    RATE = "rate"
    IRATE = "irate"
    INCREASE = "increase"
    DELTA = "delta"
    IDELTA = "idelta"
    CHANGES = "changes"
    RESETS = "resets"
    DERIV = "deriv"

    # Over time aggregations
    AVG_OVER_TIME = "avg_over_time"
    MAX_OVER_TIME = "max_over_time"
    MIN_OVER_TIME = "min_over_time"
    SUM_OVER_TIME = "sum_over_time"
    COUNT_OVER_TIME = "count_over_time"
    STDDEV_OVER_TIME = "stddev_over_time"
    STDVAR_OVER_TIME = "stdvar_over_time"
    LAST_OVER_TIME = "last_over_time"
    PRESENT_OVER_TIME = "present_over_time"

    # MetricsQL extensions
    MAD_OVER_TIME = "mad_over_time"
    MEDIAN_OVER_TIME = "median_over_time"
    MODE_OVER_TIME = "mode_over_time"
    QUANTILE_OVER_TIME = "quantile_over_time"
    ZSCORE_OVER_TIME = "zscore_over_time"
    RATE_OVER_SUM = "rate_over_sum"

    # Advanced functions
    PREDICT_LINEAR = "predict_linear"
    HOLT_WINTERS = "holt_winters"
    ROLLUP = "rollup"
    ROLLUP_RATE = "rollup_rate"

    @property
    def is_standard_promql(self) -> bool:
        """Check if this function is part of standard PromQL."""
        standard = {
            self.RATE, self.IRATE, self.INCREASE, self.DELTA, self.IDELTA,
            self.CHANGES, self.RESETS, self.DERIV, self.AVG_OVER_TIME,
            self.MAX_OVER_TIME, self.MIN_OVER_TIME, self.SUM_OVER_TIME,
            self.COUNT_OVER_TIME, self.STDDEV_OVER_TIME, self.STDVAR_OVER_TIME,
            self.LAST_OVER_TIME, self.PRESENT_OVER_TIME, self.PREDICT_LINEAR,
            self.HOLT_WINTERS
        }
        return self in standard

    @property
    def requires_duration(self) -> bool:
        """Check if this function requires a duration parameter."""
        return True  # All range vector functions require duration

    @property
    def requires_extra_params(self) -> bool:
        """Check if this function requires additional parameters beyond duration."""
        return self in {
            self.QUANTILE_OVER_TIME, self.PREDICT_LINEAR,
            self.HOLT_WINTERS, self.ROLLUP
        }


class MathFunction(FunctionEnum):
    """Mathematical function names."""

    # Basic math
    ABS = "abs"
    CEIL = "ceil"
    FLOOR = "floor"
    ROUND = "round"
    SQRT = "sqrt"

    # Trigonometric
    SIN = "sin"
    COS = "cos"
    TAN = "tan"
    ASIN = "asin"
    ACOS = "acos"
    ATAN = "atan"
    ATAN2 = "atan2"

    # Hyperbolic functions
    SINH = "sinh"
    COSH = "cosh"
    TANH = "tanh"
    ASINH = "asinh"
    ACOSH = "acosh"
    ATANH = "atanh"

    # Exponential and logarithmic
    EXP = "exp"
    LN = "ln"
    LOG2 = "log2"
    LOG10 = "log10"

    # Statistical
    HISTOGRAM_QUANTILE = "histogram_quantile"

    # Clamp functions
    CLAMP = "clamp"
    CLAMP_MAX = "clamp_max"
    CLAMP_MIN = "clamp_min"

    @property
    def is_trigonometric(self) -> bool:
        """Check if this is a trigonometric function."""
        return self in {
            self.SIN, self.COS, self.TAN,
            self.ASIN, self.ACOS, self.ATAN, self.ATAN2
        }

    @property
    def is_logarithmic(self) -> bool:
        """Check if this is a logarithmic function."""
        return self in {self.EXP, self.LN, self.LOG2, self.LOG10}


class TransformationFunction(FunctionEnum):
    """Data transformation function names."""

    # Value manipulation
    SCALAR = "scalar"
    VECTOR = "vector"

    # Missing data handling
    ABSENT = "absent"
    ABSENT_OVER_TIME = "absent_over_time"

    # Resets and changes
    RESETS = "resets"
    CHANGES = "changes"

    # Type conversion
    BOOL = "bool"
    TIMESTAMP = "timestamp"

    # MetricsQL transformations
    INTERPOLATE = "interpolate"
    KEEP_LAST_VALUE = "keep_last_value"
    REMOVE_RESETS = "remove_resets"
    RUNNING_AVG = "running_avg"
    RUNNING_MAX = "running_max"
    RUNNING_MIN = "running_min"
    RUNNING_SUM = "running_sum"
    DEDUP = "dedup"


class DateTimeFunction(FunctionEnum):
    """Date and time function names."""

    # Time extraction
    TIME = "time"
    NOW = "now"

    # Date components
    YEAR = "year"
    MONTH = "month"
    DAY_OF_MONTH = "day_of_month"
    DAY_OF_WEEK = "day_of_week"
    DAY_OF_YEAR = "day_of_year"
    HOUR = "hour"
    MINUTE = "minute"

    # Time manipulation
    TIMESTAMP = "timestamp"

    # Special time functions
    DAYS_IN_MONTH = "days_in_month"


class SortFunction(FunctionEnum):
    """Sorting function names."""

    SORT = "sort"
    SORT_DESC = "sort_desc"
    SORT_BY_LABEL = "sort_by_label"
    SORT_BY_LABEL_DESC = "sort_by_label_desc"
    SORT_BY_LABEL_NUMERIC = "sort_by_label_numeric"
    SORT_BY_LABEL_NUMERIC_DESC = "sort_by_label_numeric_desc"


class FilterFunction(FunctionEnum):
    """Filtering function names."""

    # Basic filtering
    ABSENT = "absent"
    ABSENT_OVER_TIME = "absent_over_time"

    # MetricsQL filtering
    LIMIT_OFFSET = "limit_offset"


class LabelFunction(FunctionEnum):
    """Label manipulation function names."""

    LABEL_REPLACE = "label_replace"
    LABEL_JOIN = "label_join"

    # MetricsQL label functions
    LABEL_SET = "label_set"
    LABEL_DEL = "label_del"
    LABEL_KEEP = "label_keep"
    LABEL_COPY = "label_copy"
    LABEL_MOVE = "label_move"
    ALIAS = "alias"


class MetricsQLFunction(FunctionEnum):
    """MetricsQL-specific function names not covered by other categories."""

    # Aggregation helpers
    WITH = "with"

    # Special functions
    START = "start"
    END = "end"
    STEP = "step"

    # Series manipulation
    UNION = "union"

    # Performance functions
    BITMAP_AND = "bitmap_and"
    BITMAP_OR = "bitmap_or"
    BITMAP_XOR = "bitmap_xor"
