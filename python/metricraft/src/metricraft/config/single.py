"""Single-node VictoriaMetrics configuration."""


from typing import Any, Dict, Optional

from metricraft.config.http_options import HttpClientOptions
from metricraft.config.base import Config
from metricraft.enums import DBType


class VMSingleConfig(Config):
    """
    Configuration for single-node VictoriaMetrics deployment.

    Used for standalone VM instances where all operations go to the same endpoint.
    URL will automatically have /prometheus prefix added for API paths.
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
        Initialize single-node VM configuration.

        Args:
            url: Base URL for VictoriaMetrics instance (e.g., "http://localhost:8428")
                 The /prometheus prefix will be automatically added when constructing API paths.
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
        self.type = 'single'
        self.url = url.rstrip('/')
        self.default_step = default_step
        self.extra_params = kwargs
        timeout_tuple = self.http_options.timeout
        self.timeout = timeout_tuple[1] if timeout_tuple else self.DEFAULT_TIMEOUT

    @property
    def db_type(self) -> DBType:
        return DBType.VM

    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information for single-node VM."""
        info = {
            'type': 'single',
            'url': self.url,
            'timeout': self.timeout,
            'default_step': self.default_step,
            **self.extra_params
        }
        return self._inject_http_options(info)

    def get_query_url_base(self) -> str:
        """Get base URL for query operations with /prometheus prefix."""
        return f"{self.url}/prometheus"

    def get_insert_url_base(self) -> str:
        """Get base URL for insert operations with /prometheus prefix."""
        return f"{self.url}/prometheus"

    def validate(self) -> None:
        """Validate single-node configuration."""
        if not self.url:
            raise ValueError("VM URL cannot be empty")
        if not isinstance(self.url, str):
            raise ValueError("VM URL must be a string")
        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")
