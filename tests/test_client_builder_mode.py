"""SDK expression arguments must use the client's selected backend before I/O."""
import pytest

from metricraft import DatabaseClient, HttpClientOptions, PrometheusConfig, VMSingleConfig
from metricraft import QueryBuilder as Q


class RecordingTransport:
    def __init__(self):
        self.calls = []

    def get(self, url, params=None):
        self.calls.append((url, params))
        return {"status": "success", "data": {"resultType": "vector", "result": []}}

    def close(self):
        pass


def test_prometheus_rejects_vm_builder_before_request_but_preserves_raw_text():
    transport = RecordingTransport()
    source = Q.from_metric("up")
    query = source.default(0)
    with DatabaseClient(PrometheusConfig("http://prom.invalid", http_options=HttpClientOptions(client=transport))) as client:
        for invoke in (
            lambda: client.query(query),
            lambda: client.query_range(query, start=0, end=60, step="1m"),
            lambda: client.series(query),
            lambda: client.series([query]),
        ):
            with pytest.raises(ValueError, match="MetricsQL"):
                invoke()
        assert not transport.calls
        # Stored strings belong to the application; the client never reparses them.
        text = query.build("metricsql")
        client.query(text)
        assert transport.calls[-1][1]["query"] == text
        client.query(Q.from_metric("histogram").histogram_count())
    assert source.build("promql") == "up"


@pytest.mark.asyncio
async def test_async_prometheus_uses_same_pre_request_dialect_contract():
    transport = RecordingTransport()
    query = Q.from_metric("up").default(0)
    async with DatabaseClient(PrometheusConfig("http://prom.invalid", http_options=HttpClientOptions(client=transport))) as client:
        with pytest.raises(ValueError, match="MetricsQL"):
            await client.query_async(query)
        with pytest.raises(ValueError, match="MetricsQL"):
            await client.query_range_async(query, start=0, end=60, step="1m")
    assert not transport.calls


def test_victoriametrics_keeps_its_dialect_for_builder_arguments():
    transport = RecordingTransport()
    query = Q.from_metric("up").default(0)
    with DatabaseClient(VMSingleConfig("http://vm.invalid", http_options=HttpClientOptions(client=transport))) as client:
        client.query(query)
        assert transport.calls[-1][1]["query"] == query.build("metricsql")
        with pytest.raises(ValueError, match="PromQL"):
            client.query(Q.from_metric("histogram").histogram_count())
    assert len(transport.calls) == 1


@pytest.mark.parametrize("container", [list, tuple])
def test_metadata_accepts_read_only_selector_sequences(container):
    transport = RecordingTransport()
    base = Q.from_metric("up").where_eq("job", "api")
    selectors = container([base, "process_cpu_seconds_total"])
    config = PrometheusConfig("http://prom.invalid", http_options=HttpClientOptions(client=transport))
    with DatabaseClient(config) as client:
        client.series(selectors)
        client.labels(match=selectors)
        client.label_values("job", match=selectors)
        for _, params in transport.calls:
            assert params["match[]"] == ['up{job="api"}', "process_cpu_seconds_total"]
        # The request normalizes a new collection; the caller's input is reusable.
        assert selectors[0] is base
        assert selectors[1] == "process_cpu_seconds_total"
        before = len(transport.calls)
        with pytest.raises(ValueError, match="MetricsQL"):
            client.series(container([base.default(0)]))
        assert len(transport.calls) == before
