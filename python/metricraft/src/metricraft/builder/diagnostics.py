"""Read-only native validation, graph inspection and source positions."""
from __future__ import annotations

from .capabilities import QueryMode


class DiagnosticMixin:
    """Read-only native validation, graph inspection and source positions."""

    __slots__ = ()

    def validate(self, standard=None, strict=True, **build_options):
        """Return an empty string or native validation error; never bypass validation."""
        if strict is not True:
            raise ValueError("validation is always enabled; strict=False is not supported")
        if self._handle is None:
            raise ValueError("start with a from_* factory before validate()")
        mode = QueryMode.METRICSQL if standard is None else QueryMode(standard.lower())
        try:
            self.build(mode, **build_options)
        except ValueError as exc:
            return str(exc)
        return ""

    def _inspect(self, kind, *, mode=QueryMode.METRICSQL, max_output_bytes=None,
                 max_items=None, experimental_functions=False, features=()):
        if self._handle is None:
            raise ValueError("start with a from_* factory before diagnostics")
        from .. import _native

        selected = QueryMode(mode)
        return _native.inspect(self._handle, kind, 0 if selected == QueryMode.PROMQL else 1,
                               max_output_bytes, max_items, experimental_functions, features)

    def to_debug_json(self, *, max_output_bytes=None, max_items=None):
        """Bounded JSON graph; shared nodes and matcher links are emitted once."""
        return self._inspect(0, max_output_bytes=max_output_bytes, max_items=max_items)

    debug = to_debug_json

    def analyze(self, *, max_output_bytes=None, max_items=None):
        """Native structural summary and heuristics, counting unique shared nodes."""
        import json

        return json.loads(self._inspect(1, max_output_bytes=max_output_bytes, max_items=max_items))

    def debug_positions(self, *, mode=QueryMode.METRICSQL, max_output_bytes=None,
                        max_items=None, experimental_functions=False, features=()):
        """JSON source and UTF-8 byte spans for rendered expression occurrences."""
        return self._inspect(2, mode=mode, max_output_bytes=max_output_bytes,
                             max_items=max_items, experimental_functions=experimental_functions, features=features)

    def visualize_positions(self, source_code, **options):
        """Return source/span JSON after verifying it describes this exact source."""
        import json

        if not isinstance(source_code, str):
            raise TypeError("source_code must be a string")
        result = self.debug_positions(**options)
        if json.loads(result)["source"] != source_code:
            raise ValueError("source_code must equal this expression's build output")
        return result
