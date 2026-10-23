"""MetricsQL vector transforms and query-time scalar factories."""
from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from ._types import ScalarInput, StringInput
from .capabilities import vm_only, prom_experimental

if TYPE_CHECKING:
    from .query_builder import QueryBuilder


class TransformMixin:
    __slots__ = ()

    @vm_only
    def drop_empty_series(self) -> QueryBuilder:
        return self.function("drop_empty_series", self)

    @vm_only
    def interpolate(self) -> QueryBuilder:
        return self.function("interpolate", self)

    @vm_only
    def keep_last_value(self) -> QueryBuilder:
        return self.function("keep_last_value", self)

    @vm_only
    def keep_next_value(self) -> QueryBuilder:
        return self.function("keep_next_value", self)

    @vm_only
    def prometheus_buckets(self) -> QueryBuilder:
        return self.function("prometheus_buckets", self)

    @vm_only
    def range_avg(self) -> QueryBuilder:
        return self.function("range_avg", self)

    @vm_only
    def range_first(self) -> QueryBuilder:
        return self.function("range_first", self)

    @vm_only
    def range_last(self) -> QueryBuilder:
        return self.function("range_last", self)

    @vm_only
    def range_linear_regression(self) -> QueryBuilder:
        return self.function("range_linear_regression", self)

    @vm_only
    def range_mad(self) -> QueryBuilder:
        return self.function("range_mad", self)

    @vm_only
    def range_max(self) -> QueryBuilder:
        return self.function("range_max", self)

    @vm_only
    def range_median(self) -> QueryBuilder:
        return self.function("range_median", self)

    @vm_only
    def range_min(self) -> QueryBuilder:
        return self.function("range_min", self)

    @vm_only
    def range_stddev(self) -> QueryBuilder:
        return self.function("range_stddev", self)

    @vm_only
    def range_stdvar(self) -> QueryBuilder:
        return self.function("range_stdvar", self)

    @vm_only
    def range_sum(self) -> QueryBuilder:
        return self.function("range_sum", self)

    @vm_only
    def range_zscore(self) -> QueryBuilder:
        return self.function("range_zscore", self)

    @vm_only
    def remove_resets(self) -> QueryBuilder:
        return self.function("remove_resets", self)

    @vm_only
    def running_avg(self) -> QueryBuilder:
        return self.function("running_avg", self)

    @vm_only
    def running_max(self) -> QueryBuilder:
        return self.function("running_max", self)

    @vm_only
    def running_min(self) -> QueryBuilder:
        return self.function("running_min", self)

    @vm_only
    def running_sum(self) -> QueryBuilder:
        return self.function("running_sum", self)

    @vm_only
    def ttf(self) -> QueryBuilder:
        return self.function("ttf", self)

    @vm_only
    def bitmap_and(self, value: ScalarInput) -> QueryBuilder:
        return self.function("bitmap_and", self, value)

    @vm_only
    def bitmap_or(self, value: ScalarInput) -> QueryBuilder:
        return self.function("bitmap_or", self, value)

    @vm_only
    def bitmap_xor(self, value: ScalarInput) -> QueryBuilder:
        return self.function("bitmap_xor", self, value)

    @vm_only
    def ru(self, value: ScalarInput) -> QueryBuilder:
        return self.function("ru", self, value)

    @vm_only
    def buckets_limit(self, value: ScalarInput) -> QueryBuilder:
        return self.function("buckets_limit", value, self)

    @vm_only
    def range_quantile(self, value: ScalarInput) -> QueryBuilder:
        return self.function("range_quantile", value, self)

    @vm_only
    def range_trim_outliers(self, value: ScalarInput) -> QueryBuilder:
        return self.function("range_trim_outliers", value, self)

    @vm_only
    def range_trim_spikes(self, value: ScalarInput) -> QueryBuilder:
        return self.function("range_trim_spikes", value, self)

    @vm_only
    def range_trim_zscore(self, value: ScalarInput) -> QueryBuilder:
        return self.function("range_trim_zscore", value, self)

    @classmethod
    @vm_only
    def rand(cls, seed: Optional[ScalarInput] = None) -> QueryBuilder:
        return cls.function("rand", *(() if seed is None else (seed,)))

    @classmethod
    @vm_only
    def rand_exponential(cls, seed: Optional[ScalarInput] = None) -> QueryBuilder:
        return cls.function("rand_exponential", *(() if seed is None else (seed,)))

    @classmethod
    @vm_only
    def rand_normal(cls, seed: Optional[ScalarInput] = None) -> QueryBuilder:
        return cls.function("rand_normal", *(() if seed is None else (seed,)))

    @vm_only
    def range_normalize(self, *others: ScalarInput) -> QueryBuilder:
        return self.function("range_normalize", self, *others)

    @vm_only
    def limit_offset(self, limit: ScalarInput, offset: ScalarInput) -> QueryBuilder:
        return self.function("limit_offset", limit, offset, self)

    @vm_only
    def histogram_share(
        self, bound: ScalarInput, *, bounds_label: Optional[StringInput] = None
    ) -> QueryBuilder:
        return self.function("histogram_share", bound, self,
                             *(() if bounds_label is None else (bounds_label,)))

    @prom_experimental
    def histogram_quantiles(self, label: StringInput, *quantiles: ScalarInput) -> QueryBuilder:
        """Build the argument order required by the selected dialect."""
        return self._apply("histogram_quantiles_auto", children=(
            self._coerce(label), *(self._coerce(q) for q in quantiles), self))

    @classmethod
    @vm_only
    def timezone_offset(cls, timezone: StringInput) -> QueryBuilder:
        return cls.function("timezone_offset", timezone)
