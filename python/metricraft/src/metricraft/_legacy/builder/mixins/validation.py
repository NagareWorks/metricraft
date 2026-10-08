"""Validation and debugging mixin for QueryBuilder."""

from typing import Optional

from metricraft._legacy.exceptions import InvalidParameterError, ValidationError
from metricraft._legacy.contracts import ValidationMixinBase
from metricraft._legacy.exceptions import VMInvalidExpressionError as InvalidExpressionError
from metricraft._legacy.tree.nodes.base import VMASTNode
from metricraft._legacy.tree.nodes.types import NodeType
from metricraft._legacy.tree.utils.debug import QueryAnalyzer, ASTDebugger
from metricraft._legacy.tree.utils.validation import validate_ast_node, format_validation_errors
from metricraft._legacy.visitor import get_query_visitor

# MetricsQL constructs that are incompatible with PromQL.  Keeping these
# centralized makes it easy to extend validation when VM-only features grow.
PROMQL_INCOMPATIBLE_LABEL_FUNCTIONS = {
    'label_set', 'label_del', 'label_copy', 'label_move', 'label_transform',
    'label_uppercase', 'label_lowercase',
}
PROMQL_INCOMPATIBLE_OTHER_FUNCTIONS = {
    'alias', 'keep_metric_names', 'union', 'limitk', 'outliersk', 'mad_over_time',
    'mode_over_time', 'rollup', 'rollup_rate', 'rollup_deriv', 'rollup_delta',
    'rollup_increase', 'rollup_candlestick', 'smooth_exponential', 'remove_resets',
    'running_sum', 'running_max', 'running_min', 'running_avg', 'range_over_time',
    'share_le_over_time', 'share_gt_over_time', 'count_le_over_time',
    'count_gt_over_time', 'buckets_limit', 'histogram_avg', 'histogram_stddev',
    'histogram_stdvar', 'prometheus_buckets', 'vmrange_buckets',
    'increases_over_time', 'decreases_over_time', 'sort_by_label', 'sort_by_label_desc',
    'sort_by_label_numeric', 'sort_by_label_numeric_desc',
}
PROMQL_INCOMPATIBLE_FUNCTIONS = (
    PROMQL_INCOMPATIBLE_LABEL_FUNCTIONS | PROMQL_INCOMPATIBLE_OTHER_FUNCTIONS
)
PROMQL_INCOMPATIBLE_MODIFIERS = {' keep_metric_names'}
PROMQL_INCOMPATIBLE_OPERATORS = {' default '}

class ValidationMixin(ValidationMixinBase):
    """
    Mixin providing validation and debugging capabilities for QueryBuilder.

    This mixin handles query validation against different standards and provides
    debugging utilities to inspect the AST structure.
    """

    def validate(self, standard: Optional[str] = None, strict: bool = True) -> str:
        """Validate current expression and return an error string (empty if valid).

        Args:
            standard: Syntax standard: "MetricsQL" or "PromQL". Defaults to the configured provider dialect.
            strict: When True, run AST validation with position-aware errors.

        Returns:
            str: "" if valid; otherwise a formatted error message with caret arrows.

        Raises:
            InvalidParameterError: If standard is not one of {"PromQL","MetricsQL"}.
            InvalidExpressionError: If called without a base expression.
        """
        resolved_standard = self._resolve_validation_standard(standard)

        if self.ast_node is None:
            error = InvalidExpressionError("validate")
            error.set_source_query("<no expression>")
            raise error

        try:
            # Generate source string once for arrow/squiggle rendering
            query_string = get_query_visitor().visit(self.ast_node)

            # Strict AST validation using position-aware errors, formatted with arrows
            if strict:
                errors = validate_ast_node(self.ast_node, self.ast_node)
                if errors:
                    return format_validation_errors(errors, source_code=query_string)

            # PromQL compatibility check with arrow highlighting of offending token
            if resolved_standard == "PromQL":
                promql_error = self._validate_promql_compatibility(query_string)
                if promql_error:
                    return promql_error

            return ""
        except ValidationError as e:
            # Prefer rich formatting with source if available
            try:
                if hasattr(e, 'format_error_with_source'):
                    return e.format_error_with_source(query_string)
            except Exception:
                pass
            return str(e)
        except Exception as e:
            return f"Syntax validation failed: {str(e)}"

    def _resolve_validation_standard(self, explicit: Optional[str]) -> str:
        if explicit is not None:
            if explicit not in ("PromQL", "MetricsQL"):
                raise InvalidParameterError("standard", explicit, "'PromQL' or 'MetricsQL'", "validate")
            return explicit

        inferred = getattr(self, "_default_validation_standard", "MetricsQL")
        if inferred not in ("PromQL", "MetricsQL"):
            return "MetricsQL"
        return inferred

    def _validate_promql_compatibility(self, query_string: str) -> str:
        """Check MetricsQL-only features and render PromQL incompatibilities with arrows."""
        # Helper to render arrow display without AST position
        def _arrow_message(msg: str, start: int, length: int) -> str:
            # Use ValidationError's arrow rendering helper
            ve = ValidationError(message=msg)
            end = max(start + max(1, length), start + 1)
            return ve._create_arrow_display(msg, query_string, start, end)

        for func_name in PROMQL_INCOMPATIBLE_FUNCTIONS:
            needle = func_name + '('
            if needle in query_string:
                pos = query_string.find(needle)
                msg = (
                    f"PromQL compatibility error: MetricsQL-specific function '{func_name}()' is not available in PromQL."
                )
                # Highlight the function name only
                return _arrow_message(msg, pos, len(func_name))

        for modifier in PROMQL_INCOMPATIBLE_MODIFIERS:
            if modifier in query_string:
                pos = query_string.find(modifier)
                # Skip leading space for caret alignment
                start = pos + 1
                mod_name = modifier.strip()
                msg = (
                    f"PromQL compatibility error: MetricsQL-specific modifier '{mod_name}' is not available in PromQL."
                )
                return _arrow_message(msg, start, len(mod_name))

        for operator in PROMQL_INCOMPATIBLE_OPERATORS:
            if operator in query_string:
                pos = query_string.find(operator)
                # Skip leading space for caret alignment
                start = pos + 1
                op_name = operator.strip()
                msg = (
                    f"PromQL compatibility error: MetricsQL-specific operator '{op_name}' is not available in PromQL."
                )
                return _arrow_message(msg, start, len(op_name))

        return ""

    def debug(self) -> str:
        """Return a textual tree representation of the current query's AST."""
        if self.ast_node is None:
            error = InvalidExpressionError("debug")
            error.set_source_query("<no expression>")
            raise error
        return self._format_ast_tree(self.ast_node)

    def _format_ast_tree(self, node: VMASTNode, indent: int = 0) -> str:
        """Format an AST node as a tree with indentation (internal helper)."""
        if node is None:
            return "  " * indent + "<empty>"
        
        prefix = "  " * indent
        node_type = node.node_type

        if node_type is NodeType.METRIC_SELECTOR:
            result = f"{prefix}{node_type}: {node.metric_name or '<no_name>'}"
            if getattr(node, 'label_matchers', None):
                matchers = [f"{m.name}{m.op.value}{m.value}" for m in node.label_matchers]
                result += f" {{{', '.join(matchers)}}}"
        elif node_type in (NodeType.NUMBER_LITERAL, NodeType.STRING_LITERAL, NodeType.DURATION_LITERAL):
            result = f"{prefix}{node_type}: {repr(node.value)}"
        elif node_type is NodeType.BINARY_EXPR:
            operator_str = node.operator.value
            result = f"{prefix}{node_type}: '{operator_str}'"
            if getattr(node, 'return_bool', False):
                result += " (bool)"
            if getattr(node, 'modifier', None):
                result += f" [modifier: {node.modifier}]"
            result += "\n" + self._format_ast_tree(node.left, indent + 1) + "\n" + self._format_ast_tree(node.right, indent + 1)
        elif node_type is NodeType.AGGREGATION_EXPR:
            operator_str = node.operator.value
            result = f"{prefix}{node_type}: {operator_str}()"
            if getattr(node, 'parameter', None):
                result += f" [param: {type(node.parameter).__name__}]"
            if getattr(node, 'grouping', None):
                if node.grouping.is_without:
                    result += f" without ({', '.join(node.grouping.labels)})"
                else:
                    result += f" by ({', '.join(node.grouping.labels)})"
            result += "\n"
            if getattr(node, 'parameter', None):
                result += self._format_ast_tree(node.parameter, indent + 1) + "\n"
            result += self._format_ast_tree(node.expr, indent + 1)
        elif node_type is NodeType.UNARY_EXPR:
            operator_str = node.operator.value
            result = f"{prefix}{node_type}: '{operator_str}'\n" + self._format_ast_tree(node.operand, indent + 1)
        elif node_type is NodeType.FUNCTION_CALL:
            result = f"{prefix}{node_type}: {node.name}()"
            if getattr(node, 'args', None):
                result += f" [{len(node.args)} args]\n" + "\n".join(
                    self._format_ast_tree(arg, indent + 1) for arg in node.args
                )
            else:
                result += " [no args]"
        elif node_type is NodeType.RANGE_EXPR:
            duration_str = self._format_ast_tree(node.range_duration, 0).strip()
            result = f"{prefix}{node_type}: [{duration_str}]\n" + self._format_ast_tree(node.expr, indent + 1)
        elif node_type is NodeType.PARENTHESIZED_EXPR or hasattr(node, 'expr'):
            result = f"{prefix}{node_type}:\n" + self._format_ast_tree(node.expr, indent + 1)
        else:
            result = f"{prefix}{node_type}: {str(node)}"
        return result

    def analyze(self) -> dict:
        """Analyze the current query for patterns and potential issues.

        Returns:
            dict: Analyzer findings (structure may evolve but includes key heuristics).
        """
        if self.ast_node is None:
            error = InvalidExpressionError("analyze")
            error.set_source_query("<no expression>")
            raise error
        analyzer = QueryAnalyzer()
        return analyzer.analyze(self.ast_node)

    def visualize_positions(self, source_code: str) -> str:
        """Visualize node-relative positions overlaid on the source code string."""
        if self.ast_node is None:
            error = InvalidExpressionError("visualize_positions")
            error.set_source_query("<no expression>")
            raise error
        debugger = ASTDebugger()
        return debugger.visualize_positions(self.ast_node, source_code)

    def to_debug_json(self) -> str:
        """Create a JSON blob representing the AST with debug information."""
        if self.ast_node is None:
            error = InvalidExpressionError("to_debug_json")
            error.set_source_query("<no expression>")
            raise error
        debugger = ASTDebugger()
        return debugger.debug_json(self.ast_node)

    def debug_positions(self) -> str:
        """Return human-friendly dump of AST node relative positions."""
        if self.ast_node is None:
            error = InvalidExpressionError("debug_positions")
            error.set_source_query("<no expression>")
            raise error
        debugger = ASTDebugger()
        return debugger.debug_positions(self.ast_node)
