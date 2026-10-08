"""
Modifier enumerations for PromQL/MetricsQL.

This module contains enumerations for various modifier types used in
binary operations and grouping operations.
"""

from metricraft._legacy.enums.base import ModifierEnum


class GroupModifierType(ModifierEnum):
    """Group modifier types for aggregations."""

    BY = "by"
    WITHOUT = "without"

    @property
    def is_inclusive(self) -> bool:
        """Check if this modifier includes specified labels (True) or excludes them (False)."""
        return self == self.BY


class BinaryModifierType(ModifierEnum):
    """Binary modifier types for vector matching."""

    # Matching modifiers
    ON = "on"
    IGNORING = "ignoring"

    # Group modifiers
    GROUP_LEFT = "group_left"
    GROUP_RIGHT = "group_right"

    @property
    def is_matching_modifier(self) -> bool:
        """Check if this is a matching modifier (on/ignoring)."""
        return self in {self.ON, self.IGNORING}

    @property
    def is_group_modifier(self) -> bool:
        """Check if this is a group modifier (group_left/group_right)."""
        return self in {self.GROUP_LEFT, self.GROUP_RIGHT}

    @property
    def is_inclusive(self) -> bool:
        """Check if this modifier includes specified labels (True) or excludes them (False)."""
        return self == self.ON
