"""Concrete HTTP transports for Prometheus and VictoriaMetrics.

Features
- Synchronous and asynchronous helpers implemented with urllib + ThreadPoolExecutor
- Parameter normalization: filters None and stringifies values; sequences become repeated parameters
- Error mapping to framework exceptions (MCHTTPError/TimeoutError/ConnectionError)
- Configurable headers, hooks, and masking helpers for safer customization
"""

import asyncio
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Set, Tuple, Union
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from metricraft.exceptions import ConnectionError, MCHTTPError, TimeoutError


HeadersInput = Optional[Mapping[str, Union[str, int, float]]]
PrepareRequestHook = Optional[Callable[[Request], Optional[Request]]]
TimeoutType = Union[float, int, Tuple[Union[float, int], Union[float, int]]]
HTTPBody = Optional[Union[Dict[str, Any], str, bytes]]
HTTPMethod = str


_SENSITIVE_HEADER_PARTS = (
    "auth",
    "token",
    "key",
    "secret",
    "cookie",
    "password",
    "signature",
)

_logger = logging.getLogger(__name__)

_DEFAULT_RETRY_STATUS_CODES: Set[int] = {429, 500, 502, 503, 504}
_DEFAULT_RETRY_METHODS: Set[str] = {
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "HEAD",
    "OPTIONS",
}


def _prepare_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize query params for HTTP requests.

    Rules
    - Drop keys with None values
    - Convert non-None values to strings
    - Preserve lists/tuples for repeated query parameters
    """
    clean_params = {}
    for key, value in params.items():
        if value is not None:
            if isinstance(value, (list, tuple)):
                clean_params[key] = [str(v) for v in value if v is not None]
            else:
                clean_params[key] = str(value)
    return clean_params


def mask_sensitive_headers(headers: HeadersInput, placeholder: str = "******") -> Dict[str, str]:
    """Mask sensitive headers for safe logging or debugging.

    Args:
        headers: Mapping of header names to values.
        placeholder: Replacement text for sensitive headers.

    Returns:
        New dict with potentially sensitive header values masked.
    """

    if not headers:
        return {}

    masked: Dict[str, str] = {}
    for key, value in headers.items():
        value_str = str(value)
        if any(part in key.lower() for part in _SENSITIVE_HEADER_PARTS):
            masked[key] = placeholder
        else:
            masked[key] = value_str
    return masked


def _normalize_timeout(timeout: Optional[TimeoutType]) -> Tuple[float, float]:
    """Normalize timeout input to (connect, read) tuple."""

    if timeout is None:
        return (30.0, 30.0)

    if isinstance(timeout, (tuple, list)):
        if len(timeout) == 0:
            raise ValueError("Timeout tuple cannot be empty")
        if len(timeout) == 1:
            connect = read = float(timeout[0])
        else:
            connect = float(timeout[0])
            read = float(timeout[1])
    else:
        connect = read = float(timeout)

    if connect <= 0 or read <= 0:
        raise ValueError("Timeout values must be positive")

    return (connect, read)

_HEADER_CASE_OVERRIDES = {
    "Content-Type": "Content-type",
}


def _canonical_header_name(name: str) -> str:
    if not name:
        return name
    parts = str(name).split('-')
    canonical_parts = []
    for part in parts:
        if not part:
            canonical_parts.append(part)
            continue
        canonical_parts.append(part[0].upper() + part[1:])
    canonical = '-'.join(canonical_parts)
    return _HEADER_CASE_OVERRIDES.get(canonical, canonical)


def _normalize_headers(headers: HeadersInput) -> Dict[str, str]:
    if not headers:
        return {}
    normalized: Dict[str, str] = {}
    for key, value in headers.items():
        canonical = _canonical_header_name(key)
        normalized[canonical] = str(value)
    return normalized


def _canonicalize_request_headers(request: Request) -> None:
    if hasattr(request, "headers"):
        headers_dict = request.headers
        items = list(headers_dict.items())
        headers_dict.clear()
        for key, value in items:
            canonical = _canonical_header_name(key)
            headers_dict[canonical] = str(value)

    if hasattr(request, "unredirected_hdrs"):
        unredirected = request.unredirected_hdrs
        items = list(unredirected.items())
        unredirected.clear()
        for key, value in items:
            canonical = _canonical_header_name(key)
            unredirected[canonical] = str(value)


def _apply_params(url: str, params: Optional[Dict[str, Any]]) -> str:
    if not params:
        return url

    clean_params = _prepare_params(params)
    if not clean_params:
        return url

    separator = '&' if '?' in url else '?'
    return f"{url}{separator}{urlencode(clean_params, doseq=True)}"


def _has_header(headers: Dict[str, str], target: str) -> bool:
    target_lower = target.lower()
    return any(key.lower() == target_lower for key in headers.keys())


class SyncHTTPClient:
    """Synchronous HTTP helper.

    Args:
        timeout: Socket timeout in seconds or a ``(connect, read)`` tuple.
        default_headers: Headers applied to every request.
        prepare_request: Optional hook to customize the prepared request before sending.
        opener: Optional callable compatible with :func:`urllib.request.urlopen`.
        retries: Number of attempts before giving up (``>= 1``).
        backoff_factor: Exponential backoff factor (sleep = factor * 2**(attempt-1)).
        max_backoff: Optional cap for backoff delay seconds.
        retry_statuses: Iterable of HTTP status codes that should be retried.
        retry_methods: Iterable of HTTP methods allowed to retry.
    """

    def __init__(
        self,
        timeout: Optional[TimeoutType] = 30,
        *,
        default_headers: HeadersInput = None,
        prepare_request: PrepareRequestHook = None,
        opener: Optional[Callable[..., Any]] = None,
        retries: int = 3,
        backoff_factor: float = 0.5,
        max_backoff: Optional[float] = 8.0,
        retry_statuses: Optional[Iterable[int]] = None,
        retry_methods: Optional[Iterable[str]] = None,
    ):
        connect_timeout, read_timeout = _normalize_timeout(timeout)
        self.connect_timeout = connect_timeout
        self.timeout = read_timeout
        self._default_headers = _normalize_headers(default_headers)
        self._prepare_request_hook = prepare_request
        self._opener = opener
        self._closed = False
        if retries < 1:
            raise ValueError("retries must be >= 1")
        if backoff_factor < 0:
            raise ValueError("backoff_factor must be >= 0")
        if max_backoff is not None and max_backoff < 0:
            raise ValueError("max_backoff must be >= 0 when provided")
        configured_methods = retry_methods or _DEFAULT_RETRY_METHODS
        if not configured_methods:
            raise ValueError("retry_methods cannot be empty")
        self._max_attempts = retries
        self._backoff_factor = backoff_factor
        self._max_backoff = max_backoff
        self._retry_statuses = set(retry_statuses) if retry_statuses is not None else set(_DEFAULT_RETRY_STATUS_CODES)
        self._retry_methods = {method.upper() for method in configured_methods}

    def request(
        self,
        method: HTTPMethod,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        data: HTTPBody = None,
        headers: HeadersInput = None,
        timeout: Optional[TimeoutType] = None,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        method_upper = method.upper()
        body, resolved_content_type = self._encode_body(data, content_type)
        return self._execute(
            method=method_upper,
            url=url,
            params=params,
            headers=headers,
            body=body,
            timeout=timeout,
            default_content_type=resolved_content_type,
        )

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    def _build_request(
        self,
        url: str,
        *,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        headers: HeadersInput = None,
        body: Optional[bytes] = None,
        default_content_type: Optional[str] = None,
    ) -> Request:
        final_url = _apply_params(url, params)
        request = Request(final_url, data=body, method=method)

        merged_headers = {**self._default_headers, **_normalize_headers(headers)}
        if default_content_type and not _has_header(merged_headers, "Content-Type"):
            merged_headers[_canonical_header_name("Content-Type")] = default_content_type

        for key, value in merged_headers.items():
            request.add_header(key, value)
            if hasattr(request, "headers"):
                headers_dict = request.headers
                for existing_key in list(headers_dict.keys()):
                    if existing_key.lower() == key.lower() and existing_key != key:
                        headers_dict.pop(existing_key, None)
                headers_dict[key] = str(value)

        if self._prepare_request_hook:
            updated = self._prepare_request_hook(request)
            if isinstance(updated, Request):
                request = updated
            _canonicalize_request_headers(request)
        return request

    def _encode_body(
        self,
        data: HTTPBody,
        explicit_content_type: Optional[str],
    ) -> Tuple[Optional[bytes], Optional[str]]:
        if data is None:
            if explicit_content_type:
                return None, explicit_content_type
            return None, None

        if isinstance(data, bytes):
            return data, explicit_content_type or "application/octet-stream"

        if isinstance(data, str):
            return data.encode("utf-8"), explicit_content_type or "text/plain"

        if isinstance(data, Mapping):
            return json.dumps(data).encode("utf-8"), explicit_content_type or "application/json"

        raise TypeError("Unsupported request body type; expected bytes, str, or mapping")

    def _resolve_timeouts(self, timeout: Optional[TimeoutType]) -> Tuple[float, float]:
        if timeout is None:
            return self.connect_timeout, self.timeout
        return _normalize_timeout(timeout)

    def _execute(
        self,
        *,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]],
        headers: HeadersInput,
        body: Optional[bytes],
        timeout: Optional[TimeoutType],
        default_content_type: Optional[str],
        text_response: bool = False,
    ) -> Union[Dict[str, Any], str]:
        connect_timeout, read_timeout = self._resolve_timeouts(timeout)
        opener = self._opener or urlopen
        if connect_timeout != read_timeout:
            if self._opener is not None:
                raise ValueError("Unequal connect/read timeouts require the default opener or a custom HTTP client")
            from ._timeouts import phased_opener
            opener = phased_opener(read_timeout)
        attempt = 1

        while True:
            request = self._build_request(
                url,
                method=method,
                params=params,
                headers=headers,
                body=body,
                default_content_type=default_content_type,
            )

            try:
                with opener(request, timeout=connect_timeout) as response:
                    raw = response.read().decode("utf-8")
                    if text_response:
                        return raw
                    if not raw:
                        return {}
                    return json.loads(raw)

            except HTTPError as err:
                http_error = self._create_mc_http_error(request, err)
                if not self._should_retry(method, attempt, http_error, err.code):
                    raise http_error
                self._sleep_before_retry(attempt)
                attempt += 1

            except (URLError, OSError) as exc:
                translated_error = self._translate_network_error(exc)
                if not self._should_retry(method, attempt, translated_error):
                    raise translated_error
                self._sleep_before_retry(attempt)
                attempt += 1

    def _create_mc_http_error(self, request: Request, err: HTTPError) -> MCHTTPError:
        error_data: Dict[str, Any] = {}
        try:
            error_body = err.read().decode("utf-8")
            error_data = json.loads(error_body) if error_body else {}
        except (json.JSONDecodeError, UnicodeDecodeError):
            error_data = {}

        masked_headers = mask_sensitive_headers(dict(request.header_items()))
        _logger.debug(
            "HTTP %s %s failed: %s headers=%s",
            request.get_method(),
            request.full_url,
            err,
            masked_headers,
        )
        return MCHTTPError(err.code, str(err.reason), error_data)

    def _translate_network_error(self, exc: Union[URLError, OSError]) -> Exception:
        message = str(exc).lower()
        if "timed out" in message or "timeout" in message:
            return TimeoutError(f"Request timeout: {exc}")
        return ConnectionError(f"Connection error: {exc}")

    def _should_retry(
        self,
        method: str,
        attempt: int,
        error: Exception,
        status_code: Optional[int] = None,
    ) -> bool:
        if attempt >= self._max_attempts:
            return False

        if method.upper() not in self._retry_methods:
            return False

        if isinstance(error, (TimeoutError, ConnectionError)):
            return True

        if isinstance(error, MCHTTPError):
            code = status_code if status_code is not None else getattr(error, "status_code", None)
            if code is not None and code in self._retry_statuses:
                return True

        return False

    def _sleep_before_retry(self, attempt: int) -> None:
        if self._backoff_factor <= 0:
            return

        delay = self._backoff_factor * (2 ** (attempt - 1))
        if self._max_backoff is not None:
            delay = min(delay, self._max_backoff)

        if delay > 0:
            time.sleep(delay)

    def close(self) -> None:
        """Idempotent close hook for API symmetry with async client."""
        self._closed = True

    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        headers: HeadersInput = None,
        timeout: Optional[TimeoutType] = None,
    ) -> Dict[str, Any]:
        return self.request(
            "GET",
            url,
            params=params,
            headers=headers,
            timeout=timeout,
        )

    def get_text(self, url: str) -> str:
        """GET a plain-text endpoint using the same headers, retries and timeout."""
        return self._execute(method="GET", url=url, params=None, headers=None,
                             body=None, timeout=None, default_content_type=None,
                             text_response=True)

    def post(
        self,
        url: str,
        data: HTTPBody = None,
        params: Optional[Dict[str, Any]] = None,
        *,
        headers: HeadersInput = None,
        timeout: Optional[TimeoutType] = None,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.request(
            "POST",
            url,
            params=params,
            data=data,
            headers=headers,
            timeout=timeout,
            content_type=content_type,
        )

    def put(
        self,
        url: str,
        data: HTTPBody = None,
        params: Optional[Dict[str, Any]] = None,
        *,
        headers: HeadersInput = None,
        timeout: Optional[TimeoutType] = None,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.request(
            "PUT",
            url,
            params=params,
            data=data,
            headers=headers,
            timeout=timeout,
            content_type=content_type,
        )

    def patch(
        self,
        url: str,
        data: HTTPBody = None,
        params: Optional[Dict[str, Any]] = None,
        *,
        headers: HeadersInput = None,
        timeout: Optional[TimeoutType] = None,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.request(
            "PATCH",
            url,
            params=params,
            data=data,
            headers=headers,
            timeout=timeout,
            content_type=content_type,
        )

    def delete(
        self,
        url: str,
        data: HTTPBody = None,
        params: Optional[Dict[str, Any]] = None,
        *,
        headers: HeadersInput = None,
        timeout: Optional[TimeoutType] = None,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.request(
            "DELETE",
            url,
            params=params,
            data=data,
            headers=headers,
            timeout=timeout,
            content_type=content_type,
        )

    def head(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        headers: HeadersInput = None,
        timeout: Optional[TimeoutType] = None,
    ) -> Dict[str, Any]:
        return self.request(
            "HEAD",
            url,
            params=params,
            headers=headers,
            timeout=timeout,
        )

    def options(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        headers: HeadersInput = None,
        timeout: Optional[TimeoutType] = None,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.request(
            "OPTIONS",
            url,
            params=params,
            headers=headers,
            timeout=timeout,
            content_type=content_type,
        )


class AsyncHTTPClient:
    """Asynchronous HTTP helper using stdlib + thread pool.

    Args:
        timeout: Socket timeout in seconds or tuple passed to the underlying sync client.
        max_workers: Number of threads in the executor.
        executor: Optional external executor to reuse (will not be shutdown).
        sync_client: Optional transport to borrow; its owner remains responsible for closing it.
    """

    def __init__(
        self,
        timeout: Optional[TimeoutType] = 30,
        *,
        max_workers: int = 4,
        executor: Optional[ThreadPoolExecutor] = None,
        sync_client: Optional[Any] = None,
    ):
        self._owns_sync_client = sync_client is None
        self.sync_client = SyncHTTPClient(timeout=timeout) if sync_client is None else sync_client
        self._executor = executor or ThreadPoolExecutor(max_workers=max_workers)
        self._owns_executor = executor is None
        self._closed = False

    @staticmethod
    def _get_event_loop() -> asyncio.AbstractEventLoop:
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.get_event_loop()

    async def request(
        self,
        method: HTTPMethod,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        data: HTTPBody = None,
        headers: HeadersInput = None,
        timeout: Optional[TimeoutType] = None,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Make an async request, delegating to the configured sync client."""

        def _sync_call() -> Dict[str, Any]:
            if hasattr(self.sync_client, "request"):
                return self.sync_client.request(
                    method,
                    url,
                    params=params,
                    data=data,
                    headers=headers,
                    timeout=timeout,
                    content_type=content_type,
                )

            method_upper = method.upper()
            if method_upper == "GET" and hasattr(self.sync_client, "get"):
                return self.sync_client.get(
                    url,
                    params,
                    headers=headers,
                    timeout=timeout,
                )
            if method_upper == "POST" and hasattr(self.sync_client, "post"):
                return self.sync_client.post(
                    url,
                    data,
                    params,
                    headers=headers,
                    timeout=timeout,
                )
            raise AttributeError(
                "Configured sync_client does not provide a compatible request interface"
            )

        try:
            loop = self._get_event_loop()
            return await loop.run_in_executor(self._executor, _sync_call)
        except Exception as exc:
            message = str(exc).lower()
            if "timeout" in message:
                raise TimeoutError(f"Async request timeout: {exc}")
            if isinstance(exc, (MCHTTPError, TimeoutError, ConnectionError)):
                raise exc
            raise ConnectionError(f"Async connection error: {exc}")

    def __del__(self):
        """Clean up thread pool executor."""
        try:
            self.close()
        except Exception:
            pass

    def close(self) -> None:
        """Release the owned executor and any internally created sync client."""
        if self._closed:
            return
        self._closed = True
        if self._owns_sync_client and hasattr(self.sync_client, "close"):
            try:
                self.sync_client.close()  # type: ignore[attr-defined]
            except Exception:  # pragma: no cover - defensive guard during shutdown
                _logger.debug("Unhandled exception while closing sync_client", exc_info=True)
        if (
            hasattr(self, "_executor")
            and self._executor
            and getattr(self, "_owns_executor", False)
        ):
            self._executor.shutdown(wait=False)

    async def aclose(self) -> None:
        """Async variant mirroring :meth:`close`."""
        self.close()

    async def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        headers: HeadersInput = None,
        timeout: Optional[TimeoutType] = None,
    ) -> Dict[str, Any]:
        return await self.request(
            "GET",
            url,
            params=params,
            headers=headers,
            timeout=timeout,
        )

    async def get_text(self, url: str) -> str:
        """Read a plain-text endpoint through the configured sync transport."""
        loop = self._get_event_loop()
        getter = getattr(self.sync_client, "get_text", self.sync_client.get)
        return await loop.run_in_executor(self._executor, lambda: getter(url))

    async def post(
        self,
        url: str,
        data: HTTPBody = None,
        params: Optional[Dict[str, Any]] = None,
        *,
        headers: HeadersInput = None,
        timeout: Optional[TimeoutType] = None,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self.request(
            "POST",
            url,
            params=params,
            data=data,
            headers=headers,
            timeout=timeout,
            content_type=content_type,
        )

    async def put(
        self,
        url: str,
        data: HTTPBody = None,
        params: Optional[Dict[str, Any]] = None,
        *,
        headers: HeadersInput = None,
        timeout: Optional[TimeoutType] = None,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self.request(
            "PUT",
            url,
            params=params,
            data=data,
            headers=headers,
            timeout=timeout,
            content_type=content_type,
        )

    async def patch(
        self,
        url: str,
        data: HTTPBody = None,
        params: Optional[Dict[str, Any]] = None,
        *,
        headers: HeadersInput = None,
        timeout: Optional[TimeoutType] = None,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self.request(
            "PATCH",
            url,
            params=params,
            data=data,
            headers=headers,
            timeout=timeout,
            content_type=content_type,
        )

    async def delete(
        self,
        url: str,
        data: HTTPBody = None,
        params: Optional[Dict[str, Any]] = None,
        *,
        headers: HeadersInput = None,
        timeout: Optional[TimeoutType] = None,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self.request(
            "DELETE",
            url,
            params=params,
            data=data,
            headers=headers,
            timeout=timeout,
            content_type=content_type,
        )

    async def head(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        headers: HeadersInput = None,
        timeout: Optional[TimeoutType] = None,
    ) -> Dict[str, Any]:
        return await self.request(
            "HEAD",
            url,
            params=params,
            headers=headers,
            timeout=timeout,
        )

    async def options(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        headers: HeadersInput = None,
        timeout: Optional[TimeoutType] = None,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self.request(
            "OPTIONS",
            url,
            params=params,
            headers=headers,
            timeout=timeout,
            content_type=content_type,
        )
