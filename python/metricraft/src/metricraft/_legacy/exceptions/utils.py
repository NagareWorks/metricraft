"""
Exception utilities and helper functions.

This module provides utilities for creating, validating, and handling exceptions
throughout the MetriCraft framework. These functions are framework-agnostic
and can be used with any exception types.
"""

from typing import Optional, Any, List, Union, Callable
import re
from .builder import InvalidParameterError, ValidationError, PositionalError


# Validation functions
def validate_parameter(
        parameter: str,
        value: Any,
        validator: Union[type, tuple, Callable],
        method: Optional[str] = None,
        custom_message: Optional[str] = None
) -> None:
    """
    Validate a parameter value and raise InvalidParameterError if invalid.

    Args:
        parameter: The parameter name.
        value: The parameter value to validate.
        validator: Type, tuple of types, or callable for validation.
        method: Optional method name for context.
        custom_message: Optional custom error message.

    Raises:
        InvalidParameterError: If validation fails.
    """
    if callable(validator) and not isinstance(validator, type):
        # Custom validator function
        try:
            if not validator(value):
                message = custom_message or f"Value failed custom validation"
                raise InvalidParameterError(parameter, value, message, method)
        except Exception as e:
            message = custom_message or f"Validation error: {e}"
            raise InvalidParameterError(parameter, value, message, method)
    elif isinstance(validator, (type, tuple)):
        # Type validation
        if not isinstance(value, validator):
            expected = getattr(validator, '__name__', str(validator))
            raise InvalidParameterError(parameter, value, expected, method)


def validate_numeric_range(
        parameter: str,
        value: Union[int, float],
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None,
        method: Optional[str] = None
) -> None:
    """
    Validate that a numeric value is within a specified range.

    Args:
        parameter: The parameter name.
        value: The numeric value to validate.
        min_value: Optional minimum value (inclusive).
        max_value: Optional maximum value (inclusive).
        method: Optional method name for context.

    Raises:
        InvalidParameterError: If value is outside the valid range.
    """
    if not isinstance(value, (int, float)):
        raise InvalidParameterError(parameter, value, "numeric value", method)

    if min_value is not None and value < min_value:
        expected = f"value >= {min_value}"
        if max_value is not None:
            expected += f" and <= {max_value}"
        raise InvalidParameterError(parameter, value, expected, method)

    if max_value is not None and value > max_value:
        expected = f"value <= {max_value}"
        if min_value is not None:
            expected = f"value >= {min_value} and " + expected
        raise InvalidParameterError(parameter, value, expected, method)


def validate_labels(labels: List[str], method: Optional[str] = None) -> None:
    """
    Validate that a list of labels is valid.

    Args:
        labels: List of label names to validate.
        method: Optional method name for context.

    Raises:
        InvalidParameterError: If labels are invalid.
    """
    if not isinstance(labels, list):
        raise InvalidParameterError(
            "labels", labels, "list of strings", method)

    if not labels:
        raise InvalidParameterError(
            "labels", labels, "non-empty list of strings", method)

    for i, label in enumerate(labels):
        if not isinstance(label, str):
            raise InvalidParameterError(
                f"labels[{i}]", label, "string", method)

        if not label.strip():
            raise InvalidParameterError(
                f"labels[{i}]", label, "non-empty string", method)


def validate_duration(duration: str, method: Optional[str] = None) -> None:
    """
    Validate that a duration string is valid.

    Args:
        duration: Duration string to validate (e.g., "5m", "1h").
        method: Optional method name for context.

    Raises:
        InvalidParameterError: If duration format is invalid.
    """
    if not isinstance(duration, str):
        raise InvalidParameterError("duration", duration, "string", method)

    # Basic duration pattern validation
    pattern = r'^(\d+[smhdwy])+$'
    if not re.match(pattern, duration.strip()):
        expected = "duration string like '5m', '1h', '30s' or '1h30m'"
        raise InvalidParameterError("duration", duration, expected, method)


# Exception creation utilities  
def create_positioned_error(
        error_class: type,
        message: str,
        ast_node: Optional[Any] = None,
        root_node: Optional[Any] = None,
        **kwargs) -> Any:
    """
    Create a positioned error with automatic position extraction from AST node.
    
    Args:
        error_class: The error class to instantiate
        message: Error message
        ast_node: AST node where the error occurred
        root_node: Root node for absolute position calculation
        **kwargs: Additional keyword arguments for the error class
        
    Returns:
        An instance of the specified error class with position information
    """
    from .builder import ValidationError
    
    position = None
    node_type = None

    if ast_node and hasattr(ast_node, 'pos'):
        position = ast_node.pos
    if ast_node and hasattr(ast_node, 'node_type'):
        node_type = ast_node.node_type.value if hasattr(ast_node.node_type, 'value') else str(ast_node.node_type)

    # Add position-related kwargs
    kwargs.update({
        'position': position,
        'node_type': node_type,
        'ast_node': ast_node,
        'root_node': root_node
    })

    # Handle ValidationError specially since it expects different parameter order
    if error_class == ValidationError:
        kwargs['message'] = message
        # Remove parameters that ValidationError doesn't accept directly
        kwargs.pop('position', None)
        kwargs.pop('node_type', None)
        return error_class(**kwargs)
    else:
        return error_class(message, **kwargs)


def create_validation_error_with_position(
        message: str,
        ast_node: Optional[Any] = None,
        root_node: Optional[Any] = None,
        validation_type: str = "AST",
        **kwargs) -> Any:
    """
    Create a ValidationError with position information from AST node.
    
    Args:
        message: Error message
        ast_node: AST node where the error occurred
        root_node: Root node for absolute position calculation
        validation_type: Type of validation that failed
        **kwargs: Additional keyword arguments
        
    Returns:
        ValidationError with position information
    """
    kwargs['validation_type'] = validation_type
    return create_positioned_error(
        ValidationError,
        message,
        ast_node=ast_node,
        root_node=root_node,
        **kwargs
    )


def create_error_with_source(
        error_class: type,
        message: str,
        source_query: str,
        ast_node: Optional[Any] = None,
        **kwargs) -> Any:
    """
    Create a positioned error with automatic source query formatting.
    
    Args:
        error_class: The error class to instantiate
        message: Error message
        source_query: The source query where the error occurred
        ast_node: AST node where the error occurred (position extracted automatically)
        **kwargs: Additional keyword arguments
        
    Returns:
        Error instance with automatic arrow display
    """
    error = error_class(message, ast_node=ast_node, **kwargs)
    if hasattr(error, 'set_source_query'):
        error.set_source_query(source_query)
    return error


def create_validation_error_with_source(
        message: str,
        source_query: str,
        ast_node: Optional[Any] = None,
        **kwargs) -> Any:
    """
    Create a validation error that automatically shows arrows pointing to the error location.
    
    Args:
        message: Error message
        source_query: The source query string
        ast_node: AST node where the error occurred (position extracted automatically)
        **kwargs: Additional keyword arguments
        
    Returns:
        ValidationError with automatic position arrows
    """
    error = ValidationError(message=message, ast_node=ast_node, **kwargs)
    error.set_source_query(source_query)
    return error


# Convenience functions for common error scenarios
def require_expression(operation: str) -> None:
    """
    Raise InvalidExpressionError for operations requiring a base expression.

    Args:
        operation: The name of the operation being attempted.

    Raises:
        InvalidExpressionError: Always raised.
    """
    # Note: This should be implemented by specific implementations
    # For now, use the base PositionalError
    raise PositionalError(f"Cannot perform '{operation}' without a base expression.")
