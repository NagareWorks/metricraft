"""
MetricsQL-specific AST nodes (authoritative in VM provider).

This module contains AST nodes for MetricsQL-specific features that extend
standard PromQL functionality.
"""

from typing import Optional, Dict, TypeVar, TYPE_CHECKING, Union

from metricraft._legacy.ast import Position, ASTVisitor
from metricraft._legacy.tree.nodes.base import VMASTNode
from metricraft._legacy.tree.nodes.types import NodeType
from metricraft._legacy.visitor import get_query_visitor

if TYPE_CHECKING:
	from .literals import DurationLiteral

T = TypeVar('T')


class WithExpr(VMASTNode):
	"""
	Represents a WITH expression in MetricsQL.
	"""

	def __init__(self, definitions: Dict[str, VMASTNode], expr: VMASTNode):
		self.definitions = definitions  # Variable name -> expression mappings
		self.expr = expr  # Main expression that uses the definitions
		super().__init__()

	@property
	def node_type(self) -> NodeType:
		return NodeType.WITH_EXPR

	def __str__(self) -> str:
		return f"WithExpr({len(self.definitions)} definitions)"

	def accept(self, visitor: 'ASTVisitor[T]') -> T:
		return visitor.visit(self)

	def _calculate_relative_position(self) -> Position:
		visitor = get_query_visitor()
		text = visitor.visit(self)
		return Position.for_text(text)


class SubqueryExpr(VMASTNode):
	"""
	Represents a subquery expression: <expr>[<range>:<resolution>]
	"""

	def __init__(self, expr: VMASTNode, range_duration: 'DurationLiteral', step: Optional['DurationLiteral'] = None):
		self.expr = expr
		self.range_duration = range_duration
		self.step = step
		super().__init__()

	@property
	def node_type(self) -> NodeType:
		return NodeType.SUBQUERY_EXPR

	def __str__(self) -> str:
		has_step = "with step" if self.step else "no step"
		return f"SubqueryExpr([{self.range_duration.value}], {has_step})"

	def accept(self, visitor: 'ASTVisitor[T]') -> T:
		return visitor.visit(self)

	def _calculate_relative_position(self) -> Position:
		visitor = get_query_visitor()
		text = visitor.visit(self)
		return Position.for_text(text)


class RollupConfig(VMASTNode):
	"""Represents rollup configuration in MetricsQL."""

	def __init__(self, expr: VMASTNode, config: Dict[str, Union[str, int, float]]):
		self.expr = expr
		self.config = config
		super().__init__()

	@property
	def node_type(self) -> NodeType:
		return NodeType.ROLLUP_CONFIG

	def __str__(self) -> str:
		return f"RollupConfig({len(self.config)} config items)"

	def accept(self, visitor: 'ASTVisitor[T]') -> T:
		return visitor.visit(self)

	def _calculate_relative_position(self) -> Position:
		visitor = get_query_visitor()
		text = visitor.visit(self)
		return Position.for_text(text)


class KeepMetricNames(VMASTNode):
	"""Represents the keep_metric_names modifier in MetricsQL."""

	def __init__(self, expr: VMASTNode):
		self.expr = expr
		super().__init__()

	def _calculate_relative_position(self) -> Position:
		return Position.for_text("keep_metric_names")

	@property
	def node_type(self) -> NodeType:
		return NodeType.KEEP_METRIC_NAMES

	def __str__(self) -> str:
		return "KeepMetricNames(...)"

	def accept(self, visitor: 'ASTVisitor[T]') -> T:
		return visitor.visit(self)
