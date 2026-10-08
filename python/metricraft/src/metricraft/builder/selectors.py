"""Immutable selector matchers."""
from __future__ import annotations

from typing import TYPE_CHECKING
from .capabilities import vm_only

if TYPE_CHECKING:
    from .query_builder import QueryBuilder


class SelectorMixin:
    """Immutable selector matchers."""

    __slots__ = ()

    def where(self, label: str, operator: str, value: str) -> QueryBuilder:
        if operator not in ("=", "!=", "=~", "!~"):
            raise ValueError("invalid matcher operator")
        from ._expression import Expression
        if isinstance(value, Expression):
            return self._apply("match_expr", label, operator, (self, value))
        return self._unary(operator, label, "" if value is None else value)

    def where_eq(self, label: str, value: str) -> QueryBuilder:
        return self.where(label, "=", value)

    def where_ne(self, label: str, value: str) -> QueryBuilder:
        return self.where(label, "!=", value)

    def where_regex(self, label: str, value: str) -> QueryBuilder:
        return self.where(label, "=~", value)

    def where_not_regex(self, label: str, value: str) -> QueryBuilder:
        return self.where(label, "!~", value)

    filter = where_eq

    @vm_only
    def or_selector(self, *others):
        """Combine selector alternatives inside a MetricsQL selector."""
        return self._apply("selector_or", children=(self,) + others)
