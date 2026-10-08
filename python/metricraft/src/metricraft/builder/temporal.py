"""Query-time factories, ranges and time modifiers."""
from __future__ import annotations

from typing import Union
from datetime import datetime
from .capabilities import vm_only, prom_experimental, prom_only
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .query_builder import QueryBuilder


class TemporalMixin:
    """Query-time factories, ranges and time modifiers."""

    __slots__ = ()

    @classmethod
    def time(cls):
        return cls.function("time")

    from_time = time

    @classmethod
    @vm_only
    def now(cls):
        return cls.function("now")

    from_now = now

    @classmethod
    @prom_experimental
    def start(cls):
        """Query start; PromQL requires experimental-functions opt-in."""
        return cls.function("start")

    from_start = start

    @classmethod
    @prom_experimental
    def end(cls):
        return cls.function("end")

    from_end = end

    @classmethod
    @prom_experimental
    def step(cls):
        return cls.function("step")

    @staticmethod
    def _window(window, duration, default=None):
        if window is not None and duration is not None:
            raise TypeError("pass either window or duration, not both")
        return duration if duration is not None else window if window is not None else default

    def range(self, window=None, *, duration=None) -> QueryBuilder:
        window = self._window(window, duration, "5m")
        from ._expression import Expression
        return self._apply("range_expr", children=(self, window)) if isinstance(window, Expression) else self._unary("range", window)

    def subquery(self, window=None, step=None, *, range_duration=None, resolution=None) -> QueryBuilder:
        window, step = self._window(window, range_duration), self._window(step, resolution, "")
        from ._expression import Expression
        if isinstance(window, Expression) or isinstance(step, Expression):
            window = window if isinstance(window, Expression) else self.from_duration(window)
            args = (self, window)
            if isinstance(step, Expression) or step != "":
                args += (step if isinstance(step, Expression) else self.from_duration(step),)
            return self._apply("subquery_expr", children=args)
        return self._unary("subquery", "" if window is None else window, step)

    def offset(self, duration: str) -> QueryBuilder:
        from ._expression import Expression
        if isinstance(duration, Expression):
            return self._apply("offset_expr", children=(self, duration))
        return self._unary("offset", duration)

    def at(self, timestamp: Union[int, float, str]) -> QueryBuilder:
        from ._expression import Expression
        if isinstance(timestamp, Expression):
            return self._apply("at_expr", children=(self, timestamp))
        if isinstance(timestamp, bool):
            raise TypeError("timestamp must be a number or start/end")
        if isinstance(timestamp, str):
            if timestamp in ("start()", "end()"):
                timestamp = timestamp[:-2]
            elif timestamp not in ("start", "end"):
                try:
                    timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                except ValueError as exc:
                    raise ValueError("string timestamp must be start/end or an ISO timestamp with timezone") from exc
        if isinstance(timestamp, datetime):
            if timestamp.tzinfo is None or timestamp.utcoffset() is None:
                raise ValueError("timestamp must have an explicit timezone")
            timestamp = timestamp.timestamp()
        if not isinstance(timestamp, (int, float, str)):
            raise TypeError("timestamp must be a number or start/end")
        return self._unary("at", str(timestamp))

    @prom_only
    def anchored(self):
        return self._unary("anchored")

    @prom_only
    def smoothed(self):
        return self._unary("smoothed")


    @classmethod
    @prom_only
    @prom_experimental
    def query_range(cls):
        return cls.function("range")

    @prom_only
    @prom_experimental
    def start_timestamp(self):
        return self.function("start_timestamp", self)
