"""Cluster VictoriaMetrics configuration."""


from typing import Any, Dict, Optional

from metricraft.config.http_options import HttpClientOptions
from metricraft.config.base import Config
from metricraft.enums import DBType


class VMClusterConfig(Config):
    """
    Configuration for VictoriaMetrics cluster deployment.

    Used for VM cluster deployments with separate insert/select/storage endpoints.
    URLs will automatically have /select/{accountID}/prometheus or /insert/{accountID}/prometheus
    prefix added for API paths based on the operation type.
    """

    DEFAULT_TIMEOUT = 30.0
    DEFAULT_ACCOUNT_ID = 0

    def __init__(
        self,
        vminsert_url: str,
        vmselect_url: str,
        vmstorage_url: str,
        account_id: int = DEFAULT_ACCOUNT_ID,
        default_step: str = '1m',
        *,
        http_options: Optional[HttpClientOptions] = None,
        **kwargs
    ):
        """
        Initialize cluster VM configuration.

        Args:
            vminsert_url: URL for vminsert component (e.g., "http://vminsert:8480")
                         The /insert/{accountID}/prometheus prefix will be automatically added.
            vmselect_url: URL for vmselect component (e.g., "http://vmselect:8481")
                         The /select/{accountID}/prometheus prefix will be automatically added.
            vmstorage_url: URL for vmstorage component (e.g., "http://vmstorage:8482")
            account_id: Tenant account ID for multi-tenancy (default: 0)
                       Must be non-negative integer.
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
        self.type = 'cluster'
        self.vminsert_url = vminsert_url.rstrip('/')
        self.vmselect_url = vmselect_url.rstrip('/')
        self.vmstorage_url = vmstorage_url.rstrip('/')
        self.account_id = account_id
        self.default_step = default_step
        self.extra_params = kwargs
        timeout_tuple = self.http_options.timeout
        self.timeout = timeout_tuple[1] if timeout_tuple else self.DEFAULT_TIMEOUT

    @property
    def db_type(self) -> DBType:
        return DBType.VM

    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information for VM cluster."""
        info = {
            'type': 'cluster',
            'vminsert_url': self.vminsert_url,
            'vmselect_url': self.vmselect_url,
            'vmstorage_url': self.vmstorage_url,
            'account_id': self.account_id,
            'timeout': self.timeout,
            'default_step': self.default_step,
            **self.extra_params
        }
        return self._inject_http_options(info)

    def get_query_url_base(self) -> str:
        """Get base URL for query operations with /select/{accountID}/prometheus prefix."""
        return f"{self.vmselect_url}/select/{self.account_id}/prometheus"

    def get_insert_url_base(self) -> str:
        """Get base URL for insert operations with /insert/{accountID}/prometheus prefix."""
        return f"{self.vminsert_url}/insert/{self.account_id}/prometheus"

    def validate(self) -> None:
        """Validate cluster configuration."""
        urls = {
            'vminsert_url': self.vminsert_url,
            'vmselect_url': self.vmselect_url,
            'vmstorage_url': self.vmstorage_url
        }

        for name, url in urls.items():
            if not url:
                raise ValueError(f"{name} cannot be empty")
            if not isinstance(url, str):
                raise ValueError(f"{name} must be a string")

        if not isinstance(self.account_id, int):
            raise ValueError("account_id must be an integer")
        if self.account_id < 0:
            raise ValueError("account_id must be non-negative")

        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")
