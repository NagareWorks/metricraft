"""Numeric, histogram and instant-vector functions."""
from __future__ import annotations

from .capabilities import vm_only, prom_only, prom_experimental
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .query_builder import QueryBuilder


class FunctionMixin:
    """Numeric, histogram and instant-vector functions."""

    __slots__ = ()

    def abs(self):
        return self._unary("abs")

    def ceil(self):
        return self._unary("ceil")

    def floor(self):
        return self._unary("floor")

    def sqrt(self):
        return self._unary("sqrt")

    def day_of_month(self) -> QueryBuilder:
        return self.function("day_of_month", self)

    def day_of_week(self) -> QueryBuilder:
        return self.function("day_of_week", self)

    def day_of_year(self) -> QueryBuilder:
        return self.function("day_of_year", self)

    def days_in_month(self) -> QueryBuilder:
        return self.function("days_in_month", self)

    def hour(self) -> QueryBuilder:
        return self.function("hour", self)

    def minute(self) -> QueryBuilder:
        return self.function("minute", self)

    def month(self) -> QueryBuilder:
        return self.function("month", self)

    def year(self) -> QueryBuilder:
        return self.function("year", self)

    def absent(self) -> QueryBuilder:
        return self.function("absent", self)

    def exp(self) -> QueryBuilder:
        return self.function("exp", self)

    def ln(self) -> QueryBuilder:
        return self.function("ln", self)

    def log2(self) -> QueryBuilder:
        return self.function("log2", self)

    def log10(self) -> QueryBuilder:
        return self.function("log10", self)

    def sgn(self) -> QueryBuilder:
        return self.function("sgn", self)

    def sort(self, direction="asc") -> QueryBuilder:
        if direction not in ("asc", "desc"):
            raise ValueError("sort direction must be asc or desc")
        return self.function("sort" if direction == "asc" else "sort_desc", self)

    def sort_desc(self) -> QueryBuilder:
        return self.function("sort_desc", self)

    @prom_experimental
    def sort_by_label(self, *labels):
        return self.function("sort_by_label", self, *labels)

    @prom_experimental
    def sort_by_label_desc(self, *labels):
        return self.function("sort_by_label_desc", self, *labels)

    @vm_only
    def sort_by_label_numeric(self, *labels):
        return self.function("sort_by_label_numeric", self, *labels)

    @vm_only
    def sort_by_label_numeric_desc(self, *labels):
        return self.function("sort_by_label_numeric_desc", self, *labels)

    def timestamp(self) -> QueryBuilder:
        return self.function("timestamp", self)

    def sin(self) -> QueryBuilder:
        return self.function("sin", self)

    def cos(self) -> QueryBuilder:
        return self.function("cos", self)

    def tan(self) -> QueryBuilder:
        return self.function("tan", self)

    def asin(self) -> QueryBuilder:
        return self.function("asin", self)

    def acos(self) -> QueryBuilder:
        return self.function("acos", self)

    def atan(self) -> QueryBuilder:
        return self.function("atan", self)

    def sinh(self) -> QueryBuilder:
        return self.function("sinh", self)

    def cosh(self) -> QueryBuilder:
        return self.function("cosh", self)

    def tanh(self) -> QueryBuilder:
        return self.function("tanh", self)

    def asinh(self) -> QueryBuilder:
        return self.function("asinh", self)

    def acosh(self) -> QueryBuilder:
        return self.function("acosh", self)

    def atanh(self) -> QueryBuilder:
        return self.function("atanh", self)

    def deg(self) -> QueryBuilder:
        return self.function("deg", self)

    def rad(self) -> QueryBuilder:
        return self.function("rad", self)

    def histogram_avg(self) -> QueryBuilder:
        return self.function("histogram_avg", self)

    def histogram_stddev(self) -> QueryBuilder:
        return self.function("histogram_stddev", self)

    def histogram_stdvar(self) -> QueryBuilder:
        return self.function("histogram_stdvar", self)

    @prom_only
    @prom_experimental
    def info(self, data_labels=None):
        return self.function("info", self) if data_labels is None else self.function("info", self, data_labels)

    @prom_only
    def histogram_count(self) -> QueryBuilder:
        return self.function("histogram_count", self)

    @prom_only
    def histogram_sum(self) -> QueryBuilder:
        return self.function("histogram_sum", self)

    def scalar(self) -> QueryBuilder:
        return self.function("scalar", self)

    def histogram_quantile(self, q, *, bounds_label=None):
        return self.function("histogram_quantile", q, self,
                             *(() if bounds_label is None else (bounds_label,)))

    def histogram_fraction(self, lower, upper):
        return self.function("histogram_fraction", lower, upper, self)

    @vm_only
    def smooth_exponential(self, smoothing_factor):
        return self.function("smooth_exponential", self, smoothing_factor)

    def clamp(self, minimum, maximum):
        return self.function("clamp", self, minimum, maximum)

    def clamp_min(self, minimum):
        return self.function("clamp_min", self, minimum)

    def clamp_max(self, maximum):
        return self.function("clamp_max", self, maximum)

    def round(self, nearest=None, *, to_nearest=None):
        if nearest is not None and to_nearest is not None:
            raise TypeError("pass either nearest or to_nearest, not both")
        nearest = to_nearest if nearest is None else nearest
        return (
            self.function("round", self)
            if nearest is None
            else self.function("round", self, nearest)
        )

    @prom_only
    @prom_experimental
    def min_of(self, other):
        return self.function("min_of", self, other)

    @prom_only
    @prom_experimental
    def max_of(self, other):
        return self.function("max_of", self, other)
