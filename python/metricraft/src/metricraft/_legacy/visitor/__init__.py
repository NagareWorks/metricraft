"""
VM visitor implementations.

This package contains concrete implementations of AST visitors for the VM,
including the BaseVisitor class with MetricsQL-specific dispatching logic.
"""

from functools import lru_cache
from .base import BaseVisitor
from .code_gen import QueryToStringVisitor
from .position_tracking import PositionTrackingVisitor


@lru_cache(maxsize=1)
def get_query_visitor() -> QueryToStringVisitor:
	"""Get a cached instance of QueryToStringVisitor."""
	return QueryToStringVisitor()

__all__ = [
    "BaseVisitor",
    "QueryToStringVisitor",
    "PositionTrackingVisitor",
    "get_query_visitor",
]
