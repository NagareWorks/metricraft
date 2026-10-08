from enum import Enum


class NodeType(Enum):
	"""Type of AST node."""
	# Expression types
	BINARY_EXPR = "binary_expr"
	UNARY_EXPR = "unary_expr"
	FUNCTION_CALL = "function_call"
	AGGREGATION_EXPR = "aggregation_expr"
	SUBQUERY_EXPR = "subquery_expr"
	PARENTHESIZED_EXPR = "parenthesized_expr"
	RANGE_EXPR = "range_expr"

	# Selector types
	METRIC_SELECTOR = "metric_selector"

	# Literal types
	NUMBER_LITERAL = "number_literal"
	STRING_LITERAL = "string_literal"
	DURATION_LITERAL = "duration_literal"

	# Matching types
	LABEL_MATCHER = "label_matcher"

	# Time/Range types
	OFFSET_EXPR = "offset_expr"
	AT_EXPR = "at_expr"

	# MetricsQL specific types
	WITH_EXPR = "with_expr"
	ROLLUP_CONFIG = "rollup_config"
	KEEP_METRIC_NAMES = "keep_metric_names"

	# Grouping/Modifier types
	GROUP_MODIFIER = "group_modifier"
	BINARY_MODIFIER = "binary_modifier"
