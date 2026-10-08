"""AST nodes for MetricsQL/PromQL selectors (VM provider)."""

from typing import Optional, List, TypeVar, TYPE_CHECKING, Union

from metricraft._legacy.ast import Position, ASTVisitor
from metricraft._legacy.tree.nodes.base import VMASTNode
from metricraft._legacy.tree.nodes.types import NodeType
from metricraft._legacy.enums import MatchType
from metricraft._legacy.tree.nodes.literals import StringLiteral

if TYPE_CHECKING:
	from .literals import DurationLiteral

T = TypeVar('T')


class LabelMatcher(VMASTNode):
	"""Represents a label matcher for metric selectors."""

	def __init__(self, name: str, op: MatchType, value: Optional[str]):
		if not name or not isinstance(name, str):
			raise ValueError(f"Label name must be a non-empty string, got: {name}")
		
		# Convert None to empty string to support PromQL syntax
		if value is None:
			value = ""
			
		self.name = name
		self.op = op
		self.value = value
		# Also create a child StringLiteral node for precise positioning in visitors
		# Keep both string value and AST node; codegen can still use self.value
		self.value_node = StringLiteral(value)
		super().__init__()
		
		# Calculate and set position after initialization
		self.pos = self._calculate_relative_position()
		self._freeze_node()

	def _calculate_relative_position(self) -> Position:
		text = f'{self.name}{self.op.value}"{self.value}"'
		return Position.for_text(text)

	@property
	def node_type(self) -> NodeType:
		return NodeType.LABEL_MATCHER

	def __str__(self) -> str:
		return f"LabelMatcher({self.name}, {self.op.value}, {self.value!r})"

	def accept(self, visitor: 'ASTVisitor[T]') -> T:  # type: ignore[name-defined]
		return visitor.visit(self)


class MetricSelector(VMASTNode):
	"""Base class for metric selectors."""

	def __init__(
		self,
		metric_name: Optional[str] = None,
		label_matchers: Optional[List[LabelMatcher]] = None,
	):
		self.metric_name = metric_name
		self.label_matchers = label_matchers or []
		super().__init__()
		
		# Calculate and set position after initialization
		self.pos = self._calculate_relative_position()
		self._freeze_node()

	def _calculate_relative_position(self) -> Position:
		if self.metric_name:
			text = self.metric_name
			if self.label_matchers:
				matchers_text = ", ".join(
					f'{m.name}{m.op.value}"{m.value}"' for m in self.label_matchers
				)
				text += "{" + matchers_text + "}"
			return Position.for_text(text)
		elif self.label_matchers:
			matchers_text = ", ".join(
				f'{m.name}{m.op.value}"{m.value}"' for m in self.label_matchers
			)
			text = "{" + matchers_text + "}"
			return Position.for_text(text)
		else:
			return Position.for_text("{}")

	@property
	def node_type(self) -> NodeType:
		return NodeType.METRIC_SELECTOR

	def __str__(self) -> str:
		metric_name = self.metric_name or "<no_name>"
		matchers_count = len(self.label_matchers)
		return f"MetricSelector({metric_name}, {matchers_count} matchers)"

	def accept(self, visitor: 'ASTVisitor[T]') -> T:  # type: ignore[name-defined]
		return visitor.visit(self)



class OffsetExpr(VMASTNode):
	"""Represents an offset modifier."""

	def __init__(self, expr: VMASTNode, offset: 'DurationLiteral'):
		self.expr = expr
		self.offset = offset
		super().__init__()

	@property
	def node_type(self) -> NodeType:
		return NodeType.OFFSET_EXPR

	def __str__(self) -> str:
		return f"OffsetExpr({self.offset.value})"

	def accept(self, visitor: 'ASTVisitor[T]') -> T:  # type: ignore[name-defined]
		return visitor.visit(self)


class AtExpr(VMASTNode):
	"""Represents an @ modifier."""

	def __init__(self, expr: VMASTNode, timestamp: Union[float, str]):
		self.expr = expr
		self.timestamp = timestamp
		super().__init__()

	@property
	def node_type(self) -> NodeType:
		return NodeType.AT_EXPR

	def __str__(self) -> str:
		return f"AtExpr(@{self.timestamp})"

	def accept(self, visitor: 'ASTVisitor[T]') -> T:  # type: ignore[name-defined]
		return visitor.visit(self)
