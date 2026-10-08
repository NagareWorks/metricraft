"""
Synchronous and asynchronous Prometheus/VictoriaMetrics HTTP client.
"""

import logging
from weakref import finalize
from functools import cached_property
from typing import Any, Dict, Iterable, List, Optional, Union

from metricraft.client._time import ingestion_milliseconds, query_time, range_bounds
from metricraft.client._resources import TransportResources
from metricraft.client.http_client import SyncHTTPClient, AsyncHTTPClient
from metricraft.models import (
    MetricsQueryResult,
    MetricsInsertData,
    SeriesResult,
    LabelsResult,
    LabelValuesResult
)
from metricraft.builder import QueryBuilder
from metricraft.models import TimeValue
from metricraft.config.base import Config, get_config
from metricraft.config.http_options import HttpClientOptions
from metricraft.enums import DBType


_logger = logging.getLogger(__name__)


class DatabaseClient:
    """
    Execute queries with explicit endpoint configuration or a named instance.

    Supports Prometheus and VictoriaMetrics single-node/cluster deployments.
    """

    def __init__(self, config: Optional[Config] = None, *, instance: Optional[str] = None) -> None:
        """Use explicit config, or resolve an optional registered instance."""
        if config is not None and instance is not None:
            raise TypeError("Pass either config or instance, not both")
        if config is not None and not isinstance(config, Config):
            raise TypeError("config must be a MetriCraft Config instance")
        # Resolve and validate before allocating transports.
        cfg = config if config is not None else get_config(instance=instance)
        if config is not None:
            config.validate()
        self._config = cfg
        self.connection_info = cfg.get_connection_info()
        self._resources = TransportResources()
        self._finalizer = finalize(self, self._resources.close)
        try:
            self._setup_connection()
        except BaseException:
            self.close()
            raise

    @property
    def client(self):
        return self._resources.sync

    @client.setter
    def client(self, transport):
        self._resources.sync = transport

    @client.deleter
    def client(self):
        del self._resources.sync

    @property
    def async_client(self):
        return self._resources.async_

    @async_client.setter
    def async_client(self, transport):
        self._resources.async_ = transport

    @async_client.deleter
    def async_client(self):
        del self._resources.async_

    @property
    def closed(self) -> bool:
        return self._resources.closed

    def close(self) -> None:
        """Release transports once; async-only transports need aclose()."""
        self._resources.close()
        self._finalizer.detach()

    async def aclose(self) -> None:
        """Await asynchronous cleanup and release the synchronous transport."""
        try:
            await self._resources.aclose()
        finally:
            self._finalizer.detach()

    def __enter__(self) -> "DatabaseClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        self.close()
        return False

    async def __aenter__(self) -> "DatabaseClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        await self.aclose()
        return False

    def get_connection_info(self) -> Dict[str, Any]:
        """Return a shallow copy of the active connection settings."""
        return self.connection_info.copy()

    def _validate_account_id(self, account_id: Optional[int]) -> None:
        """
        Validate account_id parameter based on configuration type.

        Args:
            account_id: The account_id parameter passed to query/insert methods

        Raises:
            ValueError: If account_id is provided for non-cluster config or is invalid
        """
        if account_id is None:
            return

        conn_type = self.connection_info.get('type')
        if conn_type != 'cluster':
            raise ValueError(
                f"account_id parameter is only supported for VMClusterConfig, "
                f"but current config type is '{conn_type}'. "
                "Use VMClusterConfig for multi-tenant deployments."
            )

        if not isinstance(account_id, int):
            raise ValueError("account_id must be an integer")
        if account_id < 0:
            raise ValueError("account_id must be non-negative")

    def _get_effective_account_id(self, override_account_id: Optional[int]) -> int:
        """
        Get the effective account_id to use for this request.

        Args:
            override_account_id: Account ID override passed to query/insert method

        Returns:
            The account ID to use (from override or config)

        Raises:
            ValueError: If override is invalid for the config type
        """
        self._validate_account_id(override_account_id)

        if override_account_id is not None:
            return override_account_id

        # For cluster configs, use the configured account_id
        return self.connection_info.get('account_id', 0)

    def _get_query_url_with_account(self, account_id: Optional[int] = None) -> str:
        """
        Get query URL with appropriate account_id.

        For cluster configs, this allows overriding the account_id per-request.
        For single configs, the base URL is returned without modification.

        Args:
            account_id: Optional account_id override

        Returns:
            Complete base URL for query operations
        """
        conn_type = self.connection_info.get('type')

        if conn_type == 'cluster':
            # Cluster supports per-request account_id override
            effective_account_id = self._get_effective_account_id(account_id)
            vmselect_url = self.connection_info['vmselect_url']
            return f"{vmselect_url}/select/{effective_account_id}/prometheus"
        else:
            # Non-cluster configs don't support account_id override
            if account_id is not None:
                raise ValueError(
                    f"account_id parameter is only supported for VMClusterConfig, "
                    f"but current config type is '{conn_type}'"
                )
            return self.select_base_url

    def _get_insert_url_with_account(self, account_id: Optional[int] = None) -> str:
        """
        Get insert URL with appropriate account_id.

        For cluster configs, this allows overriding the account_id per-request.
        For single configs, the base URL is returned without modification.

        Args:
            account_id: Optional account_id override

        Returns:
            Complete base URL for insert operations
        """
        conn_type = self.connection_info.get('type')

        if conn_type == 'cluster':
            # Cluster supports per-request account_id override
            effective_account_id = self._get_effective_account_id(account_id)
            vminsert_url = self.connection_info['vminsert_url']
            return f"{vminsert_url}/insert/{effective_account_id}/prometheus"
        else:
            # Non-cluster configs don't support account_id override
            if account_id is not None:
                raise ValueError(
                    f"account_id parameter is only supported for VMClusterConfig, "
                    f"but current config type is '{conn_type}'"
                )
            return self.insert_base_url

    def _normalize_time(self, time_val: TimeValue) -> Optional[str]:
        """Preserve query timestamp precision; strings pass through to the backend."""
        return query_time(time_val)

    def _setup_connection(self) -> None:
        """Create or inject HTTP transports for the resolved endpoint."""
        conn_info = getattr(self, 'connection_info', {})
        config_http = getattr(self._config, 'http_options', None)
        combined_http = config_http
        overrides = conn_info.get('http_options') or {}
        if combined_http is None:
            combined_http = HttpClientOptions.ensure(overrides)
        else:
            combined_http = combined_http.merge(overrides)

        legacy_headers = conn_info.get('http_headers') or conn_info.get('headers')
        if legacy_headers and not combined_http.default_headers:
            combined_http = combined_http.merge({'default_headers': legacy_headers})

        http_options_dict = combined_http.to_dict()
        self.http_options = http_options_dict
        self.connection_info['http_options'] = http_options_dict

        timeout_setting = combined_http.timeout or conn_info.get('timeout', 30.0)
        self.timeout = self._extract_timeout_value(timeout_setting)
        self.connection_info['timeout'] = self.timeout
        self.default_step = conn_info.get('default_step', '1m')

        default_headers = http_options_dict.get('default_headers', {})
        prepare_request = http_options_dict.get('prepare_request')
        opener = http_options_dict.get('opener')

        sync_client = http_options_dict.get('client')
        async_client = http_options_dict.get('async_client')
        sync_factory = http_options_dict.get('client_factory')
        async_factory = http_options_dict.get('async_client_factory')

        sync_kwargs = {
            'timeout': timeout_setting,
            'default_headers': default_headers,
            'prepare_request': prepare_request,
        }
        if opener:
            sync_kwargs['opener'] = opener

        if sync_client is not None:
            self.client = sync_client
        elif callable(sync_factory):
            self.client = sync_factory(
                http_options=http_options_dict,
                connection_info=conn_info,
            )
        else:
            self.client = SyncHTTPClient(**sync_kwargs)

        max_workers = http_options_dict.get('max_workers', 4)
        executor = http_options_dict.get('executor')

        if async_client is not None:
            self.async_client = async_client
        elif callable(async_factory):
            self.async_client = async_factory(
                http_options=http_options_dict,
                connection_info=conn_info,
                sync_client=self.client,
            )
        else:
            try:
                async_kwargs = {
                    'timeout': timeout_setting,
                    'sync_client': self.client,
                    'max_workers': max_workers,
                }
                if executor is not None:
                    async_kwargs['executor'] = executor
                self.async_client = AsyncHTTPClient(**async_kwargs)
            except Exception:
                self.async_client = None

    @cached_property
    def select_base_url(self) -> str:
        """Get the base URL for select queries with appropriate path prefix."""
        return self._config.get_query_url_base()

    @cached_property
    def insert_base_url(self) -> str:
        """Get the base URL for insert queries with appropriate path prefix."""
        return self._config.get_insert_url_base()

    @cached_property
    def storage_base_url(self) -> str:
        """Get the base URL for storage queries (if needed)."""
        conn_info = self.connection_info
        if conn_info['type'] == 'single':
            return conn_info['url'].rstrip('/')
        elif conn_info['type'] == 'cluster':
            return conn_info['vmstorage_url'].rstrip('/')
        else:
            raise ValueError("Invalid connection type")

    def query(
        self,
        query: Union[str, QueryBuilder],
        time: Optional[TimeValue] = None,
        timeout: Optional[str] = None,
        *,
        step: Optional[str] = None,
        limit: Optional[int] = None,
        extra_label: Optional[Union[str, Dict[str, str]]] = None,
        extra_filters: Optional[Union[str, list]] = None,
        round_digits: Optional[int] = None,
        nocache: Optional[bool] = None,
        trace: Optional[bool] = None,
        account_id: Optional[int] = None,
        custom_params: Optional[Dict[str, Any]] = None,
    ) -> MetricsQueryResult:
        """
        Execute instant query against VictoriaMetrics.

        Args:
            query: MetricsQL/PromQL query string or QueryBuilder instance
            time: Evaluation time (default: current time). Supports:
                  - Unix timestamp (seconds, or milliseconds when magnitude exceeds 1e10)
                  - RFC3339 format (e.g., '2022-03-29T01:23:45Z')
                  - [VM-specific] Relative time (e.g., 'now-1h5m', '1h5m')
            timeout: [Common] Query timeout (e.g., '30s', '1m')
            step: [VM-specific] Lookback window for finding raw samples when data point
                  is missing at the specified time. For example, step=1m means searching
                  for the most recent data point in the [time-1m, time] interval.
                  Default: 5m if omitted.
            limit: [Prometheus-only] Maximum number of returned series.
                   Note: VictoriaMetrics accepts but ignores this parameter.
            extra_label: [VM-specific] Force additional label filters for the query.
                         Can be string 'key=value' or dict {'key': 'value'}.
                         Used for multi-tenancy isolation.
            extra_filters: [VM-specific] Add arbitrary label filters (supports regex).
                            Example: '{env=~"prod|staging",user="xyz"}'
            round_digits: [VM-specific] Round response values to specified decimal places.
            nocache: [VM-specific] If True, disable response caching for this query.
            trace: [VM-specific] If True, enable query tracing for performance analysis.
            account_id: [Cluster-only] Override account ID for this request.
                       Only valid for VMClusterConfig. For VMSingleConfig, this will raise ValueError.
            custom_params: [User-defined] Additional custom parameters for the request.
                          This parameter allows users to pass custom parameters to the request,
                          which can be used for calling modified versions of VM or other custom
                          implementations. No security validation is performed on these parameters.
                          Users are responsible for handling any security risks.

        Returns:
            Query result with metrics data

        Raises:
            MCHTTPError: For API errors
            TimeoutError: For timeout errors
            ConnectionError: For connection errors
            ValueError: If account_id is provided for VMSingleConfig
        """
        query_str = self._prepare_query(query)
        base_url = self._get_query_url_with_account(account_id)
        url = f"{base_url}/api/v1/query"
        params = {'query': query_str}

        if time is not None:
            params['time'] = self._normalize_time(time)
        if timeout is not None:
            params['timeout'] = timeout
        if step is not None:
            params['step'] = step
        if limit is not None:
            params['limit'] = str(limit)

        # VM-specific parameters
        self._add_vm_specific_params(params, extra_label, extra_filters,
                                    round_digits, nocache, trace)

        # Add custom parameters if provided
        if custom_params:
            params.update(custom_params)

        response = self.client.get(url, params=params)
        return self._process_response(response)

    def query_range(
        self,
        query: Union[str, QueryBuilder],
        start: Optional[TimeValue] = None,
        end: Optional[TimeValue] = None,
        step: Optional[str] = None,
        timeout: Optional[str] = None,
        *,
        limit: Optional[int] = None,
        extra_label: Optional[Union[str, Dict[str, str]]] = None,
        extra_filters: Optional[Union[str, list]] = None,
        round_digits: Optional[int] = None,
        nocache: Optional[bool] = None,
        trace: Optional[bool] = None,
        account_id: Optional[int] = None,
        custom_params: Optional[Dict[str, Any]] = None,
    ) -> MetricsQueryResult:
        """
        Execute range query against VictoriaMetrics.

        Args:
            query: MetricsQL/PromQL query string or QueryBuilder instance
            start: Range start time (default: 1 hour before end time). Supports:
                   - Unix timestamp (seconds, or milliseconds when magnitude exceeds 1e10)
                   - RFC3339 format (e.g., '2022-03-29T01:23:45Z')
                   - [VM-specific] Relative time (e.g., 'now-1h5m', '1h5m')
            end: Range end time (default: current time). Same format support as start.
            step: [Common] Query resolution step (default: driver default_step, typically '1m')
            timeout: [Common] Query timeout (e.g., '30s', '1m')
            limit: [Prometheus-only] Maximum number of returned series.
                   Note: VictoriaMetrics accepts but ignores this parameter.
            extra_label: [VM-specific] Force additional label filters for the query.
                         Can be string 'key=value' or dict {'key': 'value'}.
                         Used for multi-tenancy isolation.
            extra_filters: [VM-specific] Add arbitrary label filters (supports regex).
                            Example: '{env=~"prod|staging",user="xyz"}'
            round_digits: [VM-specific] Round response values to specified decimal places.
            nocache: [VM-specific] If True, disable response caching for this query.
            trace: [VM-specific] If True, enable query tracing for performance analysis.
            account_id: [Cluster-only] Override account ID for this request.
                       Only valid for VMClusterConfig. For VMSingleConfig, this will raise ValueError.
            custom_params: [User-defined] Additional custom parameters for the request.
                          This parameter allows users to pass custom parameters to the request,
                          which can be used for calling modified versions of VM or other custom
                          implementations. No security validation is performed on these parameters.
                          Users are responsible for handling any security risks.

        Returns:
            Query result with time series data

        Raises:
            MCHTTPError: For API errors
            TimeoutError: For timeout errors
            ConnectionError: For connection errors
            ValueError: If account_id is provided for VMSingleConfig
        """
        start, end = range_bounds(start, end)

        query_str = self._prepare_query(query)
        base_url = self._get_query_url_with_account(account_id)
        url = f"{base_url}/api/v1/query_range"

        params = {
            'query': query_str,
            'start': self._normalize_time(start),
            'end': self._normalize_time(end),
            'step': step or self.default_step
        }

        if timeout is not None:
            params['timeout'] = timeout
        if limit is not None:
            params['limit'] = str(limit)

        # VM-specific parameters
        self._add_vm_specific_params(params, extra_label, extra_filters,
                                    round_digits, nocache, trace)

        # Add custom parameters if provided
        if custom_params:
            params.update(custom_params)

        response = self.client.get(url, params=params)
        return self._process_response(response)

    def _health_url(self) -> str:
        info = self.connection_info
        base = info['vmselect_url'] if info['type'] == 'cluster' else info['url']
        path = '/-/healthy' if self._config.db_type == DBType.PROMETHEUS else '/health'
        return base.rstrip('/') + path

    @staticmethod
    def _healthy_response(response) -> bool:
        if isinstance(response, str):
            return response.strip() in ('OK', 'Prometheus Server is Healthy.')
        # Custom transports may expose a decoded health response.
        return isinstance(response, dict) and response.get('status') == 'ok'

    def health(self) -> bool:
        """
        Check if VictoriaMetrics is healthy and reachable.

        Returns:
            True if healthy, False otherwise
        """
        try:
            getter = getattr(self.client, "get_text", self.client.get)
            return self._healthy_response(getter(self._health_url()))
        except Exception:
            return False

    def insert(
        self,
        data: Union[MetricsInsertData, Iterable[MetricsInsertData]],
        *,
        account_id: Optional[int] = None,
        custom_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Insert metrics data (VM-specific method).

        Note: This method is specific to VictoriaMetrics and is not available in Prometheus.
              Using PrometheusConfig will raise NotImplementedError.

        Args:
            data: Insert payload or an iterable of payloads
            account_id: [Cluster-only] Override account ID for this request.
                       Only valid for VMClusterConfig. Will raise ValueError for other config types.
            custom_params: [User-defined] Additional custom parameters for the request.
                          This parameter allows users to pass custom parameters to the request,
                          which can be used for calling modified versions of VM or other custom
                          implementations. No security validation is performed on these parameters.
                          Users are responsible for handling any security risks.

        Returns:
            Response from insert operation

        Raises:
            NotImplementedError: If using PrometheusConfig (Prometheus doesn't support insert)
            ValueError: If account_id is provided for non-cluster config
        """
        base_url = self._get_insert_url_with_account(account_id)
        url = f"{base_url}/api/v1/import/prometheus"

        # Convert data to Prometheus format
        prometheus_data = self._convert_to_prometheus_format(data)

        # Prepare request parameters
        params = {}
        if custom_params:
            params.update(custom_params)

        response = self.client.post(url, data=prometheus_data, params=params)
        return response

   # Asynchronous query methods

    async def query_async(
            self,
            query: Union[str, QueryBuilder],
            time: Optional[TimeValue] = None,
            timeout: Optional[str] = None,
            *,
            step: Optional[str] = None,
            limit: Optional[int] = None,
            extra_label: Optional[Union[str, Dict[str, str]]] = None,
            extra_filters: Optional[Union[str, list]] = None,
            round_digits: Optional[int] = None,
            nocache: Optional[bool] = None,
            trace: Optional[bool] = None,
            account_id: Optional[int] = None,
            custom_params: Optional[Dict[str, Any]] = None,
    ) -> MetricsQueryResult:
        """
        Execute async instant query against VictoriaMetrics.

        Args:
            query: MetricsQL/PromQL query string or QueryBuilder instance
            time: Evaluation time (default: current time). Supports:
                  - Unix timestamp (seconds, or milliseconds when magnitude exceeds 1e10)
                  - RFC3339 format (e.g., '2022-03-29T01:23:45Z')
                  - [VM-specific] Relative time (e.g., 'now-1h5m', '1h5m')
            timeout: [Common] Query timeout (e.g., '30s', '1m')
            step: [VM-specific] Lookback window for finding raw samples when data point
                  is missing at the specified time. Default: 5m if omitted.
            limit: [Prometheus-only] Maximum number of returned series.
                   Note: VictoriaMetrics accepts but ignores this parameter.
            extra_label: [VM-specific] Force additional label filters for the query.
            extra_filters: [VM-specific] Add arbitrary label filters (supports regex).
            round_digits: [VM-specific] Round response values to specified decimal places.
            nocache: [VM-specific] If True, disable response caching for this query.
            trace: [VM-specific] If True, enable query tracing for performance analysis.
            account_id: [Cluster-only] Override account ID for this request.
                       Only valid for VMClusterConfig. For VMSingleConfig, this will raise ValueError.
            custom_params: [User-defined] Additional custom parameters for the request.
                          This parameter allows users to pass custom parameters to the request,
                          which can be used for calling modified versions of VM or other custom
                          implementations. No security validation is performed on these parameters.
                          Users are responsible for handling any security risks.

        Returns:
            Query result with metrics data

        Raises:
            ImportError: If async support is not available
            MCHTTPError: For API errors
            TimeoutError: For timeout errors
            ConnectionError: For connection errors
            ValueError: If account_id is provided for VMSingleConfig
        """
        if not self.async_client:
            raise RuntimeError("Async support not available")

        query_str = self._prepare_query(query)
        base_url = self._get_query_url_with_account(account_id)
        url = f"{base_url}/api/v1/query"

        params = {'query': query_str}
        if time is not None:
            params['time'] = self._normalize_time(time)
        if timeout is not None:
            params['timeout'] = timeout
        if step is not None:
            params['step'] = step
        if limit is not None:
            params['limit'] = str(limit)

        # VM-specific parameters
        self._add_vm_specific_params(params, extra_label, extra_filters,
                                    round_digits, nocache, trace)

        # Add custom parameters if provided
        if custom_params:
            params.update(custom_params)

        response = await self.async_client.get(url, params=params)
        return self._process_response(response)

    async def query_range_async(
        self,
        query: Union[str, QueryBuilder],
        start: Optional[TimeValue] = None,
        end: Optional[TimeValue] = None,
        step: Optional[str] = None,
        timeout: Optional[str] = None,
        *,
        limit: Optional[int] = None,
        extra_label: Optional[Union[str, Dict[str, str]]] = None,
        extra_filters: Optional[Union[str, list]] = None,
        round_digits: Optional[int] = None,
        nocache: Optional[bool] = None,
        trace: Optional[bool] = None,
        account_id: Optional[int] = None,
        custom_params: Optional[Dict[str, Any]] = None,
    ) -> MetricsQueryResult:
        """
        Execute async range query against VictoriaMetrics.

        Args:
            query: MetricsQL/PromQL query string or QueryBuilder instance
            start: Range start time (default: 1 hour before end time). Supports:
                   - Unix timestamp (seconds, or milliseconds when magnitude exceeds 1e10)
                   - RFC3339 format (e.g., '2022-03-29T01:23:45Z')
                   - [VM-specific] Relative time (e.g., 'now-1h5m', '1h5m')
            end: Range end time (default: current time). Same format support as start.
            step: [Common] Query resolution step (default: driver default_step)
            timeout: [Common] Query timeout (e.g., '30s', '1m')
            limit: [Prometheus-only] Maximum number of returned series.
                   Note: VictoriaMetrics accepts but ignores this parameter.
            extra_label: [VM-specific] Force additional label filters for the query.
            extra_filters: [VM-specific] Add arbitrary label filters (supports regex).
            round_digits: [VM-specific] Round response values to specified decimal places.
            nocache: [VM-specific] If True, disable response caching for this query.
            trace: [VM-specific] If True, enable query tracing for performance analysis.
            account_id: [Cluster-only] Override account ID for this request.
                       Only valid for VMClusterConfig. For VMSingleConfig, this will raise ValueError.
            custom_params: [User-defined] Additional custom parameters for the request.
                          This parameter allows users to pass custom parameters to the request,
                          which can be used for calling modified versions of VM or other custom
                          implementations. No security validation is performed on these parameters.
                          Users are responsible for handling any security risks.

        Returns:
            Query result with time series data

        Raises:
            ImportError: If async support is not available
            MCHTTPError: For API errors
            TimeoutError: For timeout errors
            ConnectionError: For connection errors
            ValueError: If account_id is provided for VMSingleConfig
        """
        if not self.async_client:
            raise RuntimeError("Async support not available")

        start, end = range_bounds(start, end)

        query_str = self._prepare_query(query)
        base_url = self._get_query_url_with_account(account_id)
        url = f"{base_url}/api/v1/query_range"

        params = {
            'query': query_str,
            'start': self._normalize_time(start),
            'end': self._normalize_time(end),
            'step': step or self.default_step
        }

        if timeout is not None:
            params['timeout'] = timeout
        if limit is not None:
            params['limit'] = str(limit)

        # VM-specific parameters
        self._add_vm_specific_params(params, extra_label, extra_filters,
                                    round_digits, nocache, trace)

        # Add custom parameters if provided
        if custom_params:
            params.update(custom_params)

        response = await self.async_client.get(url, params=params)
        return self._process_response(response)

    async def health_async(self) -> bool:
        """
        Check if VictoriaMetrics is healthy and reachable (async).

        Returns:
            True if healthy, False otherwise
        """
        if not self.async_client:
            raise RuntimeError("Async support not available")
        try:
            getter = getattr(self.async_client, "get_text", self.async_client.get)
            return self._healthy_response(await getter(self._health_url()))
        except Exception:
            return False

    async def insert_async(
        self,
        data: Union[MetricsInsertData, Iterable[MetricsInsertData]],
        *,
        account_id: Optional[int] = None,
        custom_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Insert metrics data (VM-specific method, async).

        Note: This method is specific to VictoriaMetrics and is not available in Prometheus.
              Using PrometheusConfig will raise NotImplementedError.

        Args:
            data: Insert payload or an iterable of payloads
            account_id: [Cluster-only] Override account ID for this request.
                       Only valid for VMClusterConfig. Will raise ValueError for other config types.
            custom_params: [User-defined] Additional custom parameters for the request.
                          This parameter allows users to pass custom parameters to the request,
                          which can be used for calling modified versions of VM or other custom
                          implementations. No security validation is performed on these parameters.
                          Users are responsible for handling any security risks.

        Returns:
            Response from insert operation

        Raises:
            NotImplementedError: If using PrometheusConfig (Prometheus doesn't support insert)
            ValueError: If account_id is provided for non-cluster config
        """
        if not self.async_client:
            raise RuntimeError("Async support not available")

        base_url = self._get_insert_url_with_account(account_id)
        url = f"{base_url}/api/v1/import/prometheus"

        # Convert data to Prometheus format
        prometheus_data = self._convert_to_prometheus_format(data)

        # Prepare request parameters
        params = {}
        if custom_params:
            params.update(custom_params)

        response = await self.async_client.post(url, data=prometheus_data, params=params)
        return response

    # Helper methods
    def _prepare_query(self, query: Union[str, Any]) -> str:
        """Build SDK expressions for this backend; supplied text stays untouched."""
        if isinstance(query, QueryBuilder):
            mode = "promql" if self._config.db_type == DBType.PROMETHEUS else "metricsql"
            return query.build(mode=mode)
        if hasattr(query, 'build'):
            # External text producers retain their own construction contract.
            return query.build()
        return str(query)

    def _add_vm_specific_params(
        self,
        params: Dict[str, Any],
        extra_label: Optional[Union[str, Dict[str, str], Iterable[str]]] = None,
        extra_filters: Optional[Union[str, Iterable[str]]] = None,
        round_digits: Optional[int] = None,
        nocache: Optional[bool] = None,
        trace: Optional[bool] = None,
    ) -> None:
        """Add VictoriaMetrics-specific parameters to request params."""

        if extra_label is not None:
            if isinstance(extra_label, dict):
                label_parts = [f"{key}={value}" for key, value in extra_label.items()]
                params['extra_label'] = label_parts
            elif isinstance(extra_label, str):
                params['extra_label'] = extra_label
            else:
                params['extra_label'] = [str(item) for item in extra_label]

        if extra_filters is not None:
            if isinstance(extra_filters, str):
                params['extra_filters[]'] = extra_filters
            else:
                params['extra_filters[]'] = [str(item) for item in extra_filters]

        if round_digits is not None:
            params['round_digits'] = str(round_digits)

        if nocache:
            params['nocache'] = '1'

        if trace:
            params['trace'] = '1'

    def _process_response(self, response: Dict[str, Any]) -> MetricsQueryResult:
        """Process VM API response and convert to MetricsQueryResult."""
        return MetricsQueryResult.from_dict(response)

    def _convert_to_prometheus_format(
        self, data: Union[MetricsInsertData, Iterable[MetricsInsertData]]
    ) -> str:
        """Convert one or many insert payloads to Prometheus exposition format."""
        datasets: List[MetricsInsertData]
        if isinstance(data, MetricsInsertData):
            datasets = [data]
        else:
            datasets = list(data)
            if not datasets:
                raise ValueError("insert data iterable cannot be empty")

        lines: List[str] = []
        for dataset in datasets:
            if not isinstance(dataset, MetricsInsertData):
                raise TypeError("insert data must be MetricsInsertData or iterable of MetricsInsertData")
            dataset.validate()
            for time_val, value in zip(dataset.times, dataset.values):
                if time_val is None:
                    lines.append(f"{dataset.query} {value} ")
                    continue

                timestamp = ingestion_milliseconds(time_val)
                if timestamp is None:
                    lines.append(f"{dataset.query} {value} ")
                else:
                    lines.append(f"{dataset.query} {value} {timestamp}")
        return "\n".join(lines)

    @staticmethod
    def _extract_timeout_value(timeout: Optional[Any]) -> float:
        if isinstance(timeout, (tuple, list)):
            if not timeout:
                raise ValueError("Timeout tuple cannot be empty")
            return float(timeout[1] if len(timeout) > 1 else timeout[0])
        if timeout is None:
            return 30.0
        return float(timeout)

    def _prepare_match_params(self, match: Union[str, QueryBuilder, list]) -> list:
        """
        Convert match parameter to list of query strings.

        Args:
            match: Series selector(s) - string, QueryBuilder, or list of either

        Returns:
            List of query strings
        """
        if isinstance(match, list):
            return [self._prepare_query(item) for item in match]
        return [self._prepare_query(match)]

    # Metadata queries
    def series(
        self,
        match: Union[str, QueryBuilder, list],
        start: Optional[TimeValue] = None,
        end: Optional[TimeValue] = None,
        *,
        limit: Optional[int] = None,
        account_id: Optional[int] = None,
        custom_params: Optional[Dict[str, Any]] = None,
    ) -> SeriesResult:
        """
        Query series metadata.

        Args:
            match: Series selector(s). Can be:
                   - Single selector string: 'up{job="api"}'
                   - QueryBuilder instance
                   - List of selectors: ['up', 'process_cpu_seconds_total']
            start: Start timestamp (optional)
            end: End timestamp (optional)
            limit: Maximum number of returned series (optional, 0 means disabled)
            account_id: Override account ID for cluster configs
            custom_params: Additional custom parameters

        Returns:
            SeriesResult containing list of series with their label sets
        """
        base_url = self._get_query_url_with_account(account_id)
        url = f"{base_url}/api/v1/series"

        # Prepare match parameters
        match_list = self._prepare_match_params(match)
        params = {'match[]': match_list}

        if start is not None:
            params['start'] = self._normalize_time(start)
        if end is not None:
            params['end'] = self._normalize_time(end)
        if limit is not None:
            params['limit'] = str(limit)

        if custom_params:
            params.update(custom_params)

        response = self.client.get(url, params=params)
        return SeriesResult.from_dict(response)

    def labels(
        self,
        start: Optional[TimeValue] = None,
        end: Optional[TimeValue] = None,
        *,
        match: Optional[Union[str, QueryBuilder, list]] = None,
        limit: Optional[int] = None,
        account_id: Optional[int] = None,
        custom_params: Optional[Dict[str, Any]] = None,
    ) -> LabelsResult:
        """
        Query all label names.

        Args:
            start: Start timestamp (optional)
            end: End timestamp (optional)
            match: Series selector(s) to filter by (optional)
            limit: Maximum number of returned labels (optional, 0 means disabled)
            account_id: Override account ID for cluster configs
            custom_params: Additional custom parameters

        Returns:
            LabelsResult containing list of label names
        """
        base_url = self._get_query_url_with_account(account_id)
        url = f"{base_url}/api/v1/labels"

        params = {}

        if start is not None:
            params['start'] = self._normalize_time(start)
        if end is not None:
            params['end'] = self._normalize_time(end)
        if match is not None:
            match_list = self._prepare_match_params(match)
            params['match[]'] = match_list
        if limit is not None:
            params['limit'] = str(limit)

        if custom_params:
            params.update(custom_params)

        response = self.client.get(url, params=params)
        return LabelsResult.from_dict(response)

    def label_values(
        self,
        label_name: str,
        start: Optional[TimeValue] = None,
        end: Optional[TimeValue] = None,
        *,
        match: Optional[Union[str, QueryBuilder, list]] = None,
        limit: Optional[int] = None,
        account_id: Optional[int] = None,
        custom_params: Optional[Dict[str, Any]] = None,
    ) -> LabelValuesResult:
        """
        Query values for a specific label.

        Args:
            label_name: Name of the label to query values for
            start: Start timestamp (optional)
            end: End timestamp (optional)
            match: Series selector(s) to filter by (optional)
            limit: Maximum number of returned values (optional, 0 means disabled)
            account_id: Override account ID for cluster configs
            custom_params: Additional custom parameters

        Returns:
            LabelValuesResult containing list of label values
        """
        base_url = self._get_query_url_with_account(account_id)
        url = f"{base_url}/api/v1/label/{label_name}/values"

        params = {}

        if start is not None:
            params['start'] = self._normalize_time(start)
        if end is not None:
            params['end'] = self._normalize_time(end)
        if match is not None:
            match_list = self._prepare_match_params(match)
            params['match[]'] = match_list
        if limit is not None:
            params['limit'] = str(limit)

        if custom_params:
            params.update(custom_params)

        response = self.client.get(url, params=params)
        return LabelValuesResult.from_dict(response)

    # Async metadata queries
    async def series_async(
        self,
        match: Union[str, QueryBuilder, list],
        start: Optional[TimeValue] = None,
        end: Optional[TimeValue] = None,
        *,
        limit: Optional[int] = None,
        account_id: Optional[int] = None,
        custom_params: Optional[Dict[str, Any]] = None,
    ) -> SeriesResult:
        """Async variant of series()."""
        if self.async_client is None:
            raise RuntimeError("Async client is not configured")

        base_url = self._get_query_url_with_account(account_id)
        url = f"{base_url}/api/v1/series"

        match_list = self._prepare_match_params(match)
        params = {'match[]': match_list}

        if start is not None:
            params['start'] = self._normalize_time(start)
        if end is not None:
            params['end'] = self._normalize_time(end)
        if limit is not None:
            params['limit'] = str(limit)

        if custom_params:
            params.update(custom_params)

        response = await self.async_client.get(url, params=params)
        return SeriesResult.from_dict(response)

    async def labels_async(
        self,
        start: Optional[TimeValue] = None,
        end: Optional[TimeValue] = None,
        *,
        match: Optional[Union[str, QueryBuilder, list]] = None,
        limit: Optional[int] = None,
        account_id: Optional[int] = None,
        custom_params: Optional[Dict[str, Any]] = None,
    ) -> LabelsResult:
        """Async variant of labels()."""
        if self.async_client is None:
            raise RuntimeError("Async client is not configured")

        base_url = self._get_query_url_with_account(account_id)
        url = f"{base_url}/api/v1/labels"

        params = {}

        if start is not None:
            params['start'] = self._normalize_time(start)
        if end is not None:
            params['end'] = self._normalize_time(end)
        if match is not None:
            match_list = self._prepare_match_params(match)
            params['match[]'] = match_list
        if limit is not None:
            params['limit'] = str(limit)

        if custom_params:
            params.update(custom_params)

        response = await self.async_client.get(url, params=params)
        return LabelsResult.from_dict(response)

    async def label_values_async(
        self,
        label_name: str,
        start: Optional[TimeValue] = None,
        end: Optional[TimeValue] = None,
        *,
        match: Optional[Union[str, QueryBuilder, list]] = None,
        limit: Optional[int] = None,
        account_id: Optional[int] = None,
        custom_params: Optional[Dict[str, Any]] = None,
    ) -> LabelValuesResult:
        """Async variant of label_values()."""
        if self.async_client is None:
            raise RuntimeError("Async client is not configured")

        base_url = self._get_query_url_with_account(account_id)
        url = f"{base_url}/api/v1/label/{label_name}/values"

        params = {}

        if start is not None:
            params['start'] = self._normalize_time(start)
        if end is not None:
            params['end'] = self._normalize_time(end)
        if match is not None:
            match_list = self._prepare_match_params(match)
            params['match[]'] = match_list
        if limit is not None:
            params['limit'] = str(limit)

        if custom_params:
            params.update(custom_params)

        response = await self.async_client.get(url, params=params)
        return LabelValuesResult.from_dict(response)
