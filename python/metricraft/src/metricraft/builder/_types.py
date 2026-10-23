"""Shared Python input types; expression semantics are validated by Rust."""
from typing import TYPE_CHECKING, Literal, Union

from .capabilities import QueryMode

if TYPE_CHECKING:
    from .query_builder import QueryBuilder

Number = Union[int, float]
ScalarInput = Union[Number, "QueryBuilder"]
StringInput = Union[str, "QueryBuilder"]
QueryInput = Union[Number, str, "QueryBuilder"]
Window = Union[str, "QueryBuilder"]
BuildMode = Union[QueryMode, Literal["promql", "metricsql"]]
Matcher = Literal["=", "!=", "=~", "!~"]
ReferenceKind = Literal["instant", "range", "scalar", "string"]
