"""Dialect markers exposed by the builder; enforcement belongs to Rust."""
from enum import Enum
from typing import Any, Callable, TypeVar


_Method = TypeVar("_Method", bound=Callable[..., Any])


class QueryMode(str, Enum):
    PROMQL = "promql"
    METRICSQL = "metricsql"


def vm_only(method: _Method) -> _Method:
    """Mark a MetricsQL-only operation."""
    setattr(method, "vm_only", True)
    return method


def prom_only(method: _Method) -> _Method:
    """Mark an operation unavailable in the supported MetricsQL baseline."""
    setattr(method, "prom_only", True)
    return method


def prom_experimental(method: _Method) -> _Method:
    """PromQL requires explicit build opt-in and the matching server flag."""
    setattr(method, "prom_experimental", True)
    return method
