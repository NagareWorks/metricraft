"""Owning immutable native handle and the shared construction/build boundary."""
from __future__ import annotations

from typing import Union
from weakref import finalize
from .capabilities import QueryMode
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .query_builder import QueryBuilder


class Expression:
    """Owning immutable native handle and the shared construction/build boundary."""

    __slots__ = ("_handle", "__weakref__")

    def __init__(self, *args, **kwargs):
        if args or kwargs:
            raise TypeError(
                "QueryBuilder() takes no configuration; select the dialect with build(mode=...)"
            )
        # A stateless factory is retained for QueryBuilder().from_metric(...).
        # It needs neither server configuration nor a native allocation.
        if hasattr(self, "_handle"):
            raise AttributeError("query expressions are immutable")
        object.__setattr__(self, "_handle", None)

    def __setattr__(self, name, value):
        raise AttributeError("query expressions are immutable")

    def __delattr__(self, name):
        raise AttributeError("query expressions are immutable")

    @classmethod
    def _apply(cls, op, a="", b="", children=()):
        for child in children:
            if child._handle is None:
                raise ValueError(
                    "start with from_metric() or from_scalar() before composing a query"
                )
        from .. import _native

        expression = object.__new__(cls)
        object.__setattr__(expression, "_handle", _native.create(op, a, b, children))
        finalize(expression, _native.lib.mc_expr_free, expression._handle)
        return expression

    @classmethod
    def from_metric(cls, name: str) -> QueryBuilder:
        return cls._apply("metric", name)

    @classmethod
    def from_labels(cls, **labels) -> QueryBuilder:
        """Unnamed selector; PromQL build requires a matcher excluding empty values."""
        return cls._apply("selector", children=tuple(
            cls.from_string(part) for item in labels.items() for part in item
        ))

    @classmethod
    def from_scalar(cls, value: Union[int, float]) -> QueryBuilder:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("scalar must be a number")
        return cls._apply("number", str(value))

    @classmethod
    def from_string(cls, value: str) -> QueryBuilder:
        return cls._apply("string", value)

    @classmethod
    def from_tuple(cls, *values) -> QueryBuilder:
        """MetricsQL string/scalar tuple; elements remain typed, escaped expressions."""
        return cls._apply("tuple", children=tuple(cls._coerce(value) for value in values))

    @classmethod
    def from_duration(cls, value: str) -> QueryBuilder:
        """A scalar duration in seconds; interval units use query-time step()."""
        return cls._apply("duration_literal", value)

    @classmethod
    def from_numeric_literal(cls, value: str) -> QueryBuilder:
        """Normalize a numeric value, including MetricsQL SI/binary suffixes."""
        return cls._apply("numeric_literal", value)

    @classmethod
    def _coerce(cls, value):
        if isinstance(value, Expression):
            return value
        return (
            cls.from_string(value) if isinstance(value, str) else cls.from_scalar(value)
        )

    @classmethod
    def function(cls, name: str, *args) -> QueryBuilder:
        """Call a function from the Rust signature catalog; strings are literals."""
        return cls._apply("call", name, children=tuple(cls._coerce(x) for x in args))

    def _unary(self, op, a="", b=""):
        return self._apply(op, a, b, (self,))

    def build(self, mode: Union[QueryMode, str] = QueryMode.METRICSQL, *,
              max_output_bytes=None, max_expanded_nodes=None, experimental_functions=False, features=()) -> str:
        """Render with native defaults of 1 MiB and 100,000 expanded nodes.

        Positive integer budgets override those defaults for this call only.
        Shared subexpressions count each time they appear in the output.
        experimental_functions also requires the corresponding Prometheus server flag.
        """
        if self._handle is None:
            raise ValueError("start with from_metric() or from_scalar() before build()")
        from .. import _native

        selected = QueryMode(mode)
        return _native.build(self._handle, 0 if selected == QueryMode.PROMQL else 1,
                             max_output_bytes, max_expanded_nodes, experimental_functions, features)

    def __str__(self):
        return self.build()

    def __bool__(self):
        raise TypeError(
            "query expressions have no Python truth value; use and_()/or_()"
        )

    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self
