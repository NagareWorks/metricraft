"""Validated input for VictoriaMetrics ingestion."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Union

from .types import TimeValue


@dataclass(frozen=True)
class MetricsInsertData:
    """Metric samples submitted through the VictoriaMetrics ingestion endpoint."""

    query: str
    times: List[TimeValue]
    values: List[Union[int, float, str]]

    def validate(self) -> None:
        """Validate insert data structure."""
        if not self.query:
            raise ValueError("query cannot be empty")
        if not self.times:
            raise ValueError("times cannot be empty")
        if not self.values:
            raise ValueError("values cannot be empty")
        if len(self.times) != len(self.values):
            raise ValueError("times and values must have same length")

    def __post_init__(self):
        """Validate insert data on creation."""
        self.validate()
