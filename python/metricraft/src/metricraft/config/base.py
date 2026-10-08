"""
Shared HTTP endpoint configuration and thread-safe named-instance registry.
"""


from abc import ABC, abstractmethod
from threading import RLock
from typing import Optional, Dict, Any

from metricraft.enums import DBType
from metricraft.config.http_options import HttpClientOptions

class Config(ABC):
    """
    Shared endpoint contract for Prometheus and VictoriaMetrics.

    Concrete configurations supply endpoint URLs and backend identity.
    Query-language selection belongs to the builder, not connection settings.
    """

    def __init__(
        self,
        *,
        http_options: Optional[HttpClientOptions] = None,
    ):
        """Initialize configuration container for connection info only.

        Note:
            Implementations should NOT bind builder/client classes here.
            The SDK constructs its HTTP client directly.
        """
        super().__init__()
        self._http_options = self._coerce_http_options(http_options)

    @property
    def http_options(self) -> HttpClientOptions:
        """Return the configured HTTP client options container."""

        return self._http_options

    @property
    def http_options_dict(self) -> Dict[str, Any]:
        """Return HTTP options as a serializable dict."""

        return self._http_options.to_dict()

    def set_http_options(self, options: Optional[HttpClientOptions]) -> None:
        """Replace stored HTTP client options."""

        self._http_options = self._coerce_http_options(options)

    def update_http_options(self, overrides: Optional[HttpClientOptions]) -> None:
        """Merge overrides into the stored HTTP client options."""

        if overrides is None:
            return
        if not isinstance(overrides, HttpClientOptions):
            raise TypeError("http_options overrides must be HttpClientOptions or None")
        self._http_options = self._http_options.merge(overrides)

    def _inject_http_options(self, info: Dict[str, Any]) -> Dict[str, Any]:
        """Helper to add HTTP options into ``get_connection_info`` results."""

        options_dict = self.http_options_dict
        if not options_dict:
            return info
        merged = dict(info)
        merged['http_options'] = options_dict
        return merged

    @staticmethod
    def _coerce_http_options(value: Optional[HttpClientOptions]) -> HttpClientOptions:
        if value is None:
            return HttpClientOptions()
        if not isinstance(value, HttpClientOptions):
            raise TypeError("http_options must be an instance of HttpClientOptions or None")
        return value
    
    @abstractmethod
    def get_connection_info(self) -> Dict[str, Any]:
        """
        Get database connection information.
        
        Each implementation should return appropriate connection details.
        For example, VM might return URLs, Prometheus might return different info.
        
        Returns:
            Dictionary containing connection information
        """
        pass
    
    @abstractmethod
    def validate(self) -> None:
        """
        Validate the configuration.
        
        Each implementation should validate its specific configuration requirements.
        Should raise ValueError if configuration is invalid.
        """
        pass

    @property
    @abstractmethod
    def db_type(self) -> DBType:
        """Database type this configuration belongs to."""
        raise NotImplementedError

    @abstractmethod
    def get_query_url_base(self) -> str:
        """Return the base URL for query and metadata operations."""
        raise NotImplementedError

    def get_insert_url_base(self) -> str:
        """Return an ingestion endpoint when supported by this configuration."""
        raise NotImplementedError(
            f"{type(self).__name__} does not support insert operations"
        )


_lock = RLock()
_configs: Dict[DBType, Dict[str, Config]] = {}
_defaults: Dict[DBType, str] = {}


def register_config(config: Config, instance: str = "default", *, set_default: bool = True) -> None:
    """Register a configuration for a given (db_type, instance).

    Validates the config and stores it in a thread-safe multi-instance registry.
    Set ``set_default=True`` to mark this instance as the default for the db_type.
    """
    if not isinstance(config, Config):
        raise ValueError("config must be an instance of Config")
    config.validate()
    with _lock:
        db_type = config.db_type
        bucket = _configs.setdefault(db_type, {})
        if instance in bucket:
            raise RuntimeError(f"Configuration already registered for {db_type}:{instance}")
        bucket[instance] = config
        # Only set default when explicitly requested
        if set_default:
            _defaults[db_type] = instance


def update_config(config: Config, instance: str = "default", *, set_default: bool = False) -> None:
    """Replace an existing configuration entry without resetting the registry."""
    if not isinstance(config, Config):
        raise ValueError("config must be an instance of Config")
    config.validate()
    with _lock:
        db_type = config.db_type
        bucket = _configs.get(db_type)
        if not bucket or instance not in bucket:
            raise RuntimeError(f"No configuration registered for {db_type}:{instance}")
        bucket[instance] = config
        if set_default:
            _defaults[db_type] = instance


def set_default_instance(db_type: DBType, instance: str) -> None:
    with _lock:
        if instance not in _configs.get(db_type, {}):
            raise RuntimeError(f"Instance not found for {db_type}:{instance}")
        _defaults[db_type] = instance


def get_config(db_type: Optional[DBType] = None, instance: Optional[str] = None) -> Config:
    """Get an endpoint by backend and/or instance name.

    Without a backend, the instance name must identify exactly one backend.
    Without either argument, exactly one backend must be registered. Within
    that backend, select its sole instance or configured default.
    """
    with _lock:
        if db_type is None:
            backends = [
                kind for kind, entries in _configs.items()
                if instance is None or instance in entries
            ]
            if not backends:
                raise RuntimeError(f"No configuration registered for instance {instance!r}")
            if len(backends) > 1:
                raise RuntimeError(
                    "Ambiguous configuration across backends; pass an explicit config "
                    "to DatabaseClient, use a unique instance name, or specify db_type "
                    "when calling get_config"
                )
            db_type = backends[0]
        bucket = _configs.get(db_type, {})
        if not bucket:
            raise RuntimeError(f"No configuration registered for {db_type}")
        if instance is None:
            if len(bucket) == 1:
                return next(iter(bucket.values()))
            if db_type in _defaults:
                return bucket[_defaults[db_type]]
            raise RuntimeError(f"Multiple instances for {db_type}; specify instance")
        if instance not in bucket:
            raise RuntimeError(f"No configuration for {db_type}:{instance}")
        return bucket[instance]


def is_configured(db_type: DBType, instance: Optional[str] = None) -> bool:
    with _lock:
        if instance is None:
            return bool(_configs.get(db_type))
        return instance in _configs.get(db_type, {})


def reset_config() -> None:
    """Reset the entire configuration registry (testing only)."""
    with _lock:
        _configs.clear()
        _defaults.clear()
