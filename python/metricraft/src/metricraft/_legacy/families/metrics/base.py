"""Metrics family builder base ABC.

Aggregates all mixin skeletons to provide a single, strongly-typed base for
providers to inherit. This improves IDE type hints and keeps the contract in Core.
"""

from __future__ import annotations

from typing import Optional

from metricraft.enums import DBType
from metricraft._legacy.families.metrics.mixins import (
    FactoryMixinBase,
    SignMixinBase,
    ArithmeticMixinBase,
    ComparisonMixinBase,
    LogicalMixinBase,
    TimeRangeMixinBase,
    RangeVectorFunctionsMixinBase,
    AggregationMixinBase,
    TransformationMixinBase,
    MathematicalMixinBase,
    ValidationMixinBase,
)
from metricraft._legacy.query_base import QueryBuilder


class MetricsBuilderBase(
    FactoryMixinBase,
    SignMixinBase,
    ArithmeticMixinBase,
    ComparisonMixinBase,
    LogicalMixinBase,
    TimeRangeMixinBase,
    RangeVectorFunctionsMixinBase,
    AggregationMixinBase,
    TransformationMixinBase,
    MathematicalMixinBase,
    ValidationMixinBase,
    QueryBuilder,
):
    """Abstract base that aggregates all Metrics-family mixin ABCs.

    Providers (e.g., VM/Prometheus) should inherit this base for their builder
    implementations to benefit from strong typing across all chained methods
    and operator overloads defined in mixin skeletons.
    """
