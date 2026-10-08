"""VM builder implementation package.

This package exposes the concrete MetricsQL builder implementations used by the
active provider. Public API is stable across internal refactors.
"""

from .base import MetricsBuilder
from .instant_vector import InstantVectorBuilder
from .range_vector import RangeVectorBuilder
from .scalar import ScalarBuilder
from .processed_vector import ProcessedVectorBuilder
from .types import BuilderType
from .register import BuilderRegister

__all__ = [
    "MetricsBuilder",
    "InstantVectorBuilder",
    "RangeVectorBuilder",
    "ScalarBuilder",
    "ProcessedVectorBuilder",
    "BuilderType",
    "BuilderRegister",
]