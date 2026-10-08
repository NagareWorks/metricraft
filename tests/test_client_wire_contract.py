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
