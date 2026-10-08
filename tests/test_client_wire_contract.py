"""Verify actual encoded requests and plain-text responses at the urllib boundary."""
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

import pytest

from metricraft import (DatabaseClient, HttpClientOptions, MetricsInsertData,
                       PrometheusConfig, VMClusterConfig, VMSingleConfig)


class Wire:
    def __init__(self):
        self.requests = []
        self.error = False

    def __call__(self, request, **kwargs):
        self.requests.append(request)
        if self.error:
            raise HTTPError(request.full_url, 503, "unhealthy", {}, None)
        path = urlsplit(request.full_url).path
        payload = (b"OK" if path.endswith("/health") else
                   b"Prometheus Server is Healthy.\n" if path.endswith("/-/healthy") else
                   b"" if path.endswith("/import/prometheus") else
                   b'{"status":"success","data":{"resultType":"vector","result":[]}}')

        class Reply:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def read(self):
                return payload

        return Reply()


@pytest.mark.asyncio
@pytest.mark.parametrize("kind,path", [("single", "/proxy/health"),
                                      ("cluster", "/proxy/health"),
                                      ("prometheus", "/proxy/-/healthy")])
async def test_health_uses_plain_text_and_server_path(kind, path):
    wire = Wire()
    options = HttpClientOptions(opener=wire)
    url = "http://metrics.invalid/proxy"
    config = (VMClusterConfig(url, url, url, account_id=42, http_options=options)
              if kind == "cluster" else
              PrometheusConfig(url, http_options=options) if kind == "prometheus" else
              VMSingleConfig(url, http_options=options))
    async with DatabaseClient(config) as client:
        assert client.health()
        assert await client.health_async()
        assert all(urlsplit(r.full_url).path == path for r in wire.requests)
        wire.error = True
        assert not client.health()
        assert not await client.health_async()


@pytest.mark.asyncio
async def test_repeated_parameters_preserve_delimiters_sync_and_async():
    wire = Wire()
    config = VMSingleConfig("http://metrics.invalid", http_options=HttpClientOptions(opener=wire))
    async with DatabaseClient(config) as client:
        for call in (client.query, client.query_async):
            result = call("up", extra_label={"job": "api,worker", "note": "a&b"},
                          extra_filters=['{job="api,worker"}', '{note="a&b"}'])
            if call == client.query_async:
                await result
            params = parse_qs(urlsplit(wire.requests[-1].full_url).query)
            assert params["extra_label"] == ["job=api,worker", "note=a&b"]
            assert params["extra_filters[]"] == ['{job="api,worker"}', '{note="a&b"}']


@pytest.mark.asyncio
async def test_fractional_instant_and_range_times_survive_transport():
    wire = Wire()
    config = PrometheusConfig("http://metrics.invalid", http_options=HttpClientOptions(opener=wire))
    async with DatabaseClient(config) as client:
        for call in (client.query, client.query_async):
            result = call("up", time=1700000000.125)
            if call == client.query_async:
                await result
            assert parse_qs(urlsplit(wire.requests[-1].full_url).query)["time"] == ["1700000000.125"]
        for call in (client.query_range, client.query_range_async):
            result = call("up", start=1700000000.125, end=1700000000.875, step="0.25")
            if call == client.query_range_async:
                await result
            params = parse_qs(urlsplit(wire.requests[-1].full_url).query)
            assert params["start"] == ["1700000000.125"]
            assert params["end"] == ["1700000000.875"]


@pytest.mark.asyncio
@pytest.mark.parametrize("timestamp", [1767225600.125, 1767225600125,
                                      "1767225600.125", "2026-01-01T00:00:00.125Z",
                                      datetime(2026, 1, 1, microsecond=125000, tzinfo=timezone.utc)])
async def test_insert_writes_milliseconds_sync_and_async(timestamp):
    wire = Wire()
    config = VMSingleConfig("http://metrics.invalid", http_options=HttpClientOptions(opener=wire))
    sample = MetricsInsertData("example_metric", [timestamp], [2])
    async with DatabaseClient(config) as client:
        client.insert(sample)
        await client.insert_async(sample)
        assert [r.data for r in wire.requests] == [b"example_metric 2 1767225600125"] * 2


@pytest.mark.parametrize("timestamp", ["now-1h", float("nan"), float("inf")])
def test_invalid_ingestion_time_is_rejected_before_io(timestamp):
    wire = Wire()
    config = VMSingleConfig("http://metrics.invalid", http_options=HttpClientOptions(opener=wire))
    with DatabaseClient(config) as client, pytest.raises(ValueError):
        client.insert(MetricsInsertData("example_metric", [timestamp], [2]))
    assert not wire.requests


@pytest.mark.asyncio
@pytest.mark.parametrize("end", ["2026-01-01T00:00:00.125Z", "1767225600.125"])
async def test_default_range_start_is_relative_to_absolute_string_end(end):
    wire = Wire()
    config = PrometheusConfig("http://metrics.invalid", http_options=HttpClientOptions(opener=wire))
    async with DatabaseClient(config) as client:
        client.query_range("up", end=end)
        await client.query_range_async("up", end=end)
    for request in wire.requests:
        params = parse_qs(urlsplit(request.full_url).query)
        assert params["start"] == ["1767222000.125"]
        assert params["end"] == [end]


def test_relative_end_requires_explicit_start_before_io():
    wire = Wire()
    config = VMSingleConfig("http://metrics.invalid", http_options=HttpClientOptions(opener=wire))
    with DatabaseClient(config) as client:
        with pytest.raises(ValueError, match="start explicitly"):
            client.query_range("up", end="now-1d")
        client.query_range("up", start="now-2d", end="now-1d")
    assert len(wire.requests) == 1


def test_connection_and_read_budgets_are_applied_in_distinct_phases(monkeypatch):
    from http.client import HTTPConnection, HTTPSConnection
    from unittest.mock import Mock
    from urllib.request import Request
    from metricraft.client._timeouts import phased_opener

    connections = []

    def connect(connection):
        connections.append((type(connection).__mro__, connection.timeout))
        connection.sock = Mock()

    def send(handler, connection_type, request, **kwargs):
        connection = connection_type("example.invalid", timeout=request.timeout, **kwargs)
        connection.connect()
        connection.sock.settimeout.assert_called_once_with(120)
        return connection

    monkeypatch.setattr(HTTPConnection, "connect", connect)
    monkeypatch.setattr(HTTPSConnection, "connect", connect)
    from urllib.request import AbstractHTTPHandler
    monkeypatch.setattr(AbstractHTTPHandler, "do_open", send)
    opener = phased_opener(120).__self__
    for scheme in ("http", "https"):
        request = Request(scheme + "://example.invalid")
        request.timeout = 1
        handler = next(h for h in opener.handlers if hasattr(h, scheme + "_open")
                       and type(h).__name__ in ("PlainHandler", "SecureHandler"))
        getattr(handler, scheme + "_open")(request)
    assert len(connections) == 2
    assert all(timeout == 1 for _, timeout in connections)


def test_unequal_timeouts_with_custom_opener_fail_before_io():
    from metricraft.client.http_client import SyncHTTPClient
    wire = Wire()
    client = SyncHTTPClient(timeout=(1, 120), opener=wire)
    with pytest.raises(ValueError, match="custom HTTP client"):
        client.get("http://metrics.invalid")
    assert not wire.requests


@pytest.mark.asyncio
async def test_read_budget_can_exceed_connect_budget_on_a_real_socket():
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from threading import Thread
    import time
    from metricraft.client.http_client import AsyncHTTPClient, SyncHTTPClient

    class SlowResponse(BaseHTTPRequestHandler):
        def do_GET(self):
            time.sleep(0.3)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"ok":true}')

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), SlowResponse)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    sync = SyncHTTPClient(timeout=(0.2, 2), retries=1)
    async_ = AsyncHTTPClient(sync_client=sync)
    try:
        url = "http://127.0.0.1:" + str(server.server_port)
        assert sync.get(url) == {"ok": True}
        assert await async_.get(url) == {"ok": True}
    finally:
        await async_.aclose()
        sync.close()
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
