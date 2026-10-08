"""
VM-specific visitor base classes and implementations.

This module provides the BaseVisitor implementation for MetricsQL/PromQL
AST nodes with concrete dispatching logic.
"""

from abc import abstractmethod
from typing import TypeVar, Generic

from metricraft._legacy.ast.visitor import ASTVisitor
from metricraft._legacy.ast.astnode import ASTNode

T = TypeVar('T')


class BaseVisitor(ASTVisitor, Generic[T]):
    """
    Base visitor implementation for MetricsQL/PromQL AST nodes.
    
    Provides concrete dispatching logic based on node types and
    default visit methods that can be overridden by subclasses.
    """

    @abstractmethod  
    def visit(self, node: ASTNode) -> T:
        """
        Visit an AST node by dispatching to the appropriate visit_* method.
        
        Concrete implementations should override this method to provide
        type-specific dispatching logic.
        """
        pass
    
    # Default implementations for all node types
    def visit_number_literal(self, node) -> T:
        return self.default_visit(node)

    def visit_string_literal(self, node) -> T:
        return self.default_visit(node)

    def visit_duration_literal(self, node) -> T:
        return self.default_visit(node)

    def visit_label_matcher(self, node) -> T:
        return self.default_visit(node)

    def visit_metric_selector(self, node) -> T:
        return self.default_visit(node)
        
    def visit_instant_vector_selector(self, node) -> T:
        return self.default_visit(node)

    def visit_offset_expr(self, node) -> T:
        return self.default_visit(node)

    def visit_at_expr(self, node) -> T:
        return self.default_visit(node)

    def visit_binary_expr(self, node) -> T:
        return self.default_visit(node)

    def visit_unary_expr(self, node) -> T:
        return self.default_visit(node)

    def visit_function_call(self, node) -> T:
        return self.default_visit(node)

    def visit_aggregation_expr(self, node) -> T:
        return self.default_visit(node)

    def visit_parenthesized_expr(self, node) -> T:
        return self.default_visit(node)

    def visit_range_expr(self, node) -> T:
        return self.default_visit(node)

    def visit_group_modifier(self, node) -> T:
        return self.default_visit(node)

    def visit_binary_modifier(self, node) -> T:
        return self.default_visit(node)

    def visit_with_expr(self, node) -> T:
        return self.default_visit(node)

    def visit_subquery_expr(self, node) -> T:
        return self.default_visit(node)

    def visit_rollup_config(self, node) -> T:
        return self.default_visit(node)

    def visit_keep_metric_names(self, node) -> T:
        return self.default_visit(node)

    def default_visit(self, node) -> T:
        """
        Default visit method called when no specific visitor is implemented.
        
        Override this method to provide default behavior for all node types.
        """
        raise NotImplementedError(
            f"No visit method implemented for {type(node).__name__}")
