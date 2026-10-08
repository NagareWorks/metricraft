from metricraft._legacy.ast.astnode import ASTNode
from metricraft._legacy.tree.nodes.types import NodeType
from metricraft._legacy.visitor import BaseVisitor


class QueryToStringVisitor(BaseVisitor[str]):
    """
    Visitor that converts AST nodes to MetricsQL query strings.

    This visitor traverses the AST and generates the corresponding
    MetricsQL/PromQL query string representation.
    """

    def visit(self, node: ASTNode) -> str:
        """
        Visit an AST node by dispatching based on its node_type.
        
        Uses node_type enum to determine the correct visit_* method to call,
        avoiding circular imports and improving performance.
        """
        if node is None:
            return ""
        
        # Dispatch based on node_type enum
        if node.node_type == NodeType.NUMBER_LITERAL:
            return self.visit_number_literal(node)
        elif node.node_type == NodeType.STRING_LITERAL:
            return self.visit_string_literal(node)
        elif node.node_type == NodeType.DURATION_LITERAL:
            return self.visit_duration_literal(node)
        elif node.node_type == NodeType.LABEL_MATCHER:
            return self.visit_label_matcher(node)
        elif node.node_type == NodeType.METRIC_SELECTOR:
            return self.visit_metric_selector(node)
        elif node.node_type == NodeType.OFFSET_EXPR:
            return self.visit_offset_expr(node)
        elif node.node_type == NodeType.AT_EXPR:
            return self.visit_at_expr(node)
        elif node.node_type == NodeType.BINARY_EXPR:
            return self.visit_binary_expr(node)
        elif node.node_type == NodeType.UNARY_EXPR:
            return self.visit_unary_expr(node)
        elif node.node_type == NodeType.FUNCTION_CALL:
            return self.visit_function_call(node)
        elif node.node_type == NodeType.AGGREGATION_EXPR:
            return self.visit_aggregation_expr(node)
        elif node.node_type == NodeType.PARENTHESIZED_EXPR:
            return self.visit_parenthesized_expr(node)
        elif node.node_type == NodeType.RANGE_EXPR:
            return self.visit_range_expr(node)
        elif node.node_type == NodeType.GROUP_MODIFIER:
            return self.visit_group_modifier(node)
        elif node.node_type == NodeType.BINARY_MODIFIER:
            return self.visit_binary_modifier(node)
        elif node.node_type == NodeType.WITH_EXPR:
            return self.visit_with_expr(node)
        elif node.node_type == NodeType.SUBQUERY_EXPR:
            return self.visit_subquery_expr(node)
        elif node.node_type == NodeType.ROLLUP_CONFIG:
            return self.visit_rollup_config(node)
        elif node.node_type == NodeType.KEEP_METRIC_NAMES:
            return self.visit_keep_metric_names(node)
        else:
            # Fallback to default visit for unknown types
            return self.default_visit(node)

    def visit_number_literal(self, node: ASTNode) -> str:
        # Handle integer vs float display
        if node.value == int(node.value):
            return str(int(node.value))
        return str(node.value)

    def visit_string_literal(self, node: ASTNode) -> str:
        # Need to escape newlines, tabs, and other special characters too
        value = node.value
        value = value.replace('\\', '\\\\')  # Escape backslashes first
        value = value.replace('"', '\\"')  # Escape quotes
        value = value.replace('\n', '\\n')  # Escape newlines
        value = value.replace('\t', '\\t')  # Escape tabs
        value = value.replace('\r', '\\r')  # Escape carriage returns
        return f'"{value}"'

    def visit_duration_literal(self, node: ASTNode) -> str:
        return node.value

    def visit_label_matcher(self, node: ASTNode) -> str:
        # Need to escape newlines, tabs, and other special characters too
        value = node.value
        value = value.replace('\\', '\\\\')  # Escape backslashes first
        value = value.replace('"', '\\"')  # Escape quotes
        value = value.replace('\n', '\\n')  # Escape newlines
        value = value.replace('\t', '\\t')  # Escape tabs
        value = value.replace('\r', '\\r')  # Escape carriage returns
        return f'{node.name}{node.op.value}"{value}"'

    def visit_metric_selector(self, node: ASTNode) -> str:
        parts = []
        if node.metric_name:
            parts.append(node.metric_name)

        if node.label_matchers:
            matcher_strs = [self.visit(matcher)
                            for matcher in node.label_matchers]
            parts.append("{" + ", ".join(matcher_strs) + "}")
        elif not node.metric_name:
            parts.append("{}")

        return "".join(parts)

    def visit_offset_expr(self, node: ASTNode) -> str:
        return f"{self.visit(node.expr)} offset {self.visit(node.offset)}"

    def visit_at_expr(self, node: ASTNode) -> str:
        if isinstance(node.timestamp, str):
            return f"{self.visit(node.expr)} @ {node.timestamp}"
        return f"{self.visit(node.expr)} @ {node.timestamp}"

    def visit_group_modifier(self, node: ASTNode) -> str:
        keyword = "without" if node.is_without else "by"
        labels_str = ", ".join(node.labels)
        return f"{keyword} ({labels_str})"

    def visit_binary_modifier(self, node: ASTNode) -> str:
        parts = []

        if node.matching_type and node.labels:
            labels_str = ", ".join(node.labels)
            parts.append(f"{node.matching_type} ({labels_str})")

        if node.group_type:
            if node.group_labels:
                group_labels_str = ", ".join(node.group_labels)
                parts.append(f"{node.group_type}({group_labels_str})")
            else:
                parts.append(f"{node.group_type}()")

        return " ".join(parts)

    def visit_binary_expr(self, node: ASTNode) -> str:
        left_str = self.visit(node.left)
        right_str = self.visit(node.right)

        result = f"{left_str} {node.operator.value} {right_str}"

        if node.modifier:
            if isinstance(node.modifier, str):
                result += f" {node.modifier}"
            else:
                result += f" {self.visit(node.modifier)}"
        if node.return_bool:
            result += " bool"

        return result

    def visit_unary_expr(self, node: ASTNode) -> str:
        operand_str = self.visit(node.operand)
        return f"{node.operator.value}{operand_str}"

    def visit_function_call(self, node: ASTNode) -> str:
        args_parts = []
        for arg in node.args:
            try:
                if hasattr(arg, 'accept'):
                    # Real AST node
                    result = self.visit(arg)
                    # Ensure result is always a string
                    args_parts.append(str(result))
                else:
                    # Fallback for Mock objects or other non-AST objects
                    args_parts.append(str(arg))
            except Exception:
                # Last resort: just convert to string
                args_parts.append(str(arg))

        args_str = ", ".join(args_parts)
        return f"{node.name}({args_str})"

    def visit_aggregation_expr(self, node: ASTNode) -> str:
        if node.parameter:
            result = f"{node.operator.value}({self.visit(node.parameter)}, {self.visit(node.expr)})"
        else:
            result = f"{node.operator.value}({self.visit(node.expr)})"

        if node.grouping:
            result += f" {self.visit(node.grouping)}"

        return result

    def visit_parenthesized_expr(self, node: ASTNode) -> str:
        return f"({self.visit(node.expr)})"

    def visit_range_expr(self, node: ASTNode) -> str:
        # Only add parentheses for complex expressions
        if node.expr is None:
            expr_str = "<missing-expr>"
        else:
            result = self.visit(node.expr)
            expr_str = str(result) if result is not None else "<null-expr>"

        # Simple expressions don't need parentheses
        if node.expr and node.expr.node_type in (
                NodeType.METRIC_SELECTOR,
                NodeType.NUMBER_LITERAL,
                NodeType.STRING_LITERAL):
            return f"{expr_str}[{self.visit(node.range_duration)}]"
        else:
            # Complex expressions need parentheses
            return f"({expr_str})[{self.visit(node.range_duration)}]"

    def visit_with_expr(self, node: ASTNode) -> str:
        def_strs = [f"{name} = {self.visit(expr)}" for name, expr in node.definitions.items()]
        defs = ", ".join(def_strs)
        return f"WITH ({defs}) {self.visit(node.expr)}"

    def visit_subquery_expr(self, node: ASTNode) -> str:
        if node.step:
            return f"{self.visit(node.expr)}[{self.visit(node.range_duration)}:{self.visit(node.step)}]"
        return f"{self.visit(node.expr)}[{self.visit(node.range_duration)}:]"

    def visit_rollup_config(self, node: ASTNode) -> str:
        config_strs = [f'{k}="{v}"' for k, v in node.config.items()]
        config_str = ", ".join(config_strs)
        return f"{self.visit(node.expr)} @ rollup_config{{{config_str}}}"

    def visit_keep_metric_names(self, node: ASTNode) -> str:
        return f"{self.visit(node.expr)} keep_metric_names"

    def default_visit(self, node: ASTNode) -> str:
        # Fallback for any unhandled nodes
        return f"<{type(node).__name__}>"
