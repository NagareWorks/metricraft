"""Additional MetricsQL rollups with explicit or backend-selected windows."""
from .capabilities import vm_only


class ExtendedRollupMixin:
    __slots__ = ()

    @vm_only
    def ascent_over_time(self, window=None):
        return self._rollup("ascent_over_time", window)

    @vm_only
    def changes_prometheus(self, window=None):
        return self._rollup("changes_prometheus", window)

    @vm_only
    def decreases_over_time(self, window=None):
        return self._rollup("decreases_over_time", window)

    @vm_only
    def default_rollup(self, window=None):
        return self._rollup("default_rollup", window)

    @vm_only
    def delta_prometheus(self, window=None):
        return self._rollup("delta_prometheus", window)

    @vm_only
    def deriv_fast(self, window=None):
        return self._rollup("deriv_fast", window)

    @vm_only
    def descent_over_time(self, window=None):
        return self._rollup("descent_over_time", window)

    @vm_only
    def distinct_over_time(self, window=None):
        return self._rollup("distinct_over_time", window)

    @vm_only
    def geomean_over_time(self, window=None):
        return self._rollup("geomean_over_time", window)

    @vm_only
    def histogram_over_time(self, window=None):
        return self._rollup("histogram_over_time", window)

    @vm_only
    def ideriv(self, window=None):
        return self._rollup("ideriv", window)

    @vm_only
    def increase_prometheus(self, window=None):
        return self._rollup("increase_prometheus", window)

    @vm_only
    def increase_pure(self, window=None):
        return self._rollup("increase_pure", window)

    @vm_only
    def increases_over_time(self, window=None):
        return self._rollup("increases_over_time", window)

    @vm_only
    def integrate(self, window=None):
        return self._rollup("integrate", window)

    @vm_only
    def lag(self, window=None):
        return self._rollup("lag", window)

    @vm_only
    def lifetime(self, window=None):
        return self._rollup("lifetime", window)

    @vm_only
    def outlier_iqr_over_time(self, window=None):
        return self._rollup("outlier_iqr_over_time", window)

    @vm_only
    def range_over_time(self, window=None):
        return self._rollup("range_over_time", window)

    @vm_only
    def rate_prometheus(self, window=None):
        return self._rollup("rate_prometheus", window)

    @vm_only
    def scrape_interval(self, window=None):
        return self._rollup("scrape_interval", window)

    @vm_only
    def stale_samples_over_time(self, window=None):
        return self._rollup("stale_samples_over_time", window)

    @vm_only
    def sum2_over_time(self, window=None):
        return self._rollup("sum2_over_time", window)

    @vm_only
    def tfirst_over_time(self, window=None):
        return self._rollup("tfirst_over_time", window)

    @vm_only
    def timestamp_with_name(self, window=None):
        return self._rollup("timestamp_with_name", window)

    @vm_only
    def tlast_change_over_time(self, window=None):
        return self._rollup("tlast_change_over_time", window)

    @vm_only
    def tlast_over_time(self, window=None):
        return self._rollup("tlast_over_time", window)

    @vm_only
    def tmax_over_time(self, window=None):
        return self._rollup("tmax_over_time", window)

    @vm_only
    def tmin_over_time(self, window=None):
        return self._rollup("tmin_over_time", window)

    @vm_only
    def count_eq_over_time(self, value, window=None):
        source = self.range(window) if window is not None else self
        return self.function("count_eq_over_time", source, value)

    @vm_only
    def count_gt_over_time(self, value, window=None):
        source = self.range(window) if window is not None else self
        return self.function("count_gt_over_time", source, value)

    @vm_only
    def count_le_over_time(self, value, window=None):
        source = self.range(window) if window is not None else self
        return self.function("count_le_over_time", source, value)

    @vm_only
    def count_ne_over_time(self, value, window=None):
        source = self.range(window) if window is not None else self
        return self.function("count_ne_over_time", source, value)

    @vm_only
    def duration_over_time(self, value, window=None):
        source = self.range(window) if window is not None else self
        return self.function("duration_over_time", source, value)

    @vm_only
    def share_eq_over_time(self, value, window=None):
        source = self.range(window) if window is not None else self
        return self.function("share_eq_over_time", source, value)

    @vm_only
    def share_gt_over_time(self, value, window=None):
        source = self.range(window) if window is not None else self
        return self.function("share_gt_over_time", source, value)

    @vm_only
    def share_le_over_time(self, value, window=None):
        source = self.range(window) if window is not None else self
        return self.function("share_le_over_time", source, value)

    @vm_only
    def sum_eq_over_time(self, value, window=None):
        source = self.range(window) if window is not None else self
        return self.function("sum_eq_over_time", source, value)

    @vm_only
    def sum_gt_over_time(self, value, window=None):
        source = self.range(window) if window is not None else self
        return self.function("sum_gt_over_time", source, value)

    @vm_only
    def sum_le_over_time(self, value, window=None):
        source = self.range(window) if window is not None else self
        return self.function("sum_le_over_time", source, value)

    @vm_only
    def hoeffding_bound_lower(self, value, window=None):
        source = self.range(window) if window is not None else self
        return self.function("hoeffding_bound_lower", value, source)

    @vm_only
    def hoeffding_bound_upper(self, value, window=None):
        source = self.range(window) if window is not None else self
        return self.function("hoeffding_bound_upper", value, source)

    @vm_only
    def count_values_over_time(self, value, window=None):
        source = self.range(window) if window is not None else self
        return self.function("count_values_over_time", value, source)

    @vm_only
    def rollup_candlestick(self, window=None, *, result=None):
        source = self.range(window) if window is not None else self
        return self.function("rollup_candlestick", source, *(() if result is None else (result,)))

    @vm_only
    def rollup_delta(self, window=None, *, result=None):
        source = self.range(window) if window is not None else self
        return self.function("rollup_delta", source, *(() if result is None else (result,)))

    @vm_only
    def rollup_deriv(self, window=None, *, result=None):
        source = self.range(window) if window is not None else self
        return self.function("rollup_deriv", source, *(() if result is None else (result,)))

    @vm_only
    def rollup_increase(self, window=None, *, result=None):
        source = self.range(window) if window is not None else self
        return self.function("rollup_increase", source, *(() if result is None else (result,)))

    @vm_only
    def rollup_scrape_interval(self, window=None, *, result=None):
        source = self.range(window) if window is not None else self
        return self.function("rollup_scrape_interval", source, *(() if result is None else (result,)))

    @vm_only
    def quantiles_over_time(self, label, *quantiles, window=None):
        source = self.range(window) if window is not None else self
        return self.function("quantiles_over_time", label, *quantiles, source)

    @vm_only
    def aggr_over_time(self, *functions, window=None):
        source = self.range(window) if window is not None else self
        return self.function("aggr_over_time", self.from_tuple(*functions), source)
