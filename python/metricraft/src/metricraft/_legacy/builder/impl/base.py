"""VM-side MetricsBuilder implementation that subclasses the framework QueryBuilder.

Aggregates all mixins and provides concrete behavior for the VM provider.
"""

from functools import cached_property
from typing import Optional, Any

from metricraft._legacy.builder.impl.types import BuilderType
from metricraft._legacy.builder.impl.register import BuilderRegister
from metricraft._legacy.builder.mixins import (
	FactoryMixin,
	SignMixin,
	ArithmeticMixin,
	ComparisonMixin,
	LogicalMixin,
	TimeRangeMixin,
	RangeVectorFunctionsMixin,
	AggregationMixin,
	TransformationMixin,
	MathematicalMixin,
	ValidationMixin,
)
from metricraft._legacy.builder.utils import maybe_parenthesize
from metricraft._legacy.enums import SignState
import metricraft._legacy.tree.utils.validation as ast_validation
from metricraft._legacy.tree.nodes.base import VMASTNode
from metricraft._legacy.tree.nodes.types import NodeType
from metricraft._legacy.tree import (
	UnaryExpr,
	UnaryOperator,
)
from metricraft._legacy.visitor.code_gen import QueryToStringVisitor
from metricraft._legacy.exceptions import VMInvalidExpressionError as InvalidExpressionError
from metricraft._legacy.visitor import get_query_visitor
from metricraft._legacy.contracts import MetricsBuilderBase


class MetricsBuilder(
	FactoryMixin,
	SignMixin,
	ArithmeticMixin,
	ComparisonMixin,
	LogicalMixin,
	TimeRangeMixin,
	RangeVectorFunctionsMixin,
	AggregationMixin,
	TransformationMixin,
	MathematicalMixin,
	ValidationMixin,
	MetricsBuilderBase,
):
	"""
	Abstract base class for query builders.

	This class provides the foundation for building MetricsQL queries using
	a fluent, functional programming interface. All operations return new
	builder instances, ensuring immutability and enabling easy composition.

	The builder represents different states of MetricsQL expressions:
	- InstantVectorBuilder: Raw instant vector selectors (can add filters, ranges)
	- RangeVectorBuilder: Range vector selectors (must be processed by functions)
	- ProcessedVectorBuilder: Post-function/operation results (limited operations)
	- ScalarBuilder: Scalar values and expressions (similar to ProcessedVector)

	The builder maintains an internal AST representation that is transparent
	to the user, handling the complexity of query construction while providing
	a simple, chainable API.
	"""

	_FACTORY_METHOD_NAMES = {
		"from_metric",
		"from_string",
		"from_scalar",
		"from_expr",
		"from_time",
		"from_now",
		"from_start",
		"from_end",
	}

	def __init__(
			self,
			ast_node: Optional[VMASTNode] = None,
			sign_state: SignState = SignState.NONE):
		"""
		Initialize the query builder.

		Args:
			ast_node: The root AST node for this builder instance.
					 If None, the builder starts with no root expression.
			sign_state: The sign state for this expression (NONE, POSITIVE, NEGATIVE).
		"""
		self._ast_node = ast_node
		self._sign_state = sign_state
		self._provider_config: Optional[Any] = None
		self._default_validation_standard: str = "MetricsQL"

	def __getattribute__(self, name: str) -> Any:
		attr = super().__getattribute__(name)
		if name in type(self)._FACTORY_METHOD_NAMES and callable(attr):
			def _wrapped_factory(*args: Any, **kwargs: Any):
				result = attr(*args, **kwargs)
				return self._copy_runtime_context(result)
			return _wrapped_factory
		return attr

	def _attach_provider_config(self, config: Any) -> 'MetricsBuilder':
		self._provider_config = config
		config_type = getattr(config, "type", None)
		if isinstance(config_type, str) and config_type.lower() == "prometheus":
			self._default_validation_standard = "PromQL"
		else:
			self._default_validation_standard = "MetricsQL"
		return self

	def _copy_runtime_context(self, builder: Any) -> Any:
		if isinstance(builder, MetricsBuilder):
			builder._provider_config = getattr(self, "_provider_config", None)
			builder._default_validation_standard = getattr(
				self, "_default_validation_standard", "MetricsQL")
		return builder

	@cached_property
	def ast_node(self) -> Optional[VMASTNode]:
		"""Get the current AST node with sign state applied if needed."""
		if self._ast_node is None:
			return None
		return self._apply_sign_state(self._ast_node)

	def _apply_sign_state(self, node: VMASTNode) -> VMASTNode:
		"""
		Apply the current sign state to an AST node.

		This method is responsible only for sign state application,
		following the single responsibility principle.

		Args:
			node: The AST node to apply sign state to.

		Returns:
			The node with sign state applied (wrapped in UnaryExpr if needed).
		"""
		if self._sign_state == SignState.NONE:
			return node

		# Use shared template helper to ensure consistent parenthesis rules
		parenthesized_node = maybe_parenthesize(node)
		return UnaryExpr(
			UnaryOperator.MINUS if self._sign_state == SignState.NEGATIVE else UnaryOperator.PLUS,
			parenthesized_node
		)

	def _get_raw_ast_node(self) -> Optional[VMASTNode]:
		"""
		Get the raw AST node without any sign state applied.

		This is useful when you need the underlying node structure
		without sign modifications.

		Returns:
			The raw AST node or None if no expression is set.
		"""
		return self._ast_node

	def _require_ast_node(self, operation_name: str) -> VMASTNode:
		"""
		Get the final AST node, ensuring it's not None.

		This method is a helper for operations that require a valid AST node.
		It reduces boilerplate error checking throughout the codebase.

		Args:
			operation_name: Name of the operation for error messages.

		Returns:
			The final AST node with sign state applied.

		Raises:
			InvalidExpressionError: If no AST node is set.
		"""
		if self.ast_node is None:
			error = InvalidExpressionError(operation_name)
			# Try to set some context if we have any partial query info
			if hasattr(self, '_last_query_attempt'):
				error.set_source_query(self._last_query_attempt)
			raise error
		return self.ast_node

	@cached_property
	def _query_string(self) -> str:
		"""
		Cached property for the query string.

		Returns:
			The MetricsQL query string representation of the current AST.

		Raises:
			ValueError: If no expression has been set (AST node is None).
		"""
		if self.ast_node is None:
			raise ValueError(
				"No expression set. Use one of the initialization methods first.")

		return get_query_visitor().visit(self.ast_node)

	def build(
			self,
			validate: bool = True,
			visitor: Optional['QueryToStringVisitor'] = None) -> str:
		"""
		Build the final MetricsQL query string.

		Args:
			validate: Whether to validate the AST before building (default: True)
			visitor: Optional custom visitor for code generation. If None, uses the default visitor.

		Returns:
			The MetricsQL query string representation of the current AST.

		Raises:
			ValueError: If no expression has been set (AST node is None).
			ValidationError: If validation is enabled and the AST is invalid.
		"""
		if validate and self.ast_node is not None:
			# Prefer object-based validation to preserve AST + positions
			obj_errors = ast_validation.validate_ast_node(self.ast_node, self.ast_node)
			if obj_errors:
				# Show the first error with accurate arrow once
				first_err = obj_errors[0]
				try:
					# Ensure we have a proper root for absolute position calculation
					if getattr(first_err, 'root_node', None) is None:
						first_err.root_node = self.ast_node
					# Generate source query for arrow rendering
					source_query = get_query_visitor().visit(self.ast_node)
					first_err.set_source_query(source_query)
				except Exception:
					pass
				raise first_err

		if visitor is not None:
			# Use custom visitor
			if self.ast_node is None:
				raise ValueError(
					"No expression set. Use one of the initialization methods first.")
			return visitor.visit(self.ast_node)
		else:
			# Use cached default visitor
			return self._query_string

	def _create_new_builder(
			self,
			ast_node: VMASTNode,
			sign_state: SignState = SignState.NONE) -> 'MetricsBuilder':
		"""
		Create a new builder instance with the given AST node.

		This method determines the appropriate builder type based on the
		AST node type and MetricsQL state model:
		- MetricSelector -> InstantVectorBuilder
		- RangeExpr -> RangeExprBuilder
		- Function results, operations -> ProcessedVectorBuilder
		- Literals, time functions -> ScalarBuilder

		Args:
			ast_node: The AST node for the new builder.
			sign_state: The sign state to apply to the new builder.

		Returns:
			A new builder instance of the appropriate type.
		"""
		if ast_node is None:
			raise ValueError("ast_node cannot be None")

		if ast_node.node_type is NodeType.METRIC_SELECTOR:
			return self._copy_runtime_context(BuilderRegister.get_builder(
				BuilderType.INSTANT_VECTOR,
				ast_node=ast_node,
				sign_state=sign_state,
			))
		elif ast_node.node_type is NodeType.RANGE_EXPR:
			return self._copy_runtime_context(BuilderRegister.get_builder(
				BuilderType.RANGE_VECTOR,
				ast_node=ast_node,
				sign_state=sign_state,
			))
		elif ast_node.node_type in (NodeType.NUMBER_LITERAL, NodeType.STRING_LITERAL, NodeType.DURATION_LITERAL) or \
				(ast_node.node_type is NodeType.FUNCTION_CALL and ast_node.name in ['time', 'now', 'start', 'end']):
			return self._copy_runtime_context(BuilderRegister.get_builder(
				BuilderType.SCALAR,
				ast_node=ast_node,
				sign_state=sign_state,
			))
		else:
			# Functions, operations, aggregations result in processed vectors
			return self._copy_runtime_context(BuilderRegister.get_builder(
				BuilderType.PROCESSED_VECTOR,
				ast_node=ast_node,
				sign_state=sign_state,
			))


