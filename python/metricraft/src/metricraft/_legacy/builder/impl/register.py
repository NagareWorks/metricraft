from typing import TYPE_CHECKING, Dict, Type

from metricraft._legacy.builder.impl.types import BuilderType
from metricraft._legacy.contracts import QueryBuilder


class BuilderRegister:
    """Registry for all available builder types."""

    _builders: Dict[BuilderType, Type[QueryBuilder]] = {}

    @classmethod
    def register_builder(cls, builder_type: BuilderType, builder_class: Type[QueryBuilder]):
        """Register a new builder class."""
        cls._builders[builder_type] = builder_class

    @classmethod
    def get_builder(cls, builder_type: BuilderType, **kwargs) -> QueryBuilder:
        """Get a registered builder class."""
        builder_class = cls._builders.get(builder_type)
        if not builder_class:
            raise ValueError(f"Builder type {builder_type} is not registered.")
        return builder_class(**kwargs)
