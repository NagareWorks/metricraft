"""Tests for MetricsQL-specific AST nodes."""

import pytest
from metricraft._legacy.tree.nodes.metricsql import (
    WithExpr,
    SubqueryExpr,
    RollupConfig,
    KeepMetricNames,
)
from metricraft._legacy.tree.nodes.selectors import MetricSelector
from metricraft._legacy.tree.nodes.literals import DurationLiteral
from metricraft._legacy.tree.nodes.types import NodeType


def test_with_expr_str_and_properties():
    """Test WithExpr __str__ and node properties."""
    defs = {"A": MetricSelector("m1", []), "B": MetricSelector("m2", [])}
    expr = MetricSelector("m3", [])
    with_expr = WithExpr(definitions=defs, expr=expr)
    
    assert with_expr.node_type == NodeType.WITH_EXPR
    assert str(with_expr) == "WithExpr(2 definitions)"
    assert with_expr.definitions == defs
    assert with_expr.expr == expr
    
    # Test position calculation by calling the protected method
    pos = with_expr._calculate_relative_position()
    assert pos is not None


def test_with_expr_single_definition():
    """Test WithExpr with single definition."""
    defs = {"VAR": MetricSelector("metric", [])}
    expr = MetricSelector("result", [])
    with_expr = WithExpr(definitions=defs, expr=expr)
    
    assert str(with_expr) == "WithExpr(1 definitions)"


def test_subquery_expr_with_step():
    """Test SubqueryExpr with step parameter."""
    expr = MetricSelector("cpu", [])
    range_dur = DurationLiteral("5m")
    step = DurationLiteral("1m")
    subquery = SubqueryExpr(expr, range_dur, step)
    
    assert subquery.node_type == NodeType.SUBQUERY_EXPR
    assert str(subquery) == "SubqueryExpr([5m], with step)"
    assert subquery.expr == expr
    assert subquery.range_duration == range_dur
    assert subquery.step == step
    
    # Test position calculation
    pos = subquery._calculate_relative_position()
    assert pos is not None


def test_subquery_expr_without_step():
    """Test SubqueryExpr without step parameter."""
    expr = MetricSelector("memory", [])
    range_dur = DurationLiteral("10m")
    subquery = SubqueryExpr(expr, range_dur)
    
    assert subquery.node_type == NodeType.SUBQUERY_EXPR
    assert str(subquery) == "SubqueryExpr([10m], no step)"
    assert subquery.step is None


def test_rollup_config_str_and_properties():
    """Test RollupConfig __str__ and properties."""
    expr = MetricSelector("requests", [])
    config = {"window": "5m", "step": 60, "lookback": 300.5}
    rollup = RollupConfig(expr, config)
    
    assert rollup.node_type == NodeType.ROLLUP_CONFIG
    assert str(rollup) == "RollupConfig(3 config items)"
    assert rollup.expr == expr
    assert rollup.config == config
    
    # Test position calculation
    pos = rollup._calculate_relative_position()
    assert pos is not None


def test_rollup_config_empty_config():
    """Test RollupConfig with empty config."""
    expr = MetricSelector("metric", [])
    config = {}
    rollup = RollupConfig(expr, config)
    
    assert str(rollup) == "RollupConfig(0 config items)"


def test_rollup_config_single_item():
    """Test RollupConfig with single config item."""
    expr = MetricSelector("metric", [])
    config = {"window": "1h"}
    rollup = RollupConfig(expr, config)
    
    assert str(rollup) == "RollupConfig(1 config items)"


def test_keep_metric_names_str_and_properties():
    """Test KeepMetricNames __str__ and properties."""
    expr = MetricSelector("disk_usage", [])
    keep = KeepMetricNames(expr)
    
    assert keep.node_type == NodeType.KEEP_METRIC_NAMES
    assert str(keep) == "KeepMetricNames(...)"
    assert keep.expr == expr
    
    # Test position calculation
    pos = keep._calculate_relative_position()
    assert pos is not None


def test_metricsql_nodes_accept_visitor():
    """Test that all MetricsQL nodes can accept a visitor."""
    from metricraft._legacy.visitor import QueryToStringVisitor
    
    visitor = QueryToStringVisitor()
    
    # WithExpr
    defs = {"A": MetricSelector("m1", [])}
    with_expr = WithExpr(definitions=defs, expr=MetricSelector("m2", []))
    result = with_expr.accept(visitor)
    assert isinstance(result, str)
    
    # SubqueryExpr
    subquery = SubqueryExpr(MetricSelector("m3", []), DurationLiteral("5m"))
    result = subquery.accept(visitor)
    assert isinstance(result, str)
    
    # RollupConfig
    rollup = RollupConfig(MetricSelector("m4", []), {"k": "v"})
    result = rollup.accept(visitor)
    assert isinstance(result, str)
    
    # KeepMetricNames
    keep = KeepMetricNames(MetricSelector("m5", []))
    result = keep.accept(visitor)
    assert isinstance(result, str)
