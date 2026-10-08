"""VM-specific AST public API.

This package aggregates MetricsQL AST nodes and utilities under
`metricraft._legacy.tree`.
"""

from .nodes.base import VMASTNode
from .nodes.literals import NumberLiteral, StringLiteral, DurationLiteral
from .nodes.expressions import (
    BinaryOperator,
    UnaryOperator,
    AggregationOperator,
    GroupModifier,
    RangeExpr,
    BinaryModifier,
    BinaryExpr,
    UnaryExpr,
    FunctionCall,
    AggregationExpr,
    ParenthesizedExpr,
)
from .nodes.selectors import (
    LabelMatcher,
    MatchType,
    MetricSelector,
    OffsetExpr,
    AtExpr,
)
from .nodes.metricsql import (
    WithExpr,
    SubqueryExpr,
    RollupConfig,
    KeepMetricNames,
)
from .nodes.types import NodeType

__all__ = [
    # Base
    "VMASTNode",
    "NodeType",
    # Literals
    "NumberLiteral",
    "StringLiteral",
    "DurationLiteral",
    # Selectors
    "LabelMatcher",
    "MatchType",
    "MetricSelector",
    "OffsetExpr",
    "AtExpr",
    # Expressions
    "BinaryOperator",
    "UnaryOperator",
    "AggregationOperator",
    "GroupModifier",
    "BinaryModifier",
    "BinaryExpr",
    "UnaryExpr",
    "FunctionCall",
    "AggregationExpr",
    "ParenthesizedExpr",
    "RangeExpr",
    # MetricsQL specific
    "WithExpr",
    "SubqueryExpr",
    "RollupConfig",
    "KeepMetricNames",
]
