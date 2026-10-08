"""Time range operations mixin for QueryBuilder."""

from datetime import datetime
from typing import Union, TYPE_CHECKING

from metricraft._legacy.tree import OffsetExpr, AtExpr, DurationLiteral

from metricraft._legacy.contracts import TimeRangeMixinBase

if TYPE_CHECKING:
    from metricraft._legacy.builder.impl.base import MetricsBuilder


class TimeRangeMixin(TimeRangeMixinBase):
    """
    Mixin providing time range operations for QueryBuilder.

    This mixin handles offset and @ modifiers for time-based operations.
    """

    def offset(self: 'MetricsBuilder', duration: str) -> 'MetricsBuilder':
        """Apply offset modifier: evaluate in the past by `duration` (e.g., "5m").

        Returns a new builder of the same type with the offset applied.
        """
        if self._ast_node is None:
            raise ValueError(
                "Cannot apply offset without a base expression. Use a from_* method first.")

        offset_expr = OffsetExpr(self._ast_node, DurationLiteral(duration))
        return self._create_new_builder(offset_expr, self._sign_state)

    def at(self: 'MetricsBuilder', timestamp: Union[str, datetime, int, float]) -> 'MetricsBuilder':
        """Apply @ modifier: evaluate at an absolute time point.

        Args:
            timestamp: One of
                - Unix timestamp (int|float), in seconds; milliseconds auto-detected
                - ISO datetime string (e.g., "2021-01-01T00:00:00Z")
                - datetime object
                - Special identifiers: "start()", "end()"

        Returns:
            MetricsBuilder: New builder of the same type with @ applied.

        Raises:
            TypeError: For unsupported timestamp types.
            ValueError: If called without base expression.
        """
        if self._ast_node is None:
            raise ValueError(
                "Cannot apply @ modifier without a base expression. Use a from_* method first.")

        # Handle different timestamp types
        if isinstance(timestamp, datetime):
            # Convert datetime to Unix timestamp (seconds)
            timestamp_value = timestamp.timestamp()
        elif isinstance(timestamp, str):
            # Check if it's a special function or try to parse as ISO format
            if timestamp in ("start()", "end()"):
                timestamp_value = timestamp
            else:
                try:
                    # Try to parse as ISO format
                    dt = datetime.fromisoformat(
                        timestamp.replace('Z', '+00:00'))
                    timestamp_value = dt.timestamp()
                except ValueError:
                    # If parsing fails, treat as raw string (could be a
                    # function call)
                    timestamp_value = timestamp
        elif isinstance(timestamp, (int, float)):
            # Handle Unix timestamps
            if timestamp > 1e10:  # Likely milliseconds
                timestamp_value = timestamp / 1000.0  # Convert to seconds
            else:
                timestamp_value = float(timestamp)  # Already in seconds
        else:
            raise TypeError(f"Unsupported timestamp type: {type(timestamp)}")

        at_expr = AtExpr(self._ast_node, timestamp_value)
        return self._create_new_builder(at_expr, self._sign_state)
