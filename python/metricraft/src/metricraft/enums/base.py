"""HTTP backend identifiers, independent of query dialect selection."""
from enum import Enum


class DBType(str, Enum):
    """HTTP backend identifiers. Query dialect is selected by QueryMode."""

    VM = "vm"
    PROMETHEUS = "prometheus"
