from enum import Enum

class BuilderType(Enum):
    """Enumeration of different types of builders."""

    INSTANT_VECTOR = "instant_vector"
    PROCESSED_VECTOR = "processed_vector"
    RANGE_VECTOR = "range_vector"
    SCALAR = "scalar"
