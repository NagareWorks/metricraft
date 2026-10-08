"""
Custom exceptions for the MetricsQL Query Builder.

This module defines custom exception classes to provide more specific
error handling and better error messages for different types of failures.

These are framework-level exceptions that should not contain implementation-specific logic.
"""

from __future__ import annotations

from typing import Optional, Any

# Historical position-aware errors also accept application-defined node objects.
ASTNode = Any


class QueryBuilderError(Exception):
    """
    Base exception class for all QueryBuilder errors.

    All custom exceptions in the QueryBuilder library inherit from this class,
    making it easy to catch all QueryBuilder-related errors.
    """

    def __init__(self, message: str, context: Optional[str] = None):
        self.message = message
        self.context = context
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format the error message with optional context."""
        if self.context:
            return f"{self.message} Context: {self.context}"
        return self.message


class PositionalError(QueryBuilderError):
    """
    Base class for errors that include position information.
    
    This is a framework-level base class that provides the interface for
    position-aware errors. Concrete implementations should be provided
    in specific database implementations (e.g., VM module).
    
    All position information is automatically extracted from the provided AST node.
    """

    def __init__(
            self,
            message: str,
            ast_node: Optional['ASTNode'] = None,
            root_node: Optional['ASTNode'] = None,
            context: Optional[str] = None):
        self.ast_node = ast_node  # Node where the error occurred
        self.root_node = root_node  # Root node for absolute position calculation

        # Extract position and node type from AST node
        self.position = ast_node.pos if ast_node else None
        self.node_type = ast_node.__class__.__name__ if ast_node else None

        # Build enhanced context with position info
        context_parts = []
        if context:
            context_parts.append(context)
        # Prefer absolute character offsets if computable; avoid showing internal relative positions
        try:
            if self.ast_node is not None and self.root_node is not None:
                abs_pos = self.calculate_absolute_position()
            else:
                abs_pos = None
        except Exception:
            abs_pos = None

        if abs_pos:
            start, end = abs_pos
            # Display as character range; do not include internal RelPos structure
            context_parts.append(f"at chars {start}-{max(start, end - 1)}")
        if self.node_type:
            context_parts.append(f"in {self.node_type}")

        enhanced_context = ", ".join(context_parts) if context_parts else None
        super().__init__(message, enhanced_context)

        # Store source query for automatic error formatting
        self._source_query = None

    def set_source_query(self, source_query: str) -> 'PositionalError':
        """
        Set the source query for automatic error formatting.
        
        Args:
            source_query: The source query string
            
        Returns:
            Self for method chaining
        """
        self._source_query = source_query
        return self

    def __str__(self) -> str:
        """Override to automatically include position arrows when available."""
        base_message = super().__str__()

        # If we have source query, automatically try to format with position arrows
        # Don't require self.position; we'll compute absolute positions if possible.
        if self._source_query:
            try:
                return self._format_error_with_arrows(base_message, self._source_query)
            except Exception:
                pass  # Fall back to base message if formatting fails

        return base_message

    def get_position_info(self) -> Optional[dict]:
        """Get position information as a dictionary."""
        if self.position:
            # New Position structure with relative coordinates
            return {
                'offset': self.position.offset,
                'length': self.position.length,
                'index_in_parent': self.position.index_in_parent,
                'node_type': self.position.node_type
            }
        return None

    def calculate_absolute_position(self) -> Optional[tuple[int, int]]:
        """
        Calculate absolute position in the generated query string.
        
        This is a framework-level method that should be overridden by
        concrete implementations in specific database implementations.
        
        Returns:
            Tuple of (start, end) absolute positions, or None if calculation fails
        """
        # Framework base implementation - should be overridden
        return None

    def _calculate_label_value_position(self) -> Optional[tuple[int, int]]:
        """
        Calculate position for a label value in validation context.
        
        This is a framework-level method that should be overridden by
        concrete implementations in specific database implementations.
        """
        # Framework base implementation - should be overridden
        return None

    def format_error_with_source(self, source_query: str) -> str:
        """
        Format error message with source context if position is available.
        
        Args:
            source_query: The original query string
            
        Returns:
            Formatted error message with source context and error pointer
        """
        base_message = str(self)

        if not source_query:
            return base_message

        # Try to get absolute position from the implementation
        abs_position = self.calculate_absolute_position()
        if abs_position:
            start, end = abs_position
            if 0 <= start < len(source_query):
                # Find the line and column for the error position
                lines = source_query.split('\n')
                char_count = 0
                error_line_num = 0
                error_col = start

                for i, line in enumerate(lines):
                    if char_count + len(line) >= start:
                        error_line_num = i
                        error_col = start - char_count
                        break
                    char_count += len(line) + 1  # +1 for newline

                if error_line_num < len(lines):
                    error_line = lines[error_line_num]

                    # Create pointer to error position
                    length = min(end - start, len(error_line) - error_col)
                    pointer = ' ' * error_col + '^'
                    if length > 1:
                        pointer += '~' * (length - 1)

                    return f"{base_message}\n\nLine {error_line_num + 1}:\n{error_line}\n{pointer}"

        # Fallback: show absolute character offsets if available; otherwise do not show internal RelPos
        abs_position = self.calculate_absolute_position()
        if abs_position is not None:
            start, end = abs_position
            return f"{base_message}\n\nAbsolute position: chars {start}-{max(start, end - 1)}"

        return base_message

    def _format_error_with_arrows(self, base_message: str, source_query: str) -> str:
        """
        Format error message with arrows pointing to error location.
        
        Args:
            base_message: The base error message
            source_query: The source query string
            
        Returns:
            Formatted error message with position arrows
        """
        if not self.position or not source_query:
            return base_message

        # Try absolute position calculation first
        abs_position = self.calculate_absolute_position()
        if abs_position:
            start, end = abs_position
            return self._create_arrow_display(base_message, source_query, start, end)

        # Fallback: use relative position as rough estimate
        # This assumes the position offset is roughly the character position in the query
        offset = self.position.offset
        length = max(1, self.position.length)

        if 0 <= offset < len(source_query):
            return self._create_arrow_display(base_message, source_query, offset, offset + length)

        return base_message

    def _create_arrow_display(self, base_message: str, source_query: str, start: int, end: int) -> str:
        """
        Create arrow display pointing to error location in source query.
        
        Args:
            base_message: The base error message
            source_query: The source query string
            start: Start position of error
            end: End position of error
            
        Returns:
            Formatted message with arrow display
        """
        if start < 0 or start >= len(source_query):
            return base_message

        # Find the line and column for the error position
        lines = source_query.split('\n')
        char_count = 0
        error_line_num = 0
        error_col = start

        for i, line in enumerate(lines):
            if char_count + len(line) >= start:
                error_line_num = i
                error_col = start - char_count
                break
            char_count += len(line) + 1  # +1 for newline

        if error_line_num < len(lines):
            error_line = lines[error_line_num]

            # Create pointer to error position
            length = min(end - start, len(error_line) - error_col)
            pointer = ' ' * error_col + '^'
            if length > 1:
                pointer += '~' * (length - 1)

            # Multi-line format with clear separation
            return f"{base_message}\n\n{'=' * 50}\nError location in query:\n\nLine {error_line_num + 1}: {error_line}\n{' ' * 8}{pointer}\n{'=' * 50}"
            
        return base_message


class InvalidParameterError(QueryBuilderError):
    """
    Raised when invalid parameters are passed to QueryBuilder methods.

    This includes type errors, value out of range errors, and parameter
    combination errors.
    """

    def __init__(
            self,
            parameter: str,
            value: Any,
            expected: str,
            method: Optional[str] = None):
        message = f"Invalid parameter '{parameter}': {repr(value)}. Expected: {expected}."
        context = f"Parameter: {parameter}, Value: {repr(value)}"
        if method:
            context += f", Method: {method}"
        super().__init__(message, context)


class UnsupportedOperationError(QueryBuilderError):
    """
    Raised when attempting an operation that is not supported.

    This includes operations that are not available for certain expression types
    or operations that are not supported in certain contexts.
    """

    def __init__(
            self,
            operation: str,
            expression_type: str,
            reason: Optional[str] = None):
        message = f"Operation '{operation}' is not supported for {expression_type} expressions."
        if reason:
            message += f" Reason: {reason}"
        super().__init__(
            message,
            f"Operation: {operation}, Expression type: {expression_type}")


class RangeVectorError(QueryBuilderError):
    """
    Raised when there are issues with range vector operations.

    This includes failures to create range vectors or invalid duration specifications.
    """

    def __init__(
            self,
            operation: str,
            duration: Optional[str] = None,
            reason: Optional[str] = None):
        message = f"Range vector operation '{operation}' failed."
        if reason:
            message += f" {reason}"
        context_parts = [f"Operation: {operation}"]
        if duration:
            context_parts.append(f"Duration: {duration}")
        super().__init__(message, ", ".join(context_parts))


class AggregationError(QueryBuilderError):
    """
    Raised when there are issues with aggregation operations.

    This includes invalid grouping specifications or operations that
    cannot be applied to certain expression types.
    """

    def __init__(self, operation: str, issue: str,
                 suggestion: Optional[str] = None):
        message = f"Aggregation operation '{operation}' failed: {issue}"
        if suggestion:
            message += f" Suggestion: {suggestion}"
        super().__init__(message, f"Operation: {operation}")


class ValidationError(PositionalError):
    """
    Raised when query validation fails.

    This includes standard compliance errors (PromQL vs MetricsQL)
    and other validation issues. Framework-level base class that should
    be extended by specific implementations.
    """

    def __init__(
            self,
            validation_type: Optional[str] = None,
            issue: Optional[str] = None,
            standard: Optional[str] = None,
            message: Optional[str] = None,
            ast_node: Optional['ASTNode'] = None,
            root_node: Optional['ASTNode'] = None,
            context: Optional[str] = None):

        # Support new message-based constructor
        if message is not None:
            actual_message = message
            # Only use context if explicitly provided
            actual_context = context
        else:
            # Support legacy constructor
            actual_message = f"{validation_type} validation failed: {issue}"
            context_parts = [f"Validation type: {validation_type}"]
            if standard:
                context_parts.append(f"Standard: {standard}")
            actual_context = ", ".join(context_parts)

        super().__init__(actual_message, ast_node=ast_node, root_node=root_node,
                         context=actual_context)
        self.context = actual_context
        self.validation_type = validation_type
        self.issue = issue
        self.standard = standard
