"""Public immutable builder composed from stateless operation groups."""
from __future__ import annotations

from ._expression import Expression
from ._types import ScalarInput
from .aggregation import AggregationMixin
from .diagnostics import DiagnosticMixin
from .extended_rollups import ExtendedRollupMixin
from .functions import FunctionMixin
from .labels import LabelMixin
from .operators import OperatorMixin
from .rollups import RollupMixin
from .selectors import SelectorMixin
from .templates import TemplateMixin
from .temporal import TemporalMixin
from .transforms import TransformMixin


class QueryBuilder(
    AggregationMixin, DiagnosticMixin, FunctionMixin, OperatorMixin,
    RollupMixin, ExtendedRollupMixin, TransformMixin, SelectorMixin, LabelMixin, TemporalMixin, TemplateMixin, Expression,
):
    """One immutable Rust expression owner for PromQL and MetricsQL.

    Operation groups contain no instance state. Native construction and ownership
    live in Expression; Rust remains the authority for types, dialects and syntax.
    """

    __slots__ = ()

    def vector(value: ScalarInput) -> QueryBuilder:
        """Convert a scalar expression, or construct with QueryBuilder.vector(number)."""
        return QueryBuilder.function("vector", value)
