"""Metrics family builder state skeletons for Core.

These state-specific bases define the fluent API stages for metrics builders.
Provider implementations should inherit from these and return the matching
Base types to maintain chaining and strong type hints.
"""

from typing import Any, Optional
from metricraft._legacy.families.metrics.base import MetricsBuilderBase


class InstantVectorBuilderBase(MetricsBuilderBase):
    def metric(self, name: str) -> 'InstantVectorBuilderBase':
        """Select metric by name and return an instant-vector builder."""
        raise NotImplementedError
    def where(self, label_name: str, operator: str, value: Optional[str]) -> 'InstantVectorBuilderBase':
        """Filter by label using explicit operator (e.g., ==, !=, =~, !~)."""
        raise NotImplementedError
    def where_eq(self, label_name: str, value: Optional[str]) -> 'InstantVectorBuilderBase':
        """Filter where label equals value."""
        raise NotImplementedError
    def where_ne(self, label_name: str, value: Optional[str]) -> 'InstantVectorBuilderBase':
        """Filter where label not equals value."""
        raise NotImplementedError
    def where_regex(self, label_name: str, pattern: Optional[str]) -> 'InstantVectorBuilderBase':
        """Filter where label matches regex pattern."""
        raise NotImplementedError
    def where_not_regex(self, label_name: str, pattern: Optional[str]) -> 'InstantVectorBuilderBase':
        """Filter where label does not match regex pattern."""
        raise NotImplementedError


class RangeVectorBuilderBase(MetricsBuilderBase):
    def range(self, duration: str) -> 'RangeVectorBuilderBase':
        """Attach a range selector to the underlying expression."""
        raise NotImplementedError


class ProcessedVectorBuilderBase(MetricsBuilderBase):
    def by(self, *labels: str) -> 'ProcessedVectorBuilderBase':
        """Aggregation modifier: group by given labels."""
        raise NotImplementedError
    def without(self, *labels: str) -> 'ProcessedVectorBuilderBase':
        """Aggregation modifier: group without given labels."""
        raise NotImplementedError
    def on(self, *labels: str) -> 'ProcessedVectorBuilderBase':
        """Binary op modifier: match only on given labels."""
        raise NotImplementedError
    def ignoring(self, *labels: str) -> 'ProcessedVectorBuilderBase':
        """Binary op modifier: ignore given labels during matching."""
        raise NotImplementedError
    def group_left(self, *labels: str) -> 'ProcessedVectorBuilderBase':
        """Binary op modifier: allow many-to-one on LHS with labels."""
        raise NotImplementedError
    def group_right(self, *labels: str) -> 'ProcessedVectorBuilderBase':
        """Binary op modifier: allow many-to-one on RHS with labels."""
        raise NotImplementedError


class ScalarBuilderBase(MetricsBuilderBase):
    def value(self, v: Any) -> 'ScalarBuilderBase':
        """Create/override scalar value for this builder context."""
        raise NotImplementedError
