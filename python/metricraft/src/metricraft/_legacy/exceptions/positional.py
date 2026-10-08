"""
VM-specific positional error implementation.

This module provides VMPositionalError that extends the framework PositionalError
with MetricsQL-specific position calculation logic.
"""

from __future__ import annotations

import re
from typing import Optional
from metricraft._legacy.exceptions.builder import PositionalError
from metricraft._legacy.tree.nodes.types import NodeType
from metricraft._legacy.visitor import get_query_visitor, PositionTrackingVisitor


class VMPositionalError(PositionalError):
    """
    VM-specific positional error with MetricsQL AST position tracking.
    
    This class extends the framework PositionalError to provide actual
    implementation of position calculation methods using VM-specific AST nodes.
    """

    def calculate_absolute_position(self) -> Optional[tuple[int, int]]:
        """
        Calculate absolute position in the generated query string.
        
        For validation errors, we need to calculate where the error node would
        appear if it were added to the query. This handles the special case
        where the error node is a temporary validation node.
        
        Returns:
            Tuple of (start, end) absolute positions, or None if calculation fails
        """
        if not self.ast_node or not self.root_node:
            return None
            
        # Position can be None, we'll calculate it dynamically
        try:
            if (self.ast_node.node_type == NodeType.STRING_LITERAL and self.root_node.node_type == NodeType.METRIC_SELECTOR):
                # This is likely a label value validation error
                # We need to calculate where this value would appear in a label matcher
                return self._calculate_label_value_position()
            else:
                # For other cases, use the general position tracking
                visitor = PositionTrackingVisitor()
                position_map = visitor.build_position_map(self.root_node)

                node_id = id(self.ast_node)
                if node_id in position_map:
                    start, end = position_map[node_id]
                    return (start, end)

            return None
        except Exception:
            return None

    def _calculate_label_value_position(self) -> Optional[tuple[int, int]]:
        """
        Calculate position for a label value in validation context.
        
        This handles the special case where we're validating a label value
        that would be added to the query.
        """
        try:
            if not self.root_node or self.root_node.node_type is not NodeType.METRIC_SELECTOR:
                return None

            # Start with metric name
            query_parts = [self.root_node.metric_name]
            current_pos = len(self.root_node.metric_name)

            # If there are existing matchers or we're adding one, we need braces
            query_parts.append("{")
            current_pos += 1

            # Add existing matchers
            if self.root_node.label_matchers:
                for i, matcher in enumerate(self.root_node.label_matchers):
                    if i > 0:
                        query_parts.append(",")
                        current_pos += 1

                    matcher_str = f'{matcher.name}{matcher.op.value}"{matcher.value}"'
                    query_parts.append(matcher_str)
                    current_pos += len(matcher_str)

            # Extract label name from error message to find the correct matcher
            label_match = re.search(r"label value for '([^']+)'", self.message)
            if label_match:
                target_label = label_match.group(1)
                
                # Reconstruct query to find exact position
                visitor = get_query_visitor()
                full_query = visitor.visit(self.root_node)
                
                # Find the target pattern: label_name="value"
                pattern = f'{target_label}="'
                pattern_start = full_query.find(pattern)
                if pattern_start >= 0:
                    value_start = pattern_start + len(pattern)  # Position after opening quote
                    
                    # Find the closing quote
                    value_end_quote = full_query.find('"', value_start)
                    if value_end_quote >= 0:
                        value_end = value_end_quote
                        return (value_start, value_end)

            # Fallback: use the StringLiteral node's reported position
            if hasattr(self.ast_node, 'pos') and self.ast_node.pos:
                return (self.ast_node.pos.offset, self.ast_node.pos.offset + self.ast_node.pos.length)
                
            # Final fallback
            return (0, 21)

        except Exception:
            return None
