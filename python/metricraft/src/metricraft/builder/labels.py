"""Label transformations; every operation returns a new shared Rust expression."""
from __future__ import annotations

from typing import TYPE_CHECKING, Tuple

from .capabilities import vm_only

if TYPE_CHECKING:
    from .query_builder import QueryBuilder


def _flatten_pairs(pairs):
    for pair in pairs:
        if not isinstance(pair, tuple) or len(pair) != 2:
            raise TypeError("each mapping must be a (source, destination) tuple")
        if not all(isinstance(value, str) for value in pair):
            raise TypeError("mapping sources and destinations must be strings")
        yield from pair


class LabelMixin:
    """Stateless helpers for labels on query results, including aggregations."""

    __slots__ = ()

    def label_replace(self, destination, replacement, source, regex):
        return self.function(
            "label_replace", self, destination, replacement, source, regex
        )

    def label_join(self, destination, separator, *sources):
        return self.function("label_join", self, destination, separator, *sources)

    @vm_only
    def label_set(self, **labels):
        return self.function(
            "label_set", self, *(part for item in labels.items() for part in item)
        )

    @vm_only
    def label_del(self, *labels):
        return self.function("label_del", self, *labels)

    @vm_only
    def label_keep(self, *labels):
        return self.function("label_keep", self, *labels)

    @vm_only
    def label_copy(self, *pairs: Tuple[str, str]) -> QueryBuilder:
        """Copy (source, destination) label pairs in order; missing sources are skipped."""
        return self.function("label_copy", self, *_flatten_pairs(pairs))

    @vm_only
    def label_move(self, *pairs: Tuple[str, str]) -> QueryBuilder:
        """Move (source, destination) label pairs in order, removing source labels."""
        return self.function("label_move", self, *_flatten_pairs(pairs))

    @vm_only
    def label_map(self, label: str, *pairs: Tuple[str, str]) -> QueryBuilder:
        """Map exact label values with (source value, destination value) pairs."""
        return self.function("label_map", self, label, *_flatten_pairs(pairs))

    @vm_only
    def label_lowercase(self, *labels: str) -> QueryBuilder:
        return self.function("label_lowercase", self, *labels)

    @vm_only
    def label_uppercase(self, *labels: str) -> QueryBuilder:
        return self.function("label_uppercase", self, *labels)

    @vm_only
    def label_match(self, label: str, regex: str) -> QueryBuilder:
        """Keep series whose label value matches the anchored backend regex."""
        return self.function("label_match", self, label, regex)

    @vm_only
    def label_mismatch(self, label: str, regex: str) -> QueryBuilder:
        return self.function("label_mismatch", self, label, regex)

    @vm_only
    def label_transform(self, label: str, regex: str, replacement: str) -> QueryBuilder:
        """Replace every regex match within a label value on the backend."""
        return self.function("label_transform", self, label, regex, replacement)

    @vm_only
    def label_value(self, label: str) -> QueryBuilder:
        """Use a numeric label as the sample value; invalid values yield no samples."""
        return self.function("label_value", self, label)

    @vm_only
    def labels_equal(self, first: str, second: str, *others: str) -> QueryBuilder:
        return self.function("labels_equal", self, first, second, *others)

    @vm_only
    def label_graphite_group(self, *groups: int) -> QueryBuilder:
        """Select zero-based dot-separated metric-name components."""
        return self.function("label_graphite_group", self, *groups)

    @vm_only
    def drop_common_labels(self, *others: QueryBuilder) -> QueryBuilder:
        return self.function("drop_common_labels", self, *others)

    @vm_only
    def alias(self, name):
        return self.function("alias", self, name)

    @vm_only
    def keep_metric_names(self):
        return self._unary("keep_metric_names")
