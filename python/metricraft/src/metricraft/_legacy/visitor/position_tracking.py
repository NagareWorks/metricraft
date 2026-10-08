"""
VM-specific AST visitors for position tracking and error reporting.

This module provides visitors that are specific to MetricsQL/VM AST nodes
and are used for error reporting with precise position information.
"""

from metricraft._legacy.ast.visitor import ASTVisitor
from metricraft._legacy.tree.nodes.types import NodeType


class PositionTrackingVisitor(ASTVisitor):
    """
    Visitor for tracking positions of AST nodes in generated query strings.
    Used by PositionalError to calculate absolute positions for arrow display.
    
    This visitor extends the framework ASTVisitor to provide VM-specific
    position tracking for MetricsQL AST nodes.
    """

    def __init__(self):
        self.position_map = {}  # Maps node id -> (start, end) positions
        self.current_position = 0

    def build_position_map(self, root_node) -> dict:
        """
        Build a mapping of AST node IDs to their absolute positions in the generated query.
        
        Args:
            root_node: The root AST node to traverse
            
        Returns:
            Dictionary mapping node id -> (start_position, end_position)
        """
        self.position_map = {}
        self.current_position = 0

        # Generate the query string while tracking positions
        self.visit(root_node)

        return self.position_map

    def visit(self, node) -> str:
        """Visit a node and track its position in the generated string."""
        if node is None:
            return ""

        start_pos = self.current_position

        if node.node_type == NodeType.METRIC_SELECTOR:
            result = self.visit_instant_vector_selector(node)
        elif node.node_type == NodeType.LABEL_MATCHER:
            result = self.visit_label_matcher(node)
        elif node.node_type == NodeType.STRING_LITERAL:
            result = self.visit_string_literal(node)
        elif node.node_type == NodeType.NUMBER_LITERAL:
            result = self.visit_number_literal(node)
        elif node.node_type == NodeType.AGGREGATION_EXPR:
            result = self.visit_aggregation_expr(node)
        elif node.node_type == NodeType.BINARY_EXPR:
            result = self.visit_binary_expr(node)
        else:
            # Default: just return string representation and advance accordingly
            result = str(node)
            self.current_position += len(result)

        end_pos = self.current_position

        # Record the position for this node
        self.position_map[id(node)] = (start_pos, end_pos)

        return result

    def visit_instant_vector_selector(self, node) -> str:
        """Generate string for MetricSelector and track positions."""
        result = ""
        metric = node.metric_name or ""
        result += metric
        self.current_position += len(metric)

        if node.label_matchers:
            result += "{"
            self.current_position += 1

            for i, matcher in enumerate(node.label_matchers):
                if i > 0:
                    result += ", "
                    self.current_position += 2

                matcher_str = self.visit(matcher)
                result += matcher_str

            result += "}"
            self.current_position += 1

        return result

    def visit_label_matcher(self, node) -> str:
        """Generate string for LabelMatcher and track positions."""
        result = ""
        name_op = f'{node.name}{node.op.value}'
        result += name_op
        self.current_position += len(name_op)

        # Handle value with quotes
        result += '"'
        self.current_position += 1

        # Prefer the formal child node if present
        inner = None
        if hasattr(node, 'value_node'):
            inner = node.value_node
        elif hasattr(node, '_value_string_literal'):
            inner = node._value_string_literal
        if inner is not None:
            content_start = self.current_position
            # Map content-only (exclude quotes)
            self.position_map[id(inner)] = (content_start, content_start + len(inner.value))
            result += inner.value
            self.current_position += len(inner.value)
        else:
            result += node.value
            self.current_position += len(node.value)

        result += '"'
        self.current_position += 1

        return result

    def visit_string_literal(self, node) -> str:
        """Generate string for StringLiteral and track positions."""
        text = f'"{node.value}"'
        self.current_position += len(text)
        return text

    def visit_number_literal(self, node) -> str:
        """Generate string for NumberLiteral and track positions."""
        if node.value == int(node.value):
            text = str(int(node.value))
        else:
            text = str(node.value)
        self.current_position += len(text)
        return text

    def visit_aggregation_expr(self, node) -> str:
        """Generate string for AggregationExpr and track positions."""
        result = ""
        head = node.operator.value + "("
        result += head
        self.current_position += len(head)

        expr_str = self.visit(node.expr)
        result += expr_str

        result += ")"
        self.current_position += 1

        # Handle grouping
        if node.grouping and node.grouping.labels:
            by_clause = f" by ({', '.join(node.grouping.labels)})"
            result += by_clause
            self.current_position += len(by_clause)

        return result

    def visit_binary_expr(self, node) -> str:
        """Generate string for BinaryExpr and track positions."""
        result = ""
        left_str = self.visit(node.left)
        result += left_str

        op_str = f" {node.operator.value} "
        result += op_str
        self.current_position += len(op_str)

        right_str = self.visit(node.right)
        result += right_str

        return result

