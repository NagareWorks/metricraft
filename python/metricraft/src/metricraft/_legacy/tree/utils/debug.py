"""
AST debugging and visualization utilities with position awareness.

This module provides tools for debugging and visualizing AST trees with
enhanced position information to help developers understand query structure
and locate issues.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import json

from metricraft._legacy.ast import Position
from metricraft._legacy.tree.nodes.base import VMASTNode
from metricraft._legacy.tree.nodes.types import NodeType


@dataclass
class DebugInfo:
	"""Debug information for an AST node."""
	node_type: str
	position: Optional[Position]
	properties: Dict[str, Any]
	children: List['DebugInfo']

	def to_dict(self) -> Dict[str, Any]:
		"""Convert debug info to dictionary format."""
		return {
			'node_type': self.node_type,
			'position': self.position.__dict__ if self.position else None,
			'properties': self.properties,
			'children': [child.to_dict() for child in self.children]
		}


class ASTDebugger:
	"""Enhanced AST debugger with position information."""

	def __init__(self, show_positions: bool = True, show_types: bool = True):
		"""Initialize the debugger."""
		self.show_positions = show_positions
		self.show_types = show_types

	def debug_tree(self, node: VMASTNode, indent: int = 0) -> str:
		"""Create a text-based debug representation of the AST tree."""
		lines = []
		prefix = "  " * indent

		# Node header with type and position
		header_parts = [self._get_node_name(node)]
		if self.show_types:
			header_parts.append(f"({type(node).__name__})")
		if self.show_positions and hasattr(node, 'pos') and node.pos:
			pos = node.pos
			header_parts.append(f"@{pos.offset}+{pos.length}")
		lines.append(f"{prefix}{' '.join(header_parts)}")

		# Node properties
		properties = self._get_node_properties(node)
		for key, value in properties.items():
			lines.append(f"{prefix}  {key}: {value}")

		# Child nodes
		children = self._get_child_nodes(node)
		for child in children:
			lines.append(self.debug_tree(child, indent + 1))

		return '\n'.join(lines)

	def debug_positions(self, node: VMASTNode) -> str:
		"""Create a position-focused debug view of the AST."""
		positions = []
		self._collect_positions(node, positions)

		# Check if any positions have actual position information
		has_positions = any(position for _, position in positions)
		if not has_positions:
			return "No position information available"

		# Sort by position
		positions.sort(key=lambda x: (x[1].offset, x[1].index_in_parent) if x[1] else (0, 0))
		lines = ["Position Map:"]
		for node_info, position in positions:
			if position:
				pos_str = f"@{position.offset}+{position.length}"
				lines.append(f"  {pos_str}: {node_info}")
		return '\n'.join(lines)

	def debug_json(self, node: VMASTNode) -> str:
		"""Create a JSON representation of the AST with debug information."""
		debug_info = self._create_debug_info(node)
		return json.dumps(debug_info.to_dict(), indent=2, default=str)

	def visualize_positions(self, node: VMASTNode, source_code: Optional[str] = None) -> str:
		"""Create a visual representation of AST node positions in source code."""
		if not source_code:
			return self.debug_positions(node)

		positions = []
		self._collect_positions(node, positions)
		if not positions:
			return f"Source Code:\n{source_code}\n\nNo position information available"

		lines = ["Source Code with AST Node Positions:", "=" * 50]
		lines.append(f"Source: {source_code}")

		# Sort positions by offset for display
		sorted_positions = sorted(
			[(node_info, pos) for node_info, pos in positions if pos],
			key=lambda x: (x[1].offset, x[1].index_in_parent)
		)

		if sorted_positions:
			# Create a visual representation with markers
			marker_line = " " * (8 + len(source_code))  # Account for "Source: " prefix
			for node_info, pos in sorted_positions:
				start = min(pos.offset + 8, len(marker_line) - 1)  # +8 for "Source: " prefix
				end = min(pos.offset + pos.length + 8, len(marker_line))
				# Mark the position with carets
				for i in range(start, end):
					if i < len(marker_line):
						marker_line = marker_line[:i] + "^" + marker_line[i + 1:]
			lines.append(marker_line)

			lines.append("\nPosition Details:")
			# Show detailed position information
			for node_info, pos in sorted_positions:
				lines.append(f"  {node_info}: {pos}")

		return '\n'.join(lines)

	def _get_node_name(self, node: VMASTNode) -> str:
		"""Get a descriptive name for the node."""
		if not node:
			return "None"

		if node.node_type is NodeType.METRIC_SELECTOR:
			return f"Metric({node.metric_name or 'unnamed'})"
		elif node.node_type is NodeType.LABEL_MATCHER:
			return f"Label({node.name} {node.op.value} {node.value})"
		elif node.node_type is NodeType.BINARY_EXPR:
			return f"BinaryOp({node.operator.value})"
		elif node.node_type is NodeType.UNARY_EXPR:
			return f"UnaryOp({node.operator.value})"
		elif node.node_type is NodeType.FUNCTION_CALL:
			return f"Function({node.name})"
		elif node.node_type is NodeType.AGGREGATION_EXPR:
			return f"Aggregation({node.operator.value})"
		elif node.node_type is NodeType.NUMBER_LITERAL:
			return f"Number({node.value})"
		elif node.node_type is NodeType.STRING_LITERAL:
			return f"String({node.value})"
		elif node.node_type is NodeType.DURATION_LITERAL:
			return f"Duration({node.value})"
		elif node.node_type is NodeType.RANGE_EXPR:
			duration = node.range_duration.value if hasattr(node.range_duration, 'value') else str(node.range_duration)
			return f"Range([{duration}])"
		elif node.node_type is NodeType.PARENTHESIZED_EXPR:
			return "Parentheses"
		else:
			return type(node).__name__

	def _get_node_properties(self, node: VMASTNode) -> Dict[str, Any]:
		"""Extract relevant properties from the node."""
		properties: Dict[str, Any] = {}
		if hasattr(node, 'pos') and node.pos and self.show_positions:
			pos = node.pos
			properties['position'] = f"{pos.offset}+{pos.length}"
			if pos.length > 1:
				properties['length'] = pos.length
			if hasattr(pos, 'source_info') and pos.source_info:
				properties['source_info'] = pos.source_info

		if node.node_type is NodeType.METRIC_SELECTOR:
			if node.label_matchers:
				properties['label_count'] = len(node.label_matchers)
		elif node.node_type is NodeType.AGGREGATION_EXPR:
			if node.grouping:
				properties['grouping'] = f"{'without' if node.grouping.is_without else 'by'} {node.grouping.labels}"
		elif node.node_type is NodeType.BINARY_EXPR:
			if hasattr(node, 'matching') and node.matching:
				properties['matching'] = "with vector matching"
		return properties

	def _get_child_nodes(self, node: VMASTNode) -> List[VMASTNode]:
		"""Get child nodes for traversal."""
		children: List[VMASTNode] = []
		if node.node_type is NodeType.BINARY_EXPR:
			children.extend([node.left, node.right])
		elif node.node_type is NodeType.UNARY_EXPR:
			children.append(node.operand)
		elif node.node_type is NodeType.FUNCTION_CALL:
			children.extend(node.args)
		elif node.node_type is NodeType.AGGREGATION_EXPR:
			children.append(node.expr)
			if node.parameter:
				children.append(node.parameter)
		elif node.node_type is NodeType.PARENTHESIZED_EXPR:
			children.append(node.expr)
		elif node.node_type is NodeType.RANGE_EXPR:
			children.append(node.expr)
		elif node.node_type is NodeType.METRIC_SELECTOR:
			children.extend(node.label_matchers)
		return children

	def _collect_positions(self, node: VMASTNode, positions: List[tuple]) -> None:
		"""Recursively collect position information from the AST."""
		node_info = self._get_node_name(node)
		position = getattr(node, 'pos', None)
		positions.append((node_info, position))
		for child in self._get_child_nodes(node):
			self._collect_positions(child, positions)

	def _create_debug_info(self, node: VMASTNode) -> DebugInfo:
		"""Create debug information structure for the node."""
		node_type = type(node).__name__
		position = getattr(node, 'pos', None)
		properties = self._get_node_properties(node)
		children = [self._create_debug_info(child) for child in self._get_child_nodes(node)]
		return DebugInfo(node_type=node_type, position=position, properties=properties, children=children)


class QueryAnalyzer:
	"""Analyzer for query patterns and potential issues."""

	def analyze(self, node: VMASTNode) -> Dict[str, Any]:
		analysis = {
			'metrics': self._analyze_metrics(node),
			'complexity': self._analyze_complexity(node),
			'performance': self._analyze_performance(node),
			'patterns': self._analyze_patterns(node)
		}
		return analysis

	def _analyze_metrics(self, node: VMASTNode) -> Dict[str, Any]:
		metrics = set()
		labels = set()
		functions: List[str] = []
		self._collect_metrics_info(node, metrics, labels, functions)
		return {
			'unique_metrics': len(metrics),
			'metric_names': list(metrics),
			'unique_labels': len(labels),
			'label_names': list(labels),
			'function_count': len(functions),
			'function_types': list(set(functions))
		}

	def _analyze_complexity(self, node: VMASTNode) -> Dict[str, Any]:
		depth = self._calculate_depth(node)
		node_count = self._count_nodes(node)
		function_count = self._count_functions(node)
		complexity_score = (depth * 2) + (node_count * 0.5) + (function_count * 3)
		return {
			'depth': depth,
			'node_count': node_count,
			'function_count': function_count,
			'complexity_score': complexity_score,
			'complexity_level': self._classify_complexity(complexity_score)
		}

	def _analyze_performance(self, node: VMASTNode) -> Dict[str, Any]:
		issues: List[str] = []
		if self._has_regex_matchers(node):
			issues.append("Contains regex label matchers (potentially expensive)")
		if self._has_many_or_operations(node):
			issues.append("Contains many OR operations (may be inefficient)")
		if self._has_nested_aggregations(node):
			issues.append("Contains nested aggregations (may be expensive)")
		range_durations = self._collect_range_durations(node)
		if any(self._is_long_duration(duration) for duration in range_durations):
			issues.append("Contains long time ranges (may be expensive)")
		return {'potential_issues': issues, 'issue_count': len(issues), 'range_durations': range_durations}

	def _analyze_patterns(self, node: VMASTNode) -> Dict[str, Any]:
		patterns: List[str] = []
		if self._has_rate_pattern(node):
			patterns.append("Rate calculation pattern detected")
		if self._has_aggregation_pattern(node):
			patterns.append("Aggregation pattern detected")
		if self._has_comparison_pattern(node):
			patterns.append("Comparison/alerting pattern detected")
		if self._has_arithmetic_pattern(node):
			patterns.append("Arithmetic computation pattern detected")
		return {'detected_patterns': patterns, 'pattern_count': len(patterns)}

	def _collect_metrics_info(self, node: VMASTNode, metrics: set, labels: set, functions: list) -> None:
		if node.node_type is NodeType.METRIC_SELECTOR:
			if node.metric_name:
				metrics.add(node.metric_name)
			for matcher in node.label_matchers:
				labels.add(matcher.name)
		elif node.node_type is NodeType.FUNCTION_CALL:
			functions.append(node.name)
		elif node.node_type is NodeType.AGGREGATION_EXPR:
			functions.append(node.operator.value)

		# Recursively process children
		if node.node_type is NodeType.BINARY_EXPR:
			self._collect_metrics_info(node.left, metrics, labels, functions)
			self._collect_metrics_info(node.right, metrics, labels, functions)
		elif node.node_type is NodeType.UNARY_EXPR:
			self._collect_metrics_info(node.operand, metrics, labels, functions)
		elif node.node_type is NodeType.RANGE_EXPR:
			self._collect_metrics_info(node.expr, metrics, labels, functions)
		elif node.node_type is NodeType.FUNCTION_CALL:
			for arg in node.args:
				self._collect_metrics_info(arg, metrics, labels, functions)
		elif node.node_type is NodeType.AGGREGATION_EXPR:
			self._collect_metrics_info(node.expr, metrics, labels, functions)
			if node.parameter:
				self._collect_metrics_info(node.parameter, metrics, labels, functions)

	def _calculate_depth(self, node: VMASTNode, current_depth: int = 0) -> int:
		max_depth = current_depth
		if node.node_type is NodeType.BINARY_EXPR:
			left_depth = self._calculate_depth(node.left, current_depth + 1)
			right_depth = self._calculate_depth(node.right, current_depth + 1)
			max_depth = max(left_depth, right_depth)
		elif node.node_type is NodeType.UNARY_EXPR:
			max_depth = self._calculate_depth(node.operand, current_depth + 1)
		elif node.node_type is NodeType.RANGE_EXPR:
			max_depth = self._calculate_depth(node.expr, current_depth + 1)
		elif node.node_type is NodeType.FUNCTION_CALL:
			for arg in node.args:
				arg_depth = self._calculate_depth(arg, current_depth + 1)
				max_depth = max(max_depth, arg_depth)
		elif node.node_type is NodeType.AGGREGATION_EXPR:
			expr_depth = self._calculate_depth(node.expr, current_depth + 1)
			max_depth = expr_depth
			if node.parameter:
				param_depth = self._calculate_depth(node.parameter, current_depth + 1)
				max_depth = max(max_depth, param_depth)
		return max_depth

	def _count_nodes(self, node: VMASTNode) -> int:
		count = 1
		if node.node_type is NodeType.BINARY_EXPR:
			count += self._count_nodes(node.left)
			count += self._count_nodes(node.right)
		elif node.node_type is NodeType.UNARY_EXPR:
			count += self._count_nodes(node.operand)
		elif node.node_type is NodeType.FUNCTION_CALL:
			for arg in node.args:
				count += self._count_nodes(arg)
		elif node.node_type is NodeType.AGGREGATION_EXPR:
			count += self._count_nodes(node.expr)
			if node.parameter:
				count += self._count_nodes(node.parameter)
		elif node.node_type is NodeType.RANGE_EXPR:
			count += self._count_nodes(node.expr)
		return count

	def _count_functions(self, node: VMASTNode) -> int:
		count = 0
		if node.node_type is NodeType.FUNCTION_CALL or node.node_type is NodeType.AGGREGATION_EXPR:
			count = 1
		if node.node_type is NodeType.BINARY_EXPR:
			count += self._count_functions(node.left)
			count += self._count_functions(node.right)
		elif node.node_type is NodeType.UNARY_EXPR:
			count += self._count_functions(node.operand)
		elif node.node_type is NodeType.FUNCTION_CALL:
			for arg in node.args:
				count += self._count_functions(arg)
		elif node.node_type is NodeType.AGGREGATION_EXPR:
			count += self._count_functions(node.expr)
			if node.parameter:
				count += self._count_functions(node.parameter)
		return count

	def _classify_complexity(self, score: float) -> str:
		if score < 10:
			return "Low"
		elif score < 25:
			return "Medium"
		elif score < 50:
			return "High"
		else:
			return "Very High"

	def _has_regex_matchers(self, node: VMASTNode) -> bool:
		if node.node_type is NodeType.METRIC_SELECTOR:
			return any(matcher.op.value in ['=~', '!~'] for matcher in node.label_matchers)
		elif node.node_type is NodeType.BINARY_EXPR:
			return self._has_regex_matchers(node.left) or self._has_regex_matchers(node.right)
		elif node.node_type is NodeType.UNARY_EXPR:
			return self._has_regex_matchers(node.operand)
		elif node.node_type is NodeType.FUNCTION_CALL:
			return any(self._has_regex_matchers(arg) for arg in node.args)
		elif node.node_type is NodeType.AGGREGATION_EXPR:
			return self._has_regex_matchers(node.expr)
		return False

	def _has_many_or_operations(self, node: VMASTNode, count: int = 0) -> bool:
		if node.node_type is NodeType.BINARY_EXPR and node.operator.value == 'or':
			count += 1
			if count > 3:
				return True
		if node.node_type is NodeType.BINARY_EXPR:
			return (self._has_many_or_operations(node.left, count) or
					self._has_many_or_operations(node.right, count))
		elif node.node_type is NodeType.UNARY_EXPR:
			return self._has_many_or_operations(node.operand, count)
		elif node.node_type is NodeType.FUNCTION_CALL:
			return any(self._has_many_or_operations(arg, count) for arg in node.args)
		elif node.node_type is NodeType.AGGREGATION_EXPR:
			return self._has_many_or_operations(node.expr, count)
		return False

	def _has_nested_aggregations(self, node: VMASTNode, in_aggregation: bool = False) -> bool:
		if node.node_type is NodeType.AGGREGATION_EXPR:
			if in_aggregation:
				return True
			return self._has_nested_aggregations(node.expr, True)
		elif node.node_type is NodeType.BINARY_EXPR:
			return (self._has_nested_aggregations(node.left, in_aggregation) or
					self._has_nested_aggregations(node.right, in_aggregation))
		elif node.node_type is NodeType.UNARY_EXPR:
			return self._has_nested_aggregations(node.operand, in_aggregation)
		elif node.node_type is NodeType.FUNCTION_CALL:
			return any(self._has_nested_aggregations(arg, in_aggregation) for arg in node.args)
		return False

	def _collect_range_durations(self, node: VMASTNode) -> List[str]:
		durations: List[str] = []
		if node.node_type is NodeType.RANGE_EXPR:
			if hasattr(node.range_duration, 'value'):
				durations.append(node.range_duration.value)
			else:
				durations.append(str(node.range_duration))
		elif node.node_type is NodeType.BINARY_EXPR:
			durations.extend(self._collect_range_durations(node.left))
			durations.extend(self._collect_range_durations(node.right))
		elif node.node_type is NodeType.UNARY_EXPR:
			durations.extend(self._collect_range_durations(node.expr))
		elif node.node_type is NodeType.FUNCTION_CALL:
			for arg in node.args:
				durations.extend(self._collect_range_durations(arg))
		elif node.node_type is NodeType.AGGREGATION_EXPR:
			durations.extend(self._collect_range_durations(node.expr))
		return durations

	def _is_long_duration(self, duration: str) -> bool:
		# Simple heuristic - anything over 1 day
		return any(duration.endswith(unit) for unit in ['d', 'w']) or \
			(duration.endswith('h') and any(duration.startswith(str(i)) for i in range(24, 1000)))

	def _has_rate_pattern(self, node: VMASTNode) -> bool:
		if node.node_type is NodeType.FUNCTION_CALL and node.name in ['rate', 'irate', 'increase']:
			return True
		elif node.node_type is NodeType.BINARY_EXPR:
			return self._has_rate_pattern(node.left) or self._has_rate_pattern(node.right)
		elif node.node_type is NodeType.UNARY_EXPR:
			return self._has_rate_pattern(node.operand)
		elif node.node_type is NodeType.AGGREGATION_EXPR:
			return self._has_rate_pattern(node.expr)
		return False

	def _has_aggregation_pattern(self, node: VMASTNode) -> bool:
		return node.node_type is NodeType.AGGREGATION_EXPR

	def _has_comparison_pattern(self, node: VMASTNode) -> bool:
		if node.node_type is NodeType.BINARY_EXPR and node.operator.value in ['>', '<', '>=', '<=', '==', '!=']:
			return True
		elif node.node_type is NodeType.BINARY_EXPR:
			return self._has_comparison_pattern(node.left) or self._has_comparison_pattern(node.right)
		elif node.node_type is NodeType.UNARY_EXPR:
			return self._has_comparison_pattern(node.operand)
		return False

	def _has_arithmetic_pattern(self, node: VMASTNode) -> bool:
		if node.node_type is NodeType.BINARY_EXPR and node.operator.value in ['+', '-', '*', '/', '%', '^']:
			return True
		elif node.node_type is NodeType.BINARY_EXPR:
			return self._has_arithmetic_pattern(node.left) or self._has_arithmetic_pattern(node.right)
		elif node.node_type is NodeType.UNARY_EXPR:
			return self._has_arithmetic_pattern(node.operand)
		return False


def debug_ast(node: VMASTNode, show_positions: bool = True) -> str:
	"""Quick debug function for AST nodes."""
	debugger = ASTDebugger(show_positions=show_positions)
	return debugger.debug_tree(node)


def analyze_query(node: VMASTNode) -> Dict[str, Any]:
	"""Quick analysis function for queries."""
	analyzer = QueryAnalyzer()
	return analyzer.analyze(node)


def visualize_query_positions(node: VMASTNode, source_code: str) -> str:
	"""Quick visualization function for query positions."""
	debugger = ASTDebugger()
	return debugger.visualize_positions(node, source_code)


__all__ = [
	"ASTDebugger",
	"QueryAnalyzer", 
	"DebugInfo",
	"debug_ast",
	"analyze_query",
	"visualize_query_positions",
]

