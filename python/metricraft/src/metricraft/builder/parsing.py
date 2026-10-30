"""Explicit query-text parsing; existing string arguments remain literal data."""
from __future__ import annotations

from typing import Iterable, Literal, Optional, Tuple, TYPE_CHECKING

from ._types import BuildMode
from .capabilities import QueryMode

if TYPE_CHECKING:
    from .query_builder import QueryBuilder

ParseErrorKind = Literal["syntax", "validation", "dialect", "unsupported", "limit", "other"]


class ParseError(ValueError):
    """Native parse failure with an end-exclusive UTF-8 byte range, not character indexes."""

    kind: ParseErrorKind
    start: int
    end: int

    def __init__(self, message: str, kind: ParseErrorKind, start: int, end: int) -> None:
        super().__init__(message)
        self.kind = kind
        self.start = start
        self.end = end

    def __reduce__(self) -> Tuple[object, ...]:
        return type(self), (str(self), self.kind, self.start, self.end), self.__dict__


class ParsingMixin:
    __slots__ = ()

    @classmethod
    def parse(
        cls, source: str, mode: BuildMode = QueryMode.PROMQL, *,
        max_input_bytes: Optional[int] = None, max_tokens: Optional[int] = None,
        max_depth: Optional[int] = None, max_work: Optional[int] = None,
        max_output_bytes: Optional[int] = None, max_expanded_nodes: Optional[int] = None,
        experimental_functions: bool = False, features: Iterable[str] = (),
    ) -> QueryBuilder:
        """Parse supported PromQL into an immutable native expression.

        MetricsQL parsing raises ParseError(kind="unsupported"). Comments and
        formatting are discarded. No raw-expression fallback or evaluation occurs.
        Positive budgets override native defaults: 1 MiB input/output, 100,000
        tokens/expanded nodes, depth 64 (maximum 128), and 1,000,000 work units.
        Features require explicit opt-in, just as with build(). The expression
        stores no default dialect: use build("promql") for PromQL output.
        """
        from .. import _native_parsing

        selected = QueryMode(mode)
        handle = _native_parsing.parse(
            source, 0 if selected == QueryMode.PROMQL else 1,
            max_input_bytes, max_tokens, max_depth, max_work,
            max_output_bytes, max_expanded_nodes, experimental_functions, features,
        )
        return cls._from_handle(handle)
