"""Windowed functions and rollup convenience forms."""
from __future__ import annotations

from .capabilities import vm_only, prom_only, prom_experimental
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .query_builder import QueryBuilder


class RollupMixin:
    """Windowed functions and rollup convenience forms."""

    __slots__ = ()

    def _rollup(self, name, window=None):
        source = self.range(window) if window is not None else self
        return self.function(name, source)

    def rate(self, window=None, *, duration=None) -> QueryBuilder:
        return self._rollup("rate", self._window(window, duration))

    def first_over_time(self, window=None):
        return self._rollup("first_over_time", window)

    @prom_only
    @prom_experimental
    def ts_of_first_over_time(self, window=None):
        return self._rollup("ts_of_first_over_time", window)

    def irate(self, window=None, *, duration=None) -> QueryBuilder:
        return self._rollup("irate", self._window(window, duration))

    def increase(self, window=None, *, duration=None) -> QueryBuilder:
        return self._rollup("increase", self._window(window, duration))

    def delta(self, window=None, *, duration=None) -> QueryBuilder:
        return self._rollup("delta", self._window(window, duration))

    def sum_over_time(self, window=None, *, duration=None) -> QueryBuilder:
        return self._rollup("sum_over_time", self._window(window, duration))

    def avg_over_time(self, window=None, *, duration=None) -> QueryBuilder:
        return self._rollup("avg_over_time", self._window(window, duration))

    def max_over_time(self, window=None, *, duration=None) -> QueryBuilder:
        return self._rollup("max_over_time", self._window(window, duration))

    def min_over_time(self, window=None, *, duration=None) -> QueryBuilder:
        return self._rollup("min_over_time", self._window(window, duration))

    def idelta(self, window=None, *, duration=None) -> QueryBuilder:
        return self._rollup("idelta", self._window(window, duration))

    def deriv(self, window=None, *, duration=None) -> QueryBuilder:
        return self._rollup("deriv", self._window(window, duration))

    def changes(self, window=None, *, duration=None) -> QueryBuilder:
        return self._rollup("changes", self._window(window, duration))

    def resets(self, window=None, *, duration=None) -> QueryBuilder:
        return self._rollup("resets", self._window(window, duration))

    def count_over_time(self, window=None, *, duration=None) -> QueryBuilder:
        return self._rollup("count_over_time", self._window(window, duration))

    def stddev_over_time(self, window=None, *, duration=None) -> QueryBuilder:
        return self._rollup("stddev_over_time", self._window(window, duration))

    def stdvar_over_time(self, window=None, *, duration=None) -> QueryBuilder:
        return self._rollup("stdvar_over_time", self._window(window, duration))

    def last_over_time(self, window=None, *, duration=None) -> QueryBuilder:
        return self._rollup("last_over_time", self._window(window, duration))

    def present_over_time(self, window=None, *, duration=None) -> QueryBuilder:
        return self._rollup("present_over_time", self._window(window, duration))

    def absent_over_time(self, window=None, *, duration=None) -> QueryBuilder:
        return self._rollup("absent_over_time", self._window(window, duration))

    @prom_experimental
    def mad_over_time(self, window=None, *, duration=None) -> QueryBuilder:
        return self._rollup("mad_over_time", self._window(window, duration))

    @vm_only
    def median_over_time(self, window=None, *, duration=None) -> QueryBuilder:
        return self._rollup("median_over_time", self._window(window, duration))

    @vm_only
    def mode_over_time(self, window=None, *, duration=None) -> QueryBuilder:
        return self._rollup("mode_over_time", self._window(window, duration))

    @vm_only
    def zscore_over_time(self, window=None, *, duration=None) -> QueryBuilder:
        return self._rollup("zscore_over_time", self._window(window, duration))

    @vm_only
    def rate_over_sum(self, window=None, *, duration=None) -> QueryBuilder:
        return self._rollup("rate_over_sum", self._window(window, duration))

    @vm_only
    def rollup(self, window=None, duration=None, *, result=None, func=None) -> QueryBuilder:
        if isinstance(window, str) and window in ("min", "max", "avg"):
            if result is not None or func is not None:
                raise TypeError("rollup result was supplied twice")
            result, window = window, duration if duration is not None else "5m"
        elif func is not None:
            if result is not None:
                raise TypeError("pass either result or func, not both")
            result = func
            window = self._window(window, duration, "5m")
        else:
            window = self._window(window, duration)
        source = self.range(window) if window is not None else self
        return self.function("rollup", source) if result is None else self.function("rollup", source, result)

    @vm_only
    def rollup_rate(self, window=None, *, result=None, duration=None) -> QueryBuilder:
        window = self._window(window, duration)
        source = self.range(window) if window is not None else self
        return self.function("rollup_rate", source) if result is None else self.function("rollup_rate", source, result)

    @prom_only
    @prom_experimental
    def ts_of_last_over_time(self, window=None, *, duration=None):
        return self._rollup("ts_of_last_over_time", self._window(window, duration))

    @prom_only
    @prom_experimental
    def ts_of_max_over_time(self, window=None, *, duration=None):
        return self._rollup("ts_of_max_over_time", self._window(window, duration))

    @prom_only
    @prom_experimental
    def ts_of_min_over_time(self, window=None, *, duration=None):
        return self._rollup("ts_of_min_over_time", self._window(window, duration))

    def quantile_over_time(self, q=None, window=None, *, quantile=None, duration=None):
        if q is not None and quantile is not None:
            raise TypeError("pass either q or quantile, not both")
        source_window = self._window(window, duration)
        source = self.range(source_window) if source_window is not None else self
        return self.function("quantile_over_time", quantile if q is None else q, source)

    def predict_linear(self, seconds=None, window=None, *, prediction_seconds=None, duration=None):
        if seconds is not None and prediction_seconds is not None:
            raise TypeError("pass either seconds or prediction_seconds, not both")
        source_window = self._window(window, duration)
        source = self.range(source_window) if source_window is not None else self
        return self.function("predict_linear", source, prediction_seconds if seconds is None else seconds)

    @vm_only
    def holt_winters(self, duration="5m", smoothing_factor=0.3, trend_factor=0.3):
        source = self.range(duration) if duration is not None else self
        return self.function("holt_winters", source, smoothing_factor, trend_factor)

    @prom_only
    @prom_experimental
    def double_exponential_smoothing(self, window=None, *, smoothing_factor=0.3, trend_factor=0.3):
        source = self.range(window) if window is not None else self
        return self.function("double_exponential_smoothing", source, smoothing_factor, trend_factor)

    def moving_average(self, duration="5m"):
        """Moving mean using the upstream avg_over_time function."""
        return self._rollup("avg_over_time", duration)
