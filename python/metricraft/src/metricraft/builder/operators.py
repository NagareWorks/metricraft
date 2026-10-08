"""Arithmetic, comparison, set operations and vector matching."""
from __future__ import annotations

from ._expression import Expression
from .capabilities import vm_only, prom_only


class OperatorMixin:
    """Arithmetic, comparison, set operations and vector matching."""

    __slots__ = ()

    def _binary(self, op, other):
        if isinstance(other, Expression):
            rhs = other
        elif op == "+" and isinstance(other, str):
            rhs = self.from_string(other)
        else:
            rhs = self.from_scalar(other)
        return self._apply(op, children=(self, rhs))

    @vm_only
    def eq_any(self, *values):
        return self.eq(self.from_tuple(*values))

    @vm_only
    def ne_all(self, *values):
        return self.ne(self.from_tuple(*values))

    @vm_only
    def group_left_all(self, *, prefix=""):
        return self._unary("group_left_all", prefix)

    @vm_only
    def group_right_all(self, *, prefix=""):
        return self._unary("group_right_all", prefix)

    @prom_only
    def trim_upper(self, threshold):
        return self._binary("</", threshold)

    @prom_only
    def trim_lower(self, threshold):
        return self._binary(">/", threshold)

    @prom_only
    def fill(self, value):
        return self._apply("fill", children=(self, self.from_scalar(value)))

    @prom_only
    def fill_left(self, value):
        return self._apply("fill_left", children=(self, self.from_scalar(value)))

    @prom_only
    def fill_right(self, value):
        return self._apply("fill_right", children=(self, self.from_scalar(value)))

    def __add__(self, other):
        return self._binary("+", other)

    def __sub__(self, other):
        return self._binary("-", other)

    def __mul__(self, other):
        return self._binary("*", other)

    def __truediv__(self, other):
        return self._binary("/", other)

    def __mod__(self, other):
        return self._binary("%", other)

    def __pow__(self, other):
        return self._binary("^", other)

    def __radd__(self, other):
        return self._coerce(other)._binary("+", self)

    def __rsub__(self, other):
        return self.from_scalar(other)._binary("-", self)

    def __rmul__(self, other):
        return self.from_scalar(other)._binary("*", self)

    def __rtruediv__(self, other):
        return self.from_scalar(other)._binary("/", self)

    def __neg__(self):
        return self._unary("negate")

    def __pos__(self):
        return self._unary("positive")

    positive = __pos__

    negative = __neg__

    def parenthesize(self):
        return self._unary("parenthesize")

    add = __add__

    sub = __sub__

    mul = __mul__

    div = __truediv__

    mod = __mod__

    pow = __pow__

    def eq(self, other):
        return self._binary("==", other)

    def ne(self, other):
        return self._binary("!=", other)

    def gt(self, other):
        return self._binary(">", other)

    def ge(self, other):
        return self._binary(">=", other)

    def lt(self, other):
        return self._binary("<", other)

    def le(self, other):
        return self._binary("<=", other)

    def between(self, minimum, maximum):
        """Keep instant-vector samples within inclusive literal numeric bounds."""
        return self._apply("between", children=(self, self.from_scalar(minimum), self.from_scalar(maximum)))

    def and_(self, other):
        return self._binary("and", other)

    def or_(self, other):
        return self._binary("or", other)

    def unless(self, other):
        return self._binary("unless", other)

    __gt__ = gt

    __ge__ = ge

    __lt__ = lt

    __le__ = le

    __eq__ = eq

    __ne__ = ne

    __and__ = and_

    __or__ = or_

    def atan2(self, other):
        return self._binary("atan2", other)

    def bool(self):
        return self._unary("bool")

    def _modifier(self, name, labels):
        return self._apply(
            name, children=(self,) + tuple(self.from_string(x) for x in labels)
        )

    def on(self, *labels):
        return self._modifier("on", labels)

    def ignoring(self, *labels):
        return self._modifier("ignoring", labels)

    def group_left(self, *labels):
        return self._modifier("group_left", labels)

    def group_right(self, *labels):
        return self._modifier("group_right", labels)

    @vm_only
    def if_(self, other):
        return self._binary("if", other)

    @vm_only
    def ifnot(self, other):
        return self._binary("ifnot", other)

    @vm_only
    def default(self, other):
        return self._binary("default", other)

    @vm_only
    def union(self, *others):
        return self.function("union", self, *others)
