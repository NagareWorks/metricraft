"""Prometheus configuration."""


from typing import Any, Dict, Optional

from metricraft.config.http_options import HttpClientOptions
from metricraft.config.base import Config
from metricraft.enums import DBType


class PrometheusConfig(Config):
    """
    Configuration for Prometheus deployment.

    Used for standard Prometheus instances. URLs directly use /api/v1 paths
    without any additional prefixes.
    """

    DEFAULT_TIMEOUT = 30.0

    def __init__(
        self,
        url: str,
        default_step: str = "1m",
        *,
        http_options: Optional[HttpClientOptions] = None,
        **kwargs,
    ):
        """
        Initialize Prometheus configuration.

        Args:
            url: Base URL for Prometheus instance (e.g., "http://localhost:9090")
                 API paths will use /api/v1 directly without additional prefixes.
            default_step: Default step for range queries (default: "1m")
            http_options: HTTP client configuration options
            **kwargs: Additional connection parameters
        """
        if "timeout" in kwargs:
            raise TypeError("timeout must be provided inside http_options")

        options = HttpClientOptions.ensure(http_options)
        if options.timeout is None:
            options = options.merge({"timeout": self.DEFAULT_TIMEOUT})

        super().__init__(http_options=options)
        self.type = 'prometheus'
        self.url = url.rstrip('/')
        self.default_step = default_step
        self.extra_params = kwargs
        timeout_tuple = self.http_options.timeout
        self.timeout = timeout_tuple[1] if timeout_tuple else self.DEFAULT_TIMEOUT

    @property
    def db_type(self) -> DBType:
        return DBType.PROMETHEUS

    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information for Prometheus."""
        info = {
            'type': 'prometheus',
            'url': self.url,
            'timeout': self.timeout,
            'default_step': self.default_step,
            **self.extra_params
        }
        return self._inject_http_options(info)

    def get_query_url_base(self) -> str:
        """Get base URL for query operations - direct /api/v1 path."""
        return self.url

    def get_insert_url_base(self) -> str:
        """Prometheus does not support insert operations."""
        raise NotImplementedError(
            "Prometheus does not support insert operations. "
            "The insert() method is specific to VictoriaMetrics."
        )

    def validate(self) -> None:
        """Validate Prometheus configuration."""
        if not self.url:
            raise ValueError("Prometheus URL cannot be empty")
        if not isinstance(self.url, str):
            raise ValueError("Prometheus URL must be a string")
        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")
