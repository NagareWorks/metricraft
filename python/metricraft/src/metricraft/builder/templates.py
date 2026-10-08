"""Explicit scoped MetricsQL values/functions, with no global symbol registry."""
from .capabilities import vm_only


class TemplateMixin:
    __slots__ = ()

    @classmethod
    @vm_only
    def reference(cls, name, *, kind="instant"):
        """A symbolic reference, valid only within a binding or parameter scope."""
        return cls._apply("reference", name, kind)

    @classmethod
    @vm_only
    def template_call(cls, name, *args, kind="instant"):
        return cls._apply("template_call", name, kind, tuple(cls._coerce(x) for x in args))

    @classmethod
    @vm_only
    def template(cls, *parameters, body):
        return cls._apply("template", children=tuple(cls.from_string(p) for p in parameters) + (cls._coerce(body),))

    @vm_only
    def with_(self, **bindings):
        """Bind values or templates in insertion order; earlier bindings are visible."""
        args = (self,) + tuple(part for name, value in bindings.items()
                              for part in (self.from_string(name), self._coerce(value)))
        return self._apply("with", children=args)
