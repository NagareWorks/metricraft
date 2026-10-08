"""MetricsQL vector transforms and query-time scalar factories."""
from .capabilities import vm_only, prom_experimental


class TransformMixin:
    __slots__ = ()

    @vm_only
    def drop_empty_series(self):
        return self.function("drop_empty_series", self)

    @vm_only
    def interpolate(self):
        return self.function("interpolate", self)

    @vm_only
    def keep_last_value(self):
        return self.function("keep_last_value", self)

    @vm_only
    def keep_next_value(self):
        return self.function("keep_next_value", self)

    @vm_only
    def prometheus_buckets(self):
        return self.function("prometheus_buckets", self)

    @vm_only
    def range_avg(self):
        return self.function("range_avg", self)

    @vm_only
    def range_first(self):
        return self.function("range_first", self)

    @vm_only
    def range_last(self):
        return self.function("range_last", self)

    @vm_only
    def range_linear_regression(self):
        return self.function("range_linear_regression", self)

    @vm_only
    def range_mad(self):
        return self.function("range_mad", self)

    @vm_only
    def range_max(self):
        return self.function("range_max", self)

    @vm_only
    def range_median(self):
        return self.function("range_median", self)

    @vm_only
    def range_min(self):
        return self.function("range_min", self)

    @vm_only
    def range_stddev(self):
        return self.function("range_stddev", self)

    @vm_only
    def range_stdvar(self):
        return self.function("range_stdvar", self)

    @vm_only
    def range_sum(self):
        return self.function("range_sum", self)

    @vm_only
    def range_zscore(self):
        return self.function("range_zscore", self)

    @vm_only
    def remove_resets(self):
        return self.function("remove_resets", self)

    @vm_only
    def running_avg(self):
        return self.function("running_avg", self)

    @vm_only
    def running_max(self):
        return self.function("running_max", self)

    @vm_only
    def running_min(self):
        return self.function("running_min", self)

    @vm_only
    def running_sum(self):
        return self.function("running_sum", self)

    @vm_only
    def ttf(self):
        return self.function("ttf", self)

    @vm_only
    def bitmap_and(self, value):
        return self.function("bitmap_and", self, value)

    @vm_only
    def bitmap_or(self, value):
        return self.function("bitmap_or", self, value)

    @vm_only
    def bitmap_xor(self, value):
        return self.function("bitmap_xor", self, value)

    @vm_only
    def ru(self, value):
        return self.function("ru", self, value)

    @vm_only
    def buckets_limit(self, value):
        return self.function("buckets_limit", value, self)

    @vm_only
    def range_quantile(self, value):
        return self.function("range_quantile", value, self)

    @vm_only
    def range_trim_outliers(self, value):
        return self.function("range_trim_outliers", value, self)

    @vm_only
    def range_trim_spikes(self, value):
        return self.function("range_trim_spikes", value, self)

    @vm_only
    def range_trim_zscore(self, value):
        return self.function("range_trim_zscore", value, self)

    @classmethod
    @vm_only
    def rand(cls, seed=None):
        return cls.function("rand", *(() if seed is None else (seed,)))

    @classmethod
    @vm_only
    def rand_exponential(cls, seed=None):
        return cls.function("rand_exponential", *(() if seed is None else (seed,)))

    @classmethod
    @vm_only
    def rand_normal(cls, seed=None):
        return cls.function("rand_normal", *(() if seed is None else (seed,)))

    @vm_only
    def range_normalize(self, *others):
        return self.function("range_normalize", self, *others)

    @vm_only
    def limit_offset(self, limit, offset):
        return self.function("limit_offset", limit, offset, self)

    @vm_only
    def histogram_share(self, bound, *, bounds_label=None):
        return self.function("histogram_share", bound, self,
                             *(() if bounds_label is None else (bounds_label,)))

    @prom_experimental
    def histogram_quantiles(self, label, *quantiles):
        """Build the argument order required by the selected dialect."""
        return self._apply("histogram_quantiles_auto", children=(
            self._coerce(label), *(self._coerce(q) for q in quantiles), self))

    @classmethod
    @vm_only
    def timezone_offset(cls, timezone):
        return cls.function("timezone_offset", timezone)
