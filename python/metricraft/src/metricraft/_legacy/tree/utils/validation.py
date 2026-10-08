"""
AST node validation module - VM implementation.

This module provides validators that work exclusively with AST nodes,
ensuring proper position tracking and error reporting.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Union
import re

from metricraft._legacy.exceptions import ValidationError, InvalidParameterError
from metricraft._legacy.tree import (
    AggregationExpr,
    FunctionCall,
    LabelMatcher,
    MetricSelector,
)
from metricraft._legacy.tree.nodes.base import VMASTNode
from metricraft._legacy.tree.nodes.types import NodeType
from metricraft._legacy.enums.operators import MatchType


# Commonly used label names for ultra-fast pass path
_COMMON_LABEL_WHITELIST = {
    'instance', 'job', 'method', 'status', 'status_code', 'endpoint', 'service',
    'namespace', 'pod', 'container', 'cluster', 'datacenter', 'datacentre', 'region',
    'zone', 'app', 'application', 'env', 'environment', 'scheme', 'path', 'route',
    'port', 'protocol', 'role', 'component', 'version', '__name__'
}

# Precompiled regex patterns for validation
_LABEL_NAME_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
_METRIC_NAME_RE = re.compile(r'^[a-zA-Z_:][a-zA-Z0-9_:]*$')


def escape_promql_string(value: str) -> str:
    """Escape special characters in PromQL strings to prevent injection attacks.

    Args:
        value: Original string

    Returns:
        Escaped safe string
    """
    if len(value) > 1000:  # Simple length check to prevent DoS
        raise ValueError("String too long for safe processing")

    # Escape in order: backslash first, then quotes
    return value.replace('\\', '\\\\').replace('"', '\\"').replace("'", "\\'")


def validate_promql_string(value: str) -> bool:
    """Lightweight PromQL string validation using character escaping instead of regex.

    Args:
        value: String to validate

    Returns:
        True if valid
    """
    if not value:
        return True

    if len(value) > 1000:  # Simple length check
        return False

    # Check for unescaped special character sequences
    unescaped_quotes = 0
    i = 0
    while i < len(value):
        if value[i] == '\\':
            i += 2  # Skip escape character
            continue
        elif value[i] in ('"', "'"):
            unescaped_quotes += 1
        i += 1

    # Odd number of unescaped quotes may indicate injection risk
    return unescaped_quotes % 2 == 0


class ASTValidator(ABC):
    """Base class for AST validators with position-aware error reporting"""

    @abstractmethod
    def validate(self, node: VMASTNode, root_node: Optional[VMASTNode] = None) -> List[ValidationError]:
        """
        Validate an AST node and return a list of errors.

        Args:
            node: The AST node to validate
            root_node: Root node for absolute position calculation

        Returns:
            List of ValidationError objects with position info, empty list means validation passed
        """
        pass

    def _create_error(self, message: str, node: VMASTNode, root_node: Optional[VMASTNode] = None,
                      context: Optional[str] = None) -> ValidationError:
        """
        Create a ValidationError with proper position information.

        Args:
            message: Error message
            node: AST node where the error occurred
            root_node: Root node for absolute position calculation
            context: Additional context information

        Returns:
            ValidationError with position information
        """
        return ValidationError(
            message=message,
            ast_node=node,
            root_node=root_node,
            context=context
        )




class StructuralASTValidator(ASTValidator):
    """Validator for structural correctness of AST nodes"""

    def validate(self, node: VMASTNode, root_node: Optional[VMASTNode] = None) -> List[ValidationError]:
        """Validate AST node structure"""
        errors = []

        if node.node_type is NodeType.LABEL_MATCHER:
            errors.extend(self._validate_label_matcher(node, root_node))
        elif node.node_type is NodeType.METRIC_SELECTOR:
            errors.extend(self._validate_metric_selector(node, root_node))
        elif node.node_type is NodeType.AGGREGATION_EXPR:
            errors.extend(self._validate_aggregation_expr(node, root_node))
        elif node.node_type is NodeType.FUNCTION_CALL:
            errors.extend(self._validate_function_call(node, root_node))

        return errors

    def _validate_label_matcher(self, node: LabelMatcher, root_node: Optional[VMASTNode]) -> List[ValidationError]:
        """Validate label matcher structure"""
        errors = []

        # Validate label name format
        # Fast path: quick char checks before regex
        n = node.name
        if not n:
            error = self._create_error(
                "Invalid label name '': must match [a-zA-Z_][a-zA-Z0-9_]*",
                node,
                root_node,
                "Label name format validation"
            )
            errors.append(error)
            return errors

        c0 = n[0]
        if not (('A' <= c0 <= 'Z') or ('a' <= c0 <= 'z') or c0 == '_'):
            error = self._create_error(
                f"Invalid label name '{node.name}': must match [a-zA-Z_][a-zA-Z0-9_]*",
                node,
                root_node,
                "Label name format validation"
            )
            errors.append(error)
            return errors

        # Check remaining characters with a compiled regex for correctness
        if not _LABEL_NAME_RE.match(n):
            error = self._create_error(
                f"Invalid label name '{node.name}': must match [a-zA-Z_][a-zA-Z0-9_]*",
                node,
                root_node,
                "Label name format validation"
            )
            errors.append(error)

        return errors

    def _validate_metric_selector(self, node: MetricSelector, root_node: Optional[VMASTNode]) -> List[ValidationError]:
        """Validate metric selector structure"""
        errors = []

        # Validate metric name format
        # Similar fast path as label name
        name = node.metric_name or ""
        has_label_matchers = bool(node.label_matchers)

        # Empty metric name is allowed if there are label matchers (e.g., {job="api"})
        # This is valid PromQL/MetricsQL syntax
        if not name and not has_label_matchers:
            error = self._create_error(
                "Metric selector must have either a metric name or label matchers",
                node,
                root_node,
                "Metric selector validation"
            )
            errors.append(error)
        elif name and not _METRIC_NAME_RE.match(name):
            error = self._create_error(
                f"Invalid metric name '{node.metric_name}': must match [a-zA-Z_:][a-zA-Z0-9_:]*",
                node,
                root_node,
                "Metric name format validation"
            )
            errors.append(error)

        # Validate all label matchers
        for matcher in node.label_matchers or []:
            matcher_errors = self._validate_label_matcher(matcher, root_node)
            errors.extend(matcher_errors)

        return errors

    def _validate_aggregation_expr(self, node: AggregationExpr, root_node: Optional[VMASTNode]) -> List[ValidationError]:
        """Validate aggregation expression structure"""
        errors = []

        # Validate that grouping labels are not duplicated
        if node.grouping and node.grouping.labels:
            if len(node.grouping.labels) != len(set(node.grouping.labels)):
                duplicates = [label for label in node.grouping.labels if node.grouping.labels.count(label) > 1]
                error = self._create_error(
                    f"Duplicate labels in grouping clause: {duplicates}",
                    node,
                    root_node,
                    "Aggregation grouping validation"
                )
                errors.append(error)

        # Validate parameters for specific aggregation functions
        if node.operator.value in ["topk", "bottomk"]:
            if not node.parameter:
                error = self._create_error(
                    f"{node.operator.value} requires a parameter",
                    node,
                    root_node,
                    "Aggregation parameter validation"
                )
                errors.append(error)
                
        return errors

    def _validate_function_call(self, node: FunctionCall, root_node: Optional[VMASTNode]) -> List[ValidationError]:
        """Validate function call parameters"""
        errors = []

        # Define expected argument counts for common functions
        function_args = {
            'rate': (1, 1, "range vector"),
            'increase': (1, 1, "range vector"),
            'sum_over_time': (1, 1, "range vector"),
            'avg_over_time': (1, 1, "range vector"),
            'max_over_time': (1, 1, "range vector"),
            'min_over_time': (1, 1, "range vector"),
            'clamp_min': (2, 2, "vector and scalar"),
            'clamp_max': (2, 2, "vector and scalar"),
            'round': (1, 2, "vector [and scalar]"),
            'histogram_quantile': (2, 2, "quantile and vector"),
        }

        if node.name in function_args:
            min_args, max_args, expected_types = function_args[node.name]
            arg_count = len(node.args)
            
            if arg_count < min_args:
                error = self._create_error(
                    f"Function '{node.name}' requires at least {min_args} arguments, got {arg_count}",
                    node,
                    root_node,
                    f"Expected arguments: {expected_types}"
                )
                errors.append(error)
            elif arg_count > max_args:
                error = self._create_error(
                    f"Function '{node.name}' accepts at most {max_args} arguments, got {arg_count}",
                    node,
                    root_node,
                    f"Expected arguments: {expected_types}"
                )
                errors.append(error)

        return errors


class QueryComplexityValidator(ASTValidator):
    """Validator for query complexity limits to prevent DoS attacks"""

    def __init__(self, max_depth: int = 15, max_functions: int = 100):
        self.max_depth = max_depth
        self.max_functions = max_functions

    def validate(self, node: VMASTNode, root_node: Optional[VMASTNode] = None) -> List[ValidationError]:
        """Validate query complexity limits"""
        errors = []

        # Only validate at root level to avoid duplicate checks
        if root_node is None or node == root_node:
            target_node = node

            # Check AST depth
            depth = self._calculate_depth(target_node)
            if depth > self.max_depth:
                error = self._create_error(
                    f"Query too complex: depth {depth} exceeds limit {self.max_depth}",
                    target_node,
                    target_node,
                    f"Consider simplifying the query. Current depth: {depth}, Maximum: {self.max_depth}"
                )
                errors.append(error)

            # Check function count
            func_count = self._count_functions(target_node)
            if func_count > self.max_functions:
                error = self._create_error(
                    f"Too many functions: {func_count} exceeds limit {self.max_functions}",
                    target_node,
                    target_node,
                    f"Consider reducing function calls. Current count: {func_count}, Maximum: {self.max_functions}"
                )
                errors.append(error)
        
        return errors

    def _calculate_depth(self, node: VMASTNode, current_depth: int = 0) -> int:
        """Calculate AST depth recursively"""
        max_child_depth = current_depth

        if node.node_type is NodeType.BINARY_EXPR:
            left_depth = self._calculate_depth(node.left, current_depth + 1)
            right_depth = self._calculate_depth(node.right, current_depth + 1)
            max_child_depth = max(left_depth, right_depth)
        elif node.node_type is NodeType.AGGREGATION_EXPR:
            expr_depth = self._calculate_depth(node.expr, current_depth + 1)
            max_child_depth = expr_depth
            if node.parameter:
                param_depth = self._calculate_depth(node.parameter, current_depth + 1)
                max_child_depth = max(max_child_depth, param_depth)
        elif node.node_type is NodeType.FUNCTION_CALL:
            for arg in node.args:
                arg_depth = self._calculate_depth(arg, current_depth + 1)
                max_child_depth = max(max_child_depth, arg_depth)

        return max_child_depth

    def _count_functions(self, node: VMASTNode) -> int:
        """Count function calls recursively"""
        count = 0

        if node.node_type is NodeType.FUNCTION_CALL or node.node_type is NodeType.AGGREGATION_EXPR:
            count = 1

        # Recursively count child nodes
        if node.node_type is NodeType.BINARY_EXPR:
            count += self._count_functions(node.left)
            count += self._count_functions(node.right)
        elif node.node_type is NodeType.AGGREGATION_EXPR:
            count += self._count_functions(node.expr)
            if node.parameter:
                count += self._count_functions(node.parameter)
        elif node.node_type is NodeType.FUNCTION_CALL:
            for arg in node.args:
                count += self._count_functions(arg)

        return count


class CompositeASTValidator(ASTValidator):
    """Composite validator that recursively validates entire AST trees"""

    def __init__(self, validators: List[ASTValidator]):
        self.validators = validators

    def validate(self, node: VMASTNode, root_node: Optional[VMASTNode] = None) -> List[ValidationError]:
        """Validate node and all its children recursively"""
        all_errors = []

        # Set root node for the first call
        if root_node is None:
            root_node = node

        # Validate current node with all validators
        for validator in self.validators:
            errors = validator.validate(node, root_node)
            all_errors.extend(errors)

        # Recursively validate child nodes
        all_errors.extend(self._validate_children(node, root_node))

        return all_errors

    def _validate_children(self, node: VMASTNode, root_node: VMASTNode) -> List[ValidationError]:
        """Recursively validate all child nodes"""
        errors = []

        if node.node_type is NodeType.BINARY_EXPR:
            errors.extend(self.validate(node.left, root_node))
            errors.extend(self.validate(node.right, root_node))
        elif node.node_type is NodeType.UNARY_EXPR:
            errors.extend(self.validate(node.operand, root_node))
        elif node.node_type is NodeType.AGGREGATION_EXPR:
            errors.extend(self.validate(node.expr, root_node))
            if node.parameter:
                errors.extend(self.validate(node.parameter, root_node))
        elif node.node_type is NodeType.FUNCTION_CALL:
            for arg in node.args:
                errors.extend(self.validate(arg, root_node))
        elif node.node_type is NodeType.PARENTHESIZED_EXPR:
            errors.extend(self.validate(node.expr, root_node))
        elif node.node_type is NodeType.RANGE_EXPR:
            errors.extend(self.validate(node.expr, root_node))
        elif node.node_type is NodeType.METRIC_SELECTOR:
            # Validate all label matchers
            for matcher in node.label_matchers or []:
                errors.extend(self.validate(matcher, root_node))

        return errors


# Main validation function
def validate_ast_node(node: VMASTNode, root_node: Optional[VMASTNode] = None,
                      enable_complexity_validation: bool = True) -> List[ValidationError]:
    """
    Validate an AST node using structural and complexity validators.

    Args:
        node: AST node to validate
        root_node: Root node for absolute position calculation
        enable_complexity_validation: Whether to run complexity validation to prevent DoS attacks

    Returns:
        List of ValidationError objects with position information
    """
    validators = []

    # Always include structural validation
    validators.append(StructuralASTValidator())

    # Optionally include complexity validation
    if enable_complexity_validation:
        validators.append(QueryComplexityValidator())

    # Use composite validator for complete AST tree validation
    composite_validator = CompositeASTValidator(validators)
    return composite_validator.validate(node, root_node)


# Backward compatibility - keep existing function name
def validate_ast(root_node: VMASTNode) -> List[str]:
    """
    Legacy validation function for backward compatibility.
    Returns string error messages instead of ValidationError objects.
    """
    errors = validate_ast_node(root_node, root_node)
    return [str(error) for error in errors]


def format_validation_errors(errors: List[Union[str, ValidationError]], source_code: Optional[str] = None) -> str:
    """
    Format validation errors into a human-readable string.

    Args:
        errors: List of error messages or ValidationError objects
        source_code: Optional source code for enhanced error display

    Returns:
        Formatted error string
    """
    if not errors:
        return "No validation errors"

    formatted_lines = []
    for i, error in enumerate(errors, 1):
        if isinstance(error, ValidationError):
            if source_code and error.position:
                # Use the enhanced error formatting if source code is available
                if hasattr(error, 'format_error_with_source'):
                    formatted_lines.append(
                        f"Error {i}: {error.format_error_with_source(source_code)}")
                else:
                    # Generate format with offset:length notation for source code context
                    pos_str = f"offset:{error.position.offset},len:{error.position.length}"
                    formatted_lines.append(f"Error {i}: {error.message} Context: at {pos_str}")
            else:
                # Extract short position format from full string representation
                error_str = str(error)
                if error.position:
                    pos_str = f"offset:{error.position.offset},len:{error.position.length}"
                    # Keep the original message and add position format
                    if hasattr(error, 'message'):
                        formatted_lines.append(f"Error {i}: {error.message} {pos_str}")
                    else:
                        formatted_lines.append(f"Error {i}: {error_str} {pos_str}")
                else:
                    formatted_lines.append(f"Error {i}: {error_str}")
        else:
            # String error or other type
            formatted_lines.append(f"Error {i}: {error}")

    return '\n'.join(formatted_lines)


def _is_valid_label_name_fast(name: str) -> bool:
    """Ultra-fast ASCII validation for label names.

    Pattern: [a-zA-Z_][a-zA-Z0-9_]*
    """
    if not name:
        return False
    c0 = name[0]
    if not (('A' <= c0 <= 'Z') or ('a' <= c0 <= 'z') or c0 == '_'):
        return False
    for ch in name[1:]:
        if not (('A' <= ch <= 'Z') or ('a' <= ch <= 'z') or ('0' <= ch <= '9') or ch == '_'):
            return False
    return True


def validate_label_name_string(name: str) -> bool:
    """
    Helper function to validate label name string directly.
    Uses the existing validators internally.

    Args:
        name: Label name to validate

    Returns:
        True if valid

    Raises:
        InvalidParameterError: If label name is invalid
    """

    # Fast path without constructing AST nodes
    if not name:
        raise InvalidParameterError("label_name", name, "non-empty string")

    # Super-fast path: common whitelist
    if name in _COMMON_LABEL_WHITELIST:
        return True

    # Fast path: manual ASCII validation without regex or AST construction
    if _is_valid_label_name_fast(name):
        return True

    # Slow path (rare): Keep error text consistent by delegating to existing logic
    c0 = name[0]
    if not (('A' <= c0 <= 'Z') or ('a' <= c0 <= 'z') or c0 == '_') or not _LABEL_NAME_RE.match(name):
        # Keep error text consistent with tests by delegating to StructuralASTValidator
        validator = StructuralASTValidator()
        temp_matcher = LabelMatcher(name, MatchType.EQUAL, "test_value")
        errors = validator._validate_label_matcher(temp_matcher, None)
    else:
        errors = []

    if errors:
        raise InvalidParameterError("label_name", name, "; ".join(str(error) for error in errors))

    return True



def validate_metric_name_string(name: str) -> bool:
    """
    Helper function to validate metric name string directly.
    
    Args:
        name: Metric name to validate
        
    Returns:
        True if valid
        
    Raises:
        InvalidParameterError: If metric name is invalid
    """
    if not name or not _METRIC_NAME_RE.match(name):
        # Keep error text identical by falling back to existing path
        validator = StructuralASTValidator()
        temp_selector = MetricSelector(name, [])
        errors = validator._validate_metric_selector(temp_selector, None)
    else:
        errors = []

    if errors:
        raise InvalidParameterError("metric_name", name, "; ".join(str(error) for error in errors))

    return True
