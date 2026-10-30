"""Traversal and occurrence edits of the immutable native expression graph."""
from __future__ import annotations

from typing import Iterable, Literal, Optional, Tuple, TYPE_CHECKING

from ._types import BuildMode
from .capabilities import QueryMode

if TYPE_CHECKING:
    from .query_builder import QueryBuilder

ValueType = Literal["scalar", "string", "instant", "range", "tuple"]


class EditingMixin:
    __slots__ = ()

    def _editing_handle(self):
        if self._handle is None:
            raise ValueError("start with parse() or a from_* factory before AST editing")
        return self._handle

    def node_kind(self) -> str:
        """Native node category, e.g. selector, function, aggregate, binary or number."""
        from .. import _native_editing
        return _native_editing.node_info(self._editing_handle(), 0)

    def value_type(self) -> ValueType:
        """Native value category: scalar, string, instant, range or tuple."""
        from .. import _native_editing
        return _native_editing.node_info(self._editing_handle(), 1)

    def children(self) -> Tuple[QueryBuilder, ...]:
        """Ordered owning handles sharing direct children; selectors/literals are leaves.

        Labels and literal durations are metadata, not children. WITH children are
        binding values in declaration order followed by the body. No subtree copy.
        """
        from .. import _native_editing
        return _native_editing.children(self._editing_handle(), self._from_handle)

    def at_path(self, path: Iterable[int]) -> QueryBuilder:
        """Select by zero-based child indexes; empty path shares this root.

        Paths contain at most 1024 unsigned size_t integers. Negative indexes,
        booleans, non-integers and missing children are rejected.
        """
        from .. import _native_editing
        return self._from_handle(_native_editing.at_path(self._editing_handle(), path))

    def shares_node(self, other: QueryBuilder) -> bool:
        """Test native node identity, not semantic equality or Python object identity."""
        from .query_builder import QueryBuilder
        if not isinstance(other, QueryBuilder):
            raise TypeError("other must be a QueryBuilder expression")
        from .. import _native_editing
        return _native_editing.shares_node(self._editing_handle(), other._editing_handle())

    def replace_at(
        self, path: Iterable[int], replacement: QueryBuilder,
        mode: BuildMode = QueryMode.METRICSQL, *,
        max_output_bytes: Optional[int] = None, max_expanded_nodes: Optional[int] = None,
        experimental_functions: bool = False, features: Iterable[str] = (),
    ) -> QueryBuilder:
        """Replace one occurrence and validate the new root; neither input is mutated.

        Rebuild only ancestors and share unaffected nodes. A non-root replacement
        must preserve value_type(); an empty path replaces the whole root. Same-node
        replacement keeps native root identity but still validates dialect, flags,
        scopes and build budgets. Defaults match build(), including MetricsQL mode.
        """
        from .query_builder import QueryBuilder
        if not isinstance(replacement, QueryBuilder):
            raise TypeError("replacement must be a QueryBuilder expression")
        from .. import _native_editing
        selected = QueryMode(mode)
        handle = _native_editing.replace_at(
            self._editing_handle(), path, replacement._editing_handle(),
            0 if selected == QueryMode.PROMQL else 1, max_output_bytes,
            max_expanded_nodes, experimental_functions, features,
        )
        return self._from_handle(handle)
