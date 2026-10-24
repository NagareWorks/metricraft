"""Structural contracts for replaceable HTTP transports and their factories.

Implement these methods on an adapter; inheritance is not required. Responses
are decoded JSON objects, not HTTP-library response instances. Cleanup and
plain-text health checks are optional capabilities documented in the client guide.
"""

from typing import Dict, Mapping, Optional, Protocol, Tuple, Union


HTTPHeaders = Mapping[str, Union[str, int, float]]
HTTPTimeout = Union[int, float, Tuple[Union[int, float], Union[int, float]]]
HTTPParams = Mapping[str, object]
HTTPResponse = Dict[str, object]
HTTPBody = Optional[Union[Mapping[str, object], str, bytes]]


class SyncHTTPTransport(Protocol):
    """Synchronous JSON transport used by DatabaseClient and its async bridge."""

    def get(self, url: str, params: Optional[HTTPParams] = None, *,
            headers: Optional[HTTPHeaders] = None,
            timeout: Optional[HTTPTimeout] = None) -> HTTPResponse: ...

    def post(self, url: str, data: HTTPBody = None,
             params: Optional[HTTPParams] = None, *,
             headers: Optional[HTTPHeaders] = None,
             timeout: Optional[HTTPTimeout] = None,
             content_type: Optional[str] = None) -> HTTPResponse: ...


class AsyncHTTPTransport(Protocol):
    """Asynchronous JSON transport; get and post must be awaitable."""

    async def get(self, url: str, params: Optional[HTTPParams] = None, *,
                  headers: Optional[HTTPHeaders] = None,
                  timeout: Optional[HTTPTimeout] = None) -> HTTPResponse: ...

    async def post(self, url: str, data: HTTPBody = None,
                   params: Optional[HTTPParams] = None, *,
                   headers: Optional[HTTPHeaders] = None,
                   timeout: Optional[HTTPTimeout] = None,
                   content_type: Optional[str] = None) -> HTTPResponse: ...


class SyncHTTPTransportFactory(Protocol):
    """Construct a sync transport from normalized options and connection settings."""

    def __call__(self, *, http_options: Mapping[str, object],
                 connection_info: Mapping[str, object]) -> SyncHTTPTransport: ...


class AsyncHTTPTransportFactory(Protocol):
    """Construct an async transport synchronously, optionally borrowing sync_client."""

    def __call__(self, *, http_options: Mapping[str, object],
                 connection_info: Mapping[str, object],
                 sync_client: SyncHTTPTransport) -> AsyncHTTPTransport: ...


__all__ = [
    "HTTPHeaders", "HTTPTimeout", "HTTPParams", "HTTPResponse", "HTTPBody",
    "SyncHTTPTransport", "AsyncHTTPTransport",
    "SyncHTTPTransportFactory", "AsyncHTTPTransportFactory",
]
