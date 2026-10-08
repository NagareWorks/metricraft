"""AST literal nodes used by MetricsQL/PromQL codegen and validation.

Each literal node carries a minimal, immutable position (relative to parent)
so that validators and visitors can render precise error locations.

Contract
- Inputs: a Python primitive representing the literal value
- Output: an immutable AST node with `.value`, `.node_type`, `.pos`
- Error modes: invalid inputs raise ValueError (where applicable)
- Success criteria: `accept(visitor)` delegates to visitor.visit(self)
"""

from typing import TypeVar

from metricraft._legacy.ast.astnode import Position
from metricraft._legacy.tree.nodes.base import VMASTNode
from metricraft._legacy.tree.nodes.types import NodeType

T = TypeVar('T')


class NumberLiteral(VMASTNode):
	"""Numeric literal node.

	Args:
		value: Float value. Supports integers, floats, NaN, +/-Inf.

	Attributes:
		value (float): Underlying numeric value
		node_type (NodeType): NodeType.NUMBER_LITERAL
		pos (Position): Relative position based on textual representation

	Notes:
		- NaN renders as `NaN`, Infinity as `Inf`/`-Inf` for length estimation
	"""

	def __init__(self, value: float):
		self.value = value
		super().__init__()
		
		# Calculate and set position after initialization
		self.pos = self._calculate_relative_position()
		self._freeze_node()

	def _calculate_relative_position(self) -> Position:
		"""Calculate position based on number's text representation."""
		try:
			if self.value != self.value:  # NaN
				text = "NaN"
			elif self.value == float('inf'):
				text = "Inf"
			elif self.value == float('-inf'):
				text = "-Inf"
			elif self.value == int(self.value):
				text = str(int(self.value))
			else:
				text = str(self.value)
		except (OverflowError, ValueError):
			text = str(self.value)
		return Position.for_text(text)

	@property
	def node_type(self) -> NodeType:
		return NodeType.NUMBER_LITERAL

	def __str__(self) -> str:
		return f"NumberLiteral({self.value})"

	def accept(self, visitor):  # type: ignore[override]
		return visitor.visit(self)


class StringLiteral(VMASTNode):
	"""String literal node.

	Args:
		value: Raw string without quotes. Stored verbatim.

	Attributes:
		value (str): Underlying string value
		node_type (NodeType): NodeType.STRING_LITERAL
		pos (Position): Relative position including quotes for length

	Notes:
		- Position uses the quoted form to reflect generated query text.
	"""

	def __init__(self, value: str):
		self.value = value
		super().__init__()
		
		# Calculate and set position after initialization
		self.pos = self._calculate_relative_position()
		self._freeze_node()

	def _calculate_relative_position(self) -> Position:
		text = f'"{self.value}"'
		return Position.for_text(text)

	@property
	def node_type(self) -> NodeType:
		return NodeType.STRING_LITERAL

	def __str__(self) -> str:
		return f"StringLiteral({self.value!r})"

	def accept(self, visitor):  # type: ignore[override]
		return visitor.visit(self)


class DurationLiteral(VMASTNode):
	"""Duration literal node.

	Args:
		value: Duration string like "5m", "1h", "30s". Not validated here.

	Attributes:
		value (str): Raw duration string
		node_type (NodeType): NodeType.DURATION_LITERAL
		pos (Position): Relative position equal to the plain duration text

	Notes:
		- Validation of duration format is handled by higher-level validators.
	"""

	def __init__(self, value: str):
		self.value = value
		super().__init__()
		# Calculate and set position after initialization
		self.pos = self._calculate_relative_position()
		self._freeze_node()

	def _calculate_relative_position(self) -> Position:
		return Position.for_text(self.value)

	@property
	def node_type(self) -> NodeType:
		return NodeType.DURATION_LITERAL

	def __str__(self) -> str:
		return f"DurationLiteral({self.value!r})"

	def accept(self, visitor):  # type: ignore[override]
		return visitor.visit(self)
