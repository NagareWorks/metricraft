"""Dialect markers exposed by the builder; enforcement belongs to Rust."""
from enum import Enum


class QueryMode(str, Enum):
    PROMQL = "promql"
    METRICSQL = "metricsql"


def vm_only(method):
    """Mark a MetricsQL-only operation."""
    method.vm_only = True
    return method


def prom_only(method):
    """Mark an operation unavailable in the supported MetricsQL baseline."""
    method.prom_only = True
    return method


def prom_experimental(method):
    """PromQL requires explicit build opt-in and the matching server flag."""
    method.prom_experimental = True
    return method
