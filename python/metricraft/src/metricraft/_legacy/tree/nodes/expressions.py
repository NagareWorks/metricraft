"""
MetricsQL/PromQL expression AST nodes (authoritative in VM provider).

This module contains AST nodes for various types of expressions including
binary operations, unary operations, function calls, and aggregation
expressions.
"""

from enum import Enum
from typing import Optional, List, TypeVar, TYPE_CHECKING, Union

from metricraft._legacy.ast import Position, ASTVisitor
from metricraft._legacy.tree.nodes.base import VMASTNode
from metricraft._legacy.tree.nodes.types import NodeType
from metricraft._legacy.enums import BinaryOperator, UnaryOperator, AggregationOperator
from metricraft._legacy.visitor import get_query_visitor

if TYPE_CHECKING:
	from .literals import DurationLiteral

T = TypeVar('T')


class GroupModifier(VMASTNode):
	"""
	Represents grouping modifiers for aggregation and binary operations.

	Examples:
	- by (instance, job)
	- without (instance)

	Used in aggregations and binary operations to specify grouping behavior.
	"""

	def __init__(self, is_without: bool, labels: List[str]):
		self.is_without = is_without  # True for 'without', False for 'by'
		self.labels = labels
		super().__init__()

	@property
	def node_type(self) -> NodeType:
		return NodeType.GROUP_MODIFIER

	def __str__(self) -> str:
		"""Debug representation only. Use QueryToStringVisitor for code generation."""
		keyword = "without" if self.is_without else "by"
		return f"GroupModifier({keyword}, {self.labels})"

	def accept(self, visitor: 'ASTVisitor[T]') -> T:
		return visitor.visit(self)

	def _calculate_relative_position(self) -> Position:
		"""Calculate relative position based on text representation."""
		visitor = get_query_visitor()
		text = visitor.visit(self)
		return Position.for_text(text)


class BinaryModifier(VMASTNode):
	"""
	Represents binary operation modifiers.

	Examples:
	- on (instance, job)
	- ignoring (instance)
	- group_left()
	- group_right(label1, label2)

	Note: These modifiers control how vector matching works in binary operations.
	"""

	def __init__(
		self,
		matching_type: Optional[str] = None,  # 'on' or 'ignoring'
		labels: Optional[List[str]] = None,
		group_type: Optional[str] = None,  # 'group_left' or 'group_right'
		group_labels: Optional[List[str]] = None,
	):
		self.matching_type = matching_type
		self.labels = labels or []
		self.group_type = group_type
		self.group_labels = group_labels or []
		super().__init__()

	@property
	def node_type(self) -> NodeType:
		return NodeType.BINARY_MODIFIER

	def __str__(self) -> str:
		"""Debug representation only. Use QueryToStringVisitor for code generation."""
		parts = []
		if self.matching_type:
			parts.append(f"{self.matching_type}({len(self.labels)} labels)")
		if self.group_type:
			parts.append(f"{self.group_type}({len(self.group_labels)} labels)")
		return f"BinaryModifier({', '.join(parts) if parts else 'empty'})"

	def accept(self, visitor: 'ASTVisitor[T]') -> T:
		return visitor.visit(self)

	def _calculate_relative_position(self) -> Position:
		"""Calculate relative position based on text representation."""
		visitor = get_query_visitor()
		text = visitor.visit(self)
		return Position.for_text(text)


class BinaryExpr(VMASTNode):
	"""
	Represents a binary expression.

	Examples:
	- cpu_usage + memory_usage
	- cpu_usage > 0.8
	- cpu_usage and memory_usage
	- cpu_usage + on(instance) memory_usage
	"""

	def __init__(
		self,
		left: VMASTNode,
		operator: BinaryOperator,
		right: VMASTNode,
		modifier: Optional[BinaryModifier] = None,
		return_bool: bool = False,
	):
		self.left = left
		self.operator = operator
		self.right = right
		self.modifier = modifier
		self.return_bool = return_bool
		super().__init__()

	@property
	def node_type(self) -> NodeType:
		return NodeType.BINARY_EXPR

	def on(self, *labels: str) -> 'BinaryExpr':
		"""
		Add an 'on' modifier to this binary expression.

		Usage: expr1 + expr2.on('instance', 'job')
		"""
		if not self.modifier:
			modifier = BinaryModifier(matching_type='on', labels=list(labels))
		else:
			# Create a copy of existing modifier with new on settings
			modifier = BinaryModifier(
				matching_type='on',
				labels=list(labels),
				group_type=self.modifier.group_type,
				group_labels=self.modifier.group_labels[:] if self.modifier.group_labels else None,
			)

		# Return a new BinaryExpr instance
		return BinaryExpr(
			left=self.left,
			operator=self.operator,
			right=self.right,
			modifier=modifier,
			return_bool=self.return_bool,
		)

	def ignoring(self, *labels: str) -> 'BinaryExpr':
		"""
		Add an 'ignoring' modifier to this binary expression.

		Usage: expr1 + expr2.ignoring('instance')
		"""
		if not self.modifier:
			modifier = BinaryModifier(matching_type='ignoring', labels=list(labels))
		else:
			# Create a copy of existing modifier with new ignoring settings
			modifier = BinaryModifier(
				matching_type='ignoring',
				labels=list(labels),
				group_type=self.modifier.group_type,
				group_labels=self.modifier.group_labels[:] if self.modifier.group_labels else None,
			)

		# Return a new BinaryExpr instance
		return BinaryExpr(
			left=self.left,
			operator=self.operator,
			right=self.right,
			modifier=modifier,
			return_bool=self.return_bool,
		)

	def group_left(self, *labels: str) -> 'BinaryExpr':
		"""
		Add a 'group_left' modifier to this binary expression.

		Usage: expr1 + expr2.group_left('label1', 'label2')
		"""
		if not self.modifier:
			modifier = BinaryModifier(group_type='group_left', group_labels=list(labels))
		else:
			# Create a copy of existing modifier with new group_left settings
			modifier = BinaryModifier(
				matching_type=self.modifier.matching_type,
				labels=self.modifier.labels[:] if self.modifier.labels else None,
				group_type='group_left',
				group_labels=list(labels),
			)

		# Return a new BinaryExpr instance
		return BinaryExpr(
			left=self.left,
			operator=self.operator,
			right=self.right,
			modifier=modifier,
			return_bool=self.return_bool,
		)

	def group_right(self, *labels: str) -> 'BinaryExpr':
		"""
		Add a 'group_right' modifier to this binary expression.

		Usage: expr1 + expr2.group_right('label1', 'label2')
		"""
		if not self.modifier:
			modifier = BinaryModifier(group_type='group_right', group_labels=list(labels))
		else:
			# Create a copy of existing modifier with new group_right settings
			modifier = BinaryModifier(
				matching_type=self.modifier.matching_type,
				labels=self.modifier.labels[:] if self.modifier.labels else None,
				group_type='group_right',
				group_labels=list(labels),
			)

		# Return a new BinaryExpr instance
		return BinaryExpr(
			left=self.left,
			operator=self.operator,
			right=self.right,
			modifier=modifier,
			return_bool=self.return_bool,
		)

	def bool(self) -> 'BinaryExpr':
		"""
		Add a 'bool' modifier to this binary expression.

		Usage: expr1 > expr2.bool()
		"""
		# Return a new BinaryExpr instance with return_bool set to True
		return BinaryExpr(
			left=self.left,
			operator=self.operator,
			right=self.right,
			modifier=self.modifier,
			return_bool=True,
		)

	def __str__(self) -> str:
		"""Debug representation only. Use QueryToStringVisitor for code generation."""
		return f"BinaryExpr({self.operator.value})"

	def accept(self, visitor: 'ASTVisitor[T]') -> T:
		return visitor.visit(self)

	def _calculate_relative_position(self) -> Position:
		"""Calculate relative position based on text representation."""
		visitor = get_query_visitor()
		text = visitor.visit(self)
		return Position.for_text(text)


class UnaryExpr(VMASTNode):
	"""
	Represents a unary expression.

	Examples:
	- -cpu_usage
	- +memory_usage
	"""

	def __init__(self, operator: UnaryOperator, operand: VMASTNode):
		self.operator = operator
		self.operand = operand
		super().__init__()

	@property
	def node_type(self) -> NodeType:
		return NodeType.UNARY_EXPR

	def __str__(self) -> str:
		"""Debug representation only. Use QueryToStringVisitor for code generation."""
		return f"UnaryExpr({self.operator.value})"

	def accept(self, visitor: 'ASTVisitor[T]') -> T:
		return visitor.visit(self)

	def _calculate_relative_position(self) -> Position:
		"""Calculate relative position based on text representation."""
		visitor = get_query_visitor()
		text = visitor.visit(self)
		return Position.for_text(text)


class FunctionCall(VMASTNode):
	"""
	Represents a function call expression.

	Examples:
	- rate(cpu_usage[5m])
	- sum(cpu_usage) by (instance)
	- histogram_quantile(0.95, rate(http_request_duration_bucket[5m]))

	Note: MetricsQL extends PromQL with many additional functions.
	"""

	def __init__(self, name: Union[str, Enum], args: List[VMASTNode]):
		# Support both string and enum types for backward compatibility
		self.name = name.value if hasattr(name, 'value') else name
		self._name_enum = name if hasattr(name, 'value') else None
		self.args = args
		super().__init__()

	@property
	def name_enum(self) -> Optional[Enum]:
		"""Get the enum representation of the function name if available."""
		return self._name_enum

	@property
	def node_type(self) -> NodeType:
		return NodeType.FUNCTION_CALL

	def __str__(self) -> str:
		"""Debug representation only. Use QueryToStringVisitor for code generation."""
		return f"FunctionCall({self.name}, {len(self.args)} args)"

	def accept(self, visitor: 'ASTVisitor[T]') -> T:
		return visitor.visit(self)

	def _calculate_relative_position(self) -> Position:
		"""Calculate relative position based on text representation."""
		visitor = get_query_visitor()
		text = visitor.visit(self)
		return Position.for_text(text)


class AggregationExpr(VMASTNode):
	"""
	Represents an aggregation expression.

	Examples:
	- sum(cpu_usage)
	- sum(cpu_usage) by (instance)
	- topk(5, cpu_usage)
	- count_values("version", build_info)

	Note: MetricsQL provides additional aggregation functions beyond standard PromQL.
	"""

	def __init__(
		self,
		operator: AggregationOperator,
		expr: VMASTNode,
		parameter: Optional[VMASTNode] = None,
		grouping: Optional[GroupModifier] = None,
	):
		self.operator = operator
		self.expr = expr
		# For functions like topk(k, ...), quantile(q, ...)
		self.parameter = parameter
		self.grouping = grouping
		super().__init__()

	@property
	def node_type(self) -> NodeType:
		return NodeType.AGGREGATION_EXPR

	def by(self, *labels: str) -> 'AggregationExpr':
		"""
		Add a 'by' grouping modifier to this aggregation.

		Usage: sum(cpu_usage).by('instance', 'job')
		"""
		# Return a new AggregationExpr instance with the by grouping
		new_grouping = GroupModifier(is_without=False, labels=list(labels))
		return AggregationExpr(
			operator=self.operator,
			expr=self.expr,
			parameter=self.parameter,
			grouping=new_grouping,
		)

	def without(self, *labels: str) -> 'AggregationExpr':
		"""
		Add a 'without' grouping modifier to this aggregation.

		Usage: sum(cpu_usage).without('instance')
		"""
		# Return a new AggregationExpr instance with the without grouping
		new_grouping = GroupModifier(is_without=True, labels=list(labels))
		return AggregationExpr(
			operator=self.operator,
			expr=self.expr,
			parameter=self.parameter,
			grouping=new_grouping,
		)

	def __str__(self) -> str:
		"""Debug representation only. Use QueryToStringVisitor for code generation."""
		has_param = "with param" if self.parameter else "no param"
		has_grouping = "with grouping" if self.grouping else "no grouping"
		return f"AggregationExpr({self.operator.value}, {has_param}, {has_grouping})"

	def accept(self, visitor: 'ASTVisitor[T]') -> T:
		return visitor.visit(self)

	def _calculate_relative_position(self) -> Position:
		"""Calculate relative position based on text representation."""
		visitor = get_query_visitor()
		text = visitor.visit(self)
		return Position.for_text(text)


class ParenthesizedExpr(VMASTNode):
	"""
	Represents a parenthesized expression.

	Examples:
	- (cpu_usage + memory_usage)
	- (rate(cpu_usage[5m]) > 0.8)
	"""

	def __init__(self, expr: VMASTNode):
		self.expr = expr
		super().__init__()

	@property
	def node_type(self) -> NodeType:
		return NodeType.PARENTHESIZED_EXPR

	def __str__(self) -> str:
		"""Debug representation only. Use QueryToStringVisitor for code generation."""
		return "ParenthesizedExpr(...)"

	def accept(self, visitor: 'ASTVisitor[T]') -> T:
		return visitor.visit(self)

	def _calculate_relative_position(self) -> Position:
		"""Calculate relative position based on text representation."""
		visitor = get_query_visitor()
		text = visitor.visit(self)
		return Position.for_text(text)


class RangeExpr(VMASTNode):
	"""
	Represents a range expression that applies a range selector to an arbitrary expression.

	This allows for complex range expressions like:
	- cpu_usage[5m]
	- (-cpu_usage)[5m]
	- (cpu_usage + memory_usage)[1h]
	"""

	def __init__(self, expr: VMASTNode, range_duration: 'DurationLiteral'):
		self.expr = expr
		self.range_duration = range_duration
		super().__init__()

	@property
	def node_type(self) -> NodeType:
		return NodeType.RANGE_EXPR

	def __str__(self) -> str:
		"""Debug representation only. Use QueryToStringVisitor for code generation."""
		return f"RangeExpr([{self.range_duration.value}])"

	def accept(self, visitor: 'ASTVisitor[T]') -> T:
		return visitor.visit(self)

	def _calculate_relative_position(self) -> Position:
		"""Calculate relative position based on text representation."""
		visitor = get_query_visitor()
		text = visitor.visit(self)
		return Position.for_text(text)

