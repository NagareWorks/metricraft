"""Exercise structural adapters through the public injection slots."""

from typing import Mapping, Optional
from io import BytesIO
import json
from types import MappingProxyType

import pytest

from metricraft import DatabaseClient, HttpClientOptions, PrometheusConfig, SyncHTTPTransport
from metricraft.client import AsyncHTTPClient, SyncHTTPClient
from metricraft.transports import HTTPBody, HTTPHeaders, HTTPParams, HTTPResponse, HTTPTimeout


class Adapter:
    """No inheritance and no generic request method: only the public contract."""

    def __init__(self):
        self.calls = []
        self.closed = 0

    def get(self, url: str, params: Optional[HTTPParams] = None, *,
            headers: Optional[HTTPHeaders] = None,
            timeout: Optional[HTTPTimeout] = None) -> HTTPResponse:
        self.calls.append(("GET", url, params, headers, timeout))
        return {"status": "success", "data": {"resultType": "vector", "result": []}}

    def post(self, url: str, data: HTTPBody = None,
             params: Optional[HTTPParams] = None, *,
             headers: Optional[HTTPHeaders] = None,
             timeout: Optional[HTTPTimeout] = None,
             content_type: Optional[str] = None) -> HTTPResponse:
        self.calls.append(("POST", url, data, params, headers, timeout, content_type))
        return {}

    def close(self) -> None:
        self.closed += 1


def test_default_transport_accepts_read_only_mapping_inputs():
    requests = []

    def opener(request, *, timeout):
        requests.append(request)
        return BytesIO(b'{"status": "success"}')

    params = MappingProxyType({"label": "api"})
    body = MappingProxyType({"message": "hello"})
    transport = SyncHTTPClient(opener=opener)
    assert transport.post("http://metrics.invalid/write", data=body, params=params) == {
        "status": "success"}
    assert requests[0].full_url == "http://metrics.invalid/write?label=api"
    assert json.loads(requests[0].data) == {"message": "hello"}
    assert dict(params) == {"label": "api"}
    assert dict(body) == {"message": "hello"}


@pytest.mark.asyncio
async def test_factory_context_and_owned_cleanup():
    sync = Adapter()
    contexts = []

    def make_sync(*, http_options: Mapping[str, object],
                  connection_info: Mapping[str, object]) -> SyncHTTPTransport:
        contexts.append((http_options, connection_info))
        return sync

    def make_async(*, http_options: Mapping[str, object],
                   connection_info: Mapping[str, object],
                   sync_client: SyncHTTPTransport) -> AsyncHTTPClient:
        assert sync_client is sync
        contexts.append((http_options, connection_info))
        return AsyncHTTPClient(sync_client=sync_client)

    config = PrometheusConfig("http://metrics.invalid", http_options=HttpClientOptions(
        timeout=(2, 5), default_headers={"X-Team": "metrics"},
        client_factory=make_sync, async_client_factory=make_async))
    async with DatabaseClient(config) as client:
        assert client.query("up").is_success
        assert (await client.query_async("up")).is_success
    assert sync.closed == 1
    assert len(contexts) == 2
    for options, connection in contexts:
        assert options["timeout"] == (2.0, 5.0)
        assert options["default_headers"] == {"X-Team": "metrics"}
        assert connection["url"] == "http://metrics.invalid"
    assert [call[2] for call in sync.calls] == [{"query": "up"}, {"query": "up"}]


@pytest.mark.asyncio
async def test_structural_adapter_preserves_async_request_options():
    sync = Adapter()
    bridge = AsyncHTTPClient(sync_client=sync)
    try:
        await bridge.get("http://metrics.invalid/query", {"query": "up"},
                         headers={"X-Trace": "1"}, timeout=(2, 3))
        await bridge.post("http://metrics.invalid/import", b"metric 1", {"extra": 1},
                          headers={"X-Trace": "2"}, timeout=(3, 4), content_type="text/plain")
        assert sync.calls == [
            ("GET", "http://metrics.invalid/query", {"query": "up"}, {"X-Trace": "1"}, (2, 3)),
            ("POST", "http://metrics.invalid/import", b"metric 1", {"extra": 1},
             {"X-Trace": "2"}, (3, 4), "text/plain"),
        ]
    finally:
        await bridge.aclose()
    assert sync.closed == 0  # The bridge borrows the adapter; DatabaseClient owns it.


@pytest.mark.asyncio
async def test_injected_instances_take_precedence_over_factories():
    sync = Adapter()
    bridge = AsyncHTTPClient(sync_client=sync)

    def unused(**kwargs):
        pytest.fail("Factories must not run when an instance is supplied")

    options = HttpClientOptions(client=sync, async_client=bridge,
                                client_factory=unused, async_client_factory=unused)
    async with DatabaseClient(PrometheusConfig("http://metrics.invalid", http_options=options)) as client:
        assert client.client is sync
        assert client.async_client is bridge
        assert (await client.query_async("up")).is_success
    assert sync.closed == 1
