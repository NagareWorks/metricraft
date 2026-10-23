"""Explicit scoped MetricsQL values/functions, with no global symbol registry."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ._types import QueryInput, ReferenceKind
from .capabilities import vm_only

if TYPE_CHECKING:
    from .query_builder import QueryBuilder


class TemplateMixin:
    __slots__ = ()

    @classmethod
    @vm_only
    def reference(cls, name: str, *, kind: ReferenceKind = "instant") -> QueryBuilder:
        """A symbolic reference, valid only within a binding or parameter scope."""
        return cls._apply("reference", name, kind)

    @classmethod
    @vm_only
    def template_call(
        cls, name: str, *args: QueryInput, kind: ReferenceKind = "instant"
    ) -> QueryBuilder:
        return cls._apply("template_call", name, kind, tuple(cls._coerce(x) for x in args))

    @classmethod
    @vm_only
    def template(cls, *parameters: str, body: QueryInput) -> QueryBuilder:
        return cls._apply("template", children=tuple(cls.from_string(p) for p in parameters) + (cls._coerce(body),))

    @vm_only
    def with_(self, **bindings: QueryInput) -> QueryBuilder:
        """Bind values or templates in insertion order; earlier bindings are visible."""
        args = (self,) + tuple(part for name, value in bindings.items()
                              for part in (self.from_string(name), self._coerce(value)))
        return self._apply("with", children=args)
