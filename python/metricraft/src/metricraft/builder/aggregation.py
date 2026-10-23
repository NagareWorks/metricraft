"""Aggregation construction and grouping."""
from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from ._types import Number, ScalarInput, StringInput
from .capabilities import vm_only, prom_only, prom_experimental

if TYPE_CHECKING:
    from .query_builder import QueryBuilder


class AggregationMixin:
    """Aggregation construction and grouping."""

    __slots__ = ()

    def aggregate(self, op: str, *others: ScalarInput) -> QueryBuilder:
        if op not in ("sum", "avg", "min", "max", "count", "stddev", "stdvar", "group",
                      "any", "median", "mode", "mad", "distinct", "geomean", "histogram",
                      "outliers_iqr", "share", "sum2", "zscore"):
            raise ValueError("unsupported aggregation")
        return self._apply(op, children=(self,) + tuple(self._coerce(q) for q in others))

    def sum(self, *others: ScalarInput) -> QueryBuilder:
        return self.aggregate("sum", *others)

    def avg(self, *others: ScalarInput) -> QueryBuilder:
        return self.aggregate("avg", *others)

    def min(self, *others: ScalarInput) -> QueryBuilder:
        return self.aggregate("min", *others)

    def max(self, *others: ScalarInput) -> QueryBuilder:
        return self.aggregate("max", *others)

    def count(self, *others: ScalarInput) -> QueryBuilder:
        return self.aggregate("count", *others)

    def stddev(self, *others: ScalarInput) -> QueryBuilder:
        return self.aggregate("stddev", *others)

    def stdvar(self, *others: ScalarInput) -> QueryBuilder:
        return self.aggregate("stdvar", *others)

    def group(self, *others: ScalarInput) -> QueryBuilder:
        return self.aggregate("group", *others)

    @vm_only
    def any(self, *others: ScalarInput) -> QueryBuilder:
        return self.aggregate("any", *others)

    @vm_only
    def median(self, *others: ScalarInput) -> QueryBuilder:
        return self.aggregate("median", *others)

    @vm_only
    def mode(self, *others: ScalarInput) -> QueryBuilder:
        return self.aggregate("mode", *others)

    @vm_only
    def mad(self, *others: ScalarInput) -> QueryBuilder:
        return self.aggregate("mad", *others)

    @vm_only
    def outliersk(self, k: ScalarInput) -> QueryBuilder:
        return self._parameter_aggregate("outliersk", k)

    @prom_experimental
    def limitk(self, k: ScalarInput) -> QueryBuilder:
        return self._parameter_aggregate("limitk", k)

    @prom_only
    @prom_experimental
    def limit_ratio(self, ratio: ScalarInput) -> QueryBuilder:
        return self._parameter_aggregate("limit_ratio", ratio)

    def _parameter_aggregate(self, name, value):
        return self._apply(name, children=(self._coerce(value), self))

    def topk(self, k: ScalarInput) -> QueryBuilder:
        return self._parameter_aggregate("topk", k)

    def bottomk(self, k: ScalarInput) -> QueryBuilder:
        return self._parameter_aggregate("bottomk", k)

    def quantile(self, q: ScalarInput) -> QueryBuilder:
        return self._parameter_aggregate("quantile", q)

    def count_values(self, label: StringInput) -> QueryBuilder:
        return self._parameter_aggregate("count_values", label)

    def by(self, *labels: str) -> QueryBuilder:
        return self._apply(
            "by", children=(self,) + tuple(self.from_string(x) for x in labels)
        )

    def without(self, *labels: str) -> QueryBuilder:
        return self._apply(
            "without", children=(self,) + tuple(self.from_string(x) for x in labels)
        )


    @vm_only
    def distinct(self, *others: ScalarInput) -> QueryBuilder:
        return self.aggregate("distinct", *others)

    @vm_only
    def geomean(self, *others: ScalarInput) -> QueryBuilder:
        return self.aggregate("geomean", *others)

    @vm_only
    def histogram(self, *others: ScalarInput) -> QueryBuilder:
        return self.aggregate("histogram", *others)

    @vm_only
    def outliers_iqr(self) -> QueryBuilder:
        return self.aggregate("outliers_iqr")

    @vm_only
    def share(self, *others: ScalarInput) -> QueryBuilder:
        return self.aggregate("share", *others)

    @vm_only
    def sum2(self, *others: ScalarInput) -> QueryBuilder:
        return self.aggregate("sum2", *others)

    @vm_only
    def zscore(self, *others: ScalarInput) -> QueryBuilder:
        return self.aggregate("zscore", *others)

    @vm_only
    def topk_avg(self, k: ScalarInput, *, other: Optional[str] = None) -> QueryBuilder:
        args = (self._coerce(k), self) + (() if other is None else (self.from_string(other),))
        return self._apply("topk_avg", children=args)

    @vm_only
    def topk_last(self, k: ScalarInput, *, other: Optional[str] = None) -> QueryBuilder:
        args = (self._coerce(k), self) + (() if other is None else (self.from_string(other),))
        return self._apply("topk_last", children=args)

    @vm_only
    def topk_max(self, k: ScalarInput, *, other: Optional[str] = None) -> QueryBuilder:
        args = (self._coerce(k), self) + (() if other is None else (self.from_string(other),))
        return self._apply("topk_max", children=args)

    @vm_only
    def topk_median(self, k: ScalarInput, *, other: Optional[str] = None) -> QueryBuilder:
        args = (self._coerce(k), self) + (() if other is None else (self.from_string(other),))
        return self._apply("topk_median", children=args)

    @vm_only
    def topk_min(self, k: ScalarInput, *, other: Optional[str] = None) -> QueryBuilder:
        args = (self._coerce(k), self) + (() if other is None else (self.from_string(other),))
        return self._apply("topk_min", children=args)

    @vm_only
    def bottomk_avg(self, k: ScalarInput, *, other: Optional[str] = None) -> QueryBuilder:
        args = (self._coerce(k), self) + (() if other is None else (self.from_string(other),))
        return self._apply("bottomk_avg", children=args)

    @vm_only
    def bottomk_last(self, k: ScalarInput, *, other: Optional[str] = None) -> QueryBuilder:
        args = (self._coerce(k), self) + (() if other is None else (self.from_string(other),))
        return self._apply("bottomk_last", children=args)

    @vm_only
    def bottomk_max(self, k: ScalarInput, *, other: Optional[str] = None) -> QueryBuilder:
        args = (self._coerce(k), self) + (() if other is None else (self.from_string(other),))
        return self._apply("bottomk_max", children=args)

    @vm_only
    def bottomk_median(self, k: ScalarInput, *, other: Optional[str] = None) -> QueryBuilder:
        args = (self._coerce(k), self) + (() if other is None else (self.from_string(other),))
        return self._apply("bottomk_median", children=args)

    @vm_only
    def bottomk_min(self, k: ScalarInput, *, other: Optional[str] = None) -> QueryBuilder:
        args = (self._coerce(k), self) + (() if other is None else (self.from_string(other),))
        return self._apply("bottomk_min", children=args)

    @vm_only
    def outliers_mad(self, tolerance: ScalarInput) -> QueryBuilder:
        return self._parameter_aggregate("outliers_mad", tolerance)

    @vm_only
    def quantiles(self, label: str, *quantiles: ScalarInput) -> QueryBuilder:
        return self._apply("quantiles", children=(self.from_string(label),) +
                           tuple(self._coerce(q) for q in quantiles) + (self,))

    @vm_only
    def limit(self, count: Number) -> QueryBuilder:
        return self._apply("aggregate_limit", children=(self, self.from_scalar(count)))
