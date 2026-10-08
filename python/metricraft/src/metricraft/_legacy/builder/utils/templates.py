"""
Templates for QueryBuilder operations used by mixins.

This module centralizes the shared helper and template-functions that were
previously methods on QueryBuilder. Keeping them here avoids circular imports
between builders and mixins, and provides a single place for logic reuse.

Design notes:
- Functions take the builder instance as the first argument when needed
  and return a new builder by calling builder._create_new_builder(AST, sign).
- No direct imports of specific Builder classes to avoid cycles; we only
  operate on AST nodes and exceptions.
- Duck typing is used for builder-like operands (has _ast_node/ast_node).
"""

from enum import Enum
from typing import List, Optional, Sequence, Union, TYPE_CHECKING


from metricraft._legacy.enums import SignState
from metricraft._legacy.tree import (
    NumberLiteral,
    StringLiteral,
    BinaryExpr,
    FunctionCall,
    AggregationExpr,
    ParenthesizedExpr,
    BinaryOperator,
    MetricSelector,
    GroupModifier
)
from metricraft._legacy.enums import AggregationOperator as AggOp
from metricraft._legacy.exceptions import VMInvalidExpressionError as InvalidExpressionError
from metricraft._legacy.tree.nodes.base import VMASTNode
from metricraft._legacy.exceptions import (
    InvalidParameterError,
    RangeVectorError,
    AggregationError,
    validate_labels,
)

if TYPE_CHECKING:
    from metricraft._legacy.builder.impl.base import MetricsBuilder


# ===== Helper utilities =====

def require_ast_node(builder: 'MetricsBuilder', operation_name: str) -> VMASTNode:
    """Ensure the builder has an expression and return the final AST node.

    Applies the builder's sign state via builder.ast_node property.
    """
    node = getattr(builder, "ast_node", None)
    if node is None:
        error = InvalidExpressionError(operation_name)
        # attach best-effort source context if available
        if hasattr(builder, "_last_query_attempt"):
            try:
                error.set_source_query(builder._last_query_attempt)
            except Exception:
                pass
        raise error
    return node


def maybe_parenthesize(node: VMASTNode) -> VMASTNode:
    """Wrap complex expressions in ParenthesizedExpr when needed.

    Rules:
    - Always parenthesize logical operations (and, or, unless)
    - Parenthesize BinaryExpr, AggregationExpr, FunctionCall in other contexts
    """
    if isinstance(node, BinaryExpr):
        if node.operator in (BinaryOperator.AND, BinaryOperator.OR, BinaryOperator.UNLESS):
            return ParenthesizedExpr(node)

    if isinstance(node, (BinaryExpr, AggregationExpr, FunctionCall)):
        return ParenthesizedExpr(node)

    return node


def _is_builder_like(obj: 'MetricsBuilder') -> bool:
    return hasattr(obj, "_ast_node") and hasattr(obj, "ast_node")


def convert_to_ast_node(operand: Union['MetricsBuilder', int, float, str]) -> VMASTNode:
    """Convert supported operand types to AST nodes (duck-typed for builders)."""
    if _is_builder_like(operand):
        if getattr(operand, "_ast_node", None) is None:
            raise InvalidParameterError("operand", operand, "QueryBuilder with expression set")
        return operand._ast_node  # raw node without re-applying sign/parentheses
    elif isinstance(operand, (int, float)):
        return NumberLiteral(float(operand))
    elif isinstance(operand, str):
        # Treat as metric name selector
        return MetricSelector(metric_name=operand)
    else:
        raise InvalidParameterError("operand", operand, "QueryBuilder, number, or string")


# ===== Template functions used by mixins =====

def create_binary_operation(
    builder: 'MetricsBuilder',
    operator: BinaryOperator,
    other: Union['MetricsBuilder', int, float, str],
    result_sign_state: SignState = SignState.NONE,
) -> 'MetricsBuilder':
    """Create BinaryExpr for arithmetic/comparison/logical ops and return new builder."""
    left_node = require_ast_node(builder, getattr(operator, "operation_name", str(operator)))
    left_node = maybe_parenthesize(left_node)

    other_node = convert_to_ast_node(other)
    other_node = maybe_parenthesize(other_node)

    new_node = BinaryExpr(left_node, operator, other_node)
    return builder._create_new_builder(new_node, result_sign_state)


def create_reverse_binary_operation(
    builder: 'MetricsBuilder',
    operator: BinaryOperator,
    other: Union['MetricsBuilder', int, float, str],
) -> 'MetricsBuilder':
    """Create reverse BinaryExpr for r-operations like __radd__ and return new builder."""
    other_node = convert_to_ast_node(other)
    right_node = builder.ast_node  # applies sign state
    new_node = BinaryExpr(other_node, operator, right_node)
    return builder._create_new_builder(new_node, SignState.NONE)


def create_unary_function(builder: 'MetricsBuilder', function_name: Union[str, Enum]) -> 'MetricsBuilder':
    """Create FunctionCall(function_name, [expr]) and return new builder."""
    if hasattr(function_name, "error_context"):
        error_context = function_name.error_context
    else:
        func_name_str = function_name.value if hasattr(function_name, "value") else function_name
        error_context = f"{func_name_str}() function call"

    final_node = require_ast_node(builder, error_context)
    func_call = FunctionCall(function_name, [final_node])
    return builder._create_new_builder(func_call, SignState.NONE)


def create_aggregation_function(
    builder: 'MetricsBuilder',
    operator: Union[Enum, str],
    param: Optional[Union[int, float, str, 'MetricsBuilder']] = None,
    by: Optional[List[str]] = None,
    without: Optional[List[str]] = None,
) -> 'MetricsBuilder':
    """Create AggregationExpr with optional parameter and grouping, return new builder."""
    func_name_str = operator.value if hasattr(operator, "value") else str(operator)

    if by is not None and without is not None:
        raise AggregationError(
            func_name_str,
            "Cannot specify both 'by' and 'without' parameters",
            "Use either 'by' or 'without', but not both",
        )

    if by is not None:
        validate_labels(by, f"{func_name_str}() aggregation")
    if without is not None:
        validate_labels(without, f"{func_name_str}() aggregation")

    expr_node = require_ast_node(builder, f"{func_name_str}() aggregation")

    # Optional parameter handling
    param_node = None
    if param is not None:
        if _is_builder_like(param):
            if getattr(param, "_ast_node", None) is None:
                raise InvalidParameterError("param", param, "QueryBuilder with expression set", func_name_str)
            param_node = param.ast_node
        elif isinstance(param, str):
            param_node = StringLiteral(param)
        elif isinstance(param, (int, float)):
            agg_op = AggOp(operator) if not isinstance(operator, AggOp) else operator
            if agg_op in (AggOp.TOPK, AggOp.BOTTOMK):
                if param <= 0:
                    raise InvalidParameterError("k", param, "positive integer", func_name_str)
            elif agg_op == AggOp.QUANTILE:
                if not (0.0 <= float(param) <= 1.0):
                    raise InvalidParameterError("quantile", param, "between 0.0 and 1.0", func_name_str)
            param_node = NumberLiteral(float(param))
        elif isinstance(param, VMASTNode):
            param_node = param
        else:
            # unsupported type
            raise InvalidParameterError("param", param, "QueryBuilder, ASTNode, number, or string", func_name_str)

    grouping = None
    if by is not None:
        grouping = GroupModifier(is_without=False, labels=by)
    elif without is not None:
        grouping = GroupModifier(is_without=True, labels=without)

    agg_expr = AggregationExpr(
        operator=AggOp(operator),
        expr=expr_node,
        parameter=param_node,
        grouping=grouping,
    )

    return builder._create_new_builder(agg_expr, SignState.NONE)


def create_range_vector_function(
    builder: 'MetricsBuilder',
    function_name: Union[str, Enum],
    duration: str = "5m",
    extra_args: Optional[Sequence[Union[int, float, str, 'MetricsBuilder', 'VMASTNode']]] = None,
) -> 'MetricsBuilder':
    """Convert to range vector then apply the function, return new builder."""
    func_name_str = function_name.value if hasattr(function_name, "value") else str(function_name)
    error_context = getattr(function_name, "error_context", f"{func_name_str}() range vector function")

    require_ast_node(builder, error_context)
    range_builder = builder.range(duration)

    if not (hasattr(range_builder, "_ast_node") and range_builder._ast_node):
        raise RangeVectorError(func_name_str, duration, "Failed to create range vector")

    func_args: List[VMASTNode] = [range_builder._ast_node]
    if extra_args:
        for arg in extra_args:
            if _is_builder_like(arg):
                if getattr(arg, "_ast_node", None) is None:
                    raise InvalidParameterError("arg", arg, "QueryBuilder with expression set")
                func_args.append(arg.ast_node)
            elif isinstance(arg, VMASTNode):
                func_args.append(arg)
            elif isinstance(arg, (int, float)):
                func_args.append(NumberLiteral(float(arg)))
            elif isinstance(arg, str):
                func_args.append(StringLiteral(arg))
            else:
                raise InvalidParameterError("arg", arg, "QueryBuilder, ASTNode, number, or string")

    func_call = FunctionCall(function_name, func_args)
    return builder._create_new_builder(func_call, SignState.NONE)


def create_simple_over_time_function(
    builder: 'MetricsBuilder',
    function_name: Union[str, Enum],
    duration: str = "5m"
) -> 'MetricsBuilder':
    """Simplified *_over_time helpers that only require a single range vector arg."""
    func_name_str = function_name.value if hasattr(function_name, "value") else str(function_name)

    require_ast_node(builder, f"{func_name_str}() function")
    range_builder = builder.range(duration)

    if not (hasattr(range_builder, "_ast_node") and range_builder._ast_node):
        raise RangeVectorError(func_name_str, duration, "Failed to create range vector")

    func_call = FunctionCall(function_name, [range_builder._ast_node])
    return builder._create_new_builder(func_call, SignState.NONE)


def create_transformation_function(
    builder: 'MetricsBuilder',
    function_name: str,
    *args: Union[int, float, str, 'MetricsBuilder']
) -> 'MetricsBuilder':
    """Create transformation functions (e.g., clamp_min/max) with args."""
    self_node = require_ast_node(builder, f"{function_name}() transformation")

    ast_args: List[VMASTNode] = [self_node]
    for arg in args:
        if _is_builder_like(arg):
            if getattr(arg, "_ast_node", None) is None:
                raise InvalidParameterError("arg", arg, "QueryBuilder with expression set", function_name)
            ast_args.append(arg.ast_node)
        elif isinstance(arg, (int, float)):
            ast_args.append(NumberLiteral(float(arg)))
        elif isinstance(arg, str):
            ast_args.append(StringLiteral(arg))
        else:
            raise InvalidParameterError("arg", arg, "QueryBuilder, number, or string", function_name)

    func_call = FunctionCall(function_name, ast_args)
    return builder._create_new_builder(func_call, SignState.NONE)


def create_label_function(builder: 'MetricsBuilder', function_name: str, *args: str) -> 'MetricsBuilder':
    """Create label manipulation functions (label_replace, label_join, alias, ...)."""
    self_node = require_ast_node(builder, f"{function_name}() label function")

    ast_args: List[VMASTNode] = [self_node]
    for arg in args:
        if isinstance(arg, str):
            ast_args.append(StringLiteral(arg))
        else:
            raise InvalidParameterError("arg", arg, "string", function_name)

    func_call = FunctionCall(function_name, ast_args)
    return builder._create_new_builder(func_call, SignState.NONE)


def create_function_with_args(
    builder: 'MetricsBuilder',
    function_name: str,
    args: List[Union['MetricsBuilder', int, float, str]],
    min_args: int = None,
    max_args: int = None,
) -> 'MetricsBuilder':
    """Generic function call helper that accepts a list of mixed-type args."""
    if min_args is not None and len(args) < min_args:
        raise InvalidParameterError("args", args, f"at least {min_args} arguments", function_name)
    if max_args is not None and len(args) > max_args:
        raise InvalidParameterError("args", args, f"at most {max_args} arguments", function_name)

    self_node = require_ast_node(builder, f"{function_name}() function call")

    ast_args: List[VMASTNode] = [self_node]
    for i, arg in enumerate(args):
        if _is_builder_like(arg):
            if getattr(arg, "_ast_node", None) is None:
                raise InvalidParameterError(f"args[{i}]", arg, "QueryBuilder with expression set", function_name)
            ast_args.append(arg.ast_node)
        elif isinstance(arg, (int, float)):
            ast_args.append(NumberLiteral(float(arg)))
        elif isinstance(arg, str):
            ast_args.append(StringLiteral(arg))
        else:
            raise InvalidParameterError(
                f"args[{i}]", arg, "QueryBuilder, number, or string", function_name
            )

    func_call = FunctionCall(function_name, ast_args)
    return builder._create_new_builder(func_call, SignState.NONE)
