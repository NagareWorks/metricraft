"""Exercise sharing, native thread-local errors and concurrent resource release."""
import asyncio
import gc
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Lock
import weakref

import pytest

from metricraft import DatabaseClient, HttpClientOptions, PrometheusConfig, QueryBuilder as Q
from metricraft.client import AsyncHTTPClient


def test_shared_roots_can_be_derived_rendered_and_released_across_threads():
    base = Q.from_metric("up").where_eq("env", "prod")
    start = Barrier(4)

    def branch(worker):
        refs = []
        start.wait(timeout=15)
        for index in range(32):
            value = "{}-{}".format(worker, index)
            query = base.where_eq("worker", value).sum().by("env")
            refs.append(weakref.ref(query))
            assert query.build("promql") == 'sum by (env) (up{env="prod",worker="' + value + '"})'
            with pytest.raises(ValueError):
                query.build("promql", max_output_bytes=1)
        return refs

    with ThreadPoolExecutor(max_workers=4) as pool:
        refs = [ref for batch in pool.map(branch, range(4)) for ref in batch]
    gc.collect()  # Free-threaded CPython may defer reference-count reclamation.
    assert all(ref() is None for ref in refs)
    assert base.build("promql") == 'up{env="prod"}'


def test_native_errors_survive_other_threads_before_the_error_is_read(monkeypatch):
    from metricraft import _native

    rendezvous = Barrier(4)
    original_check = _native.check

    def read_after_other_threads_fail():
        rendezvous.wait(timeout=15)
        original_check()

    monkeypatch.setattr(_native, "check", read_after_other_threads_fail)
    base = Q.from_metric("up")

    def fail(worker):
        name = "missing_worker_" + str(worker)
        for _ in range(16):
            with pytest.raises(ValueError, match=name):
                Q.function(name, base)

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(fail, range(4)))
    assert base.build("promql") == "up"


class ClosingTransport:
    def __init__(self):
        self.count = 0
        self.lock = Lock()
        self.on_close = lambda: None

    def close(self):
        with self.lock:
            self.count += 1
        self.on_close()

    async def aclose(self):
        await asyncio.sleep(0)
        self.close()


def test_concurrent_sync_and_async_close_claim_each_transport_once():
    with ThreadPoolExecutor(max_workers=8) as pool:
        for _ in range(24):
            sync, async_ = ClosingTransport(), ClosingTransport()
            client = DatabaseClient(PrometheusConfig(
                "http://metrics.invalid", http_options=HttpClientOptions(client=sync, async_client=async_)))
            # Cleanup callbacks must be able to close the same owner again.
            sync.on_close = client.close
            start = Barrier(8)

            def close(worker):
                start.wait(timeout=15)
                if worker % 2:
                    asyncio.run(client.aclose())
                else:
                    client.close()

            list(pool.map(close, range(8)))
            assert client.closed
            assert sync.count == async_.count == 1
            assert not client._finalizer.alive


def test_async_http_wrapper_closes_its_owned_transport_once(monkeypatch):
    transport = ClosingTransport()
    monkeypatch.setattr("metricraft.client.http_client.SyncHTTPClient", lambda **kwargs: transport)
    client = AsyncHTTPClient()
    transport.on_close = client.close
    start = Barrier(8)

    def close(_):
        start.wait(timeout=15)
        client.close()

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(close, range(8)))
    assert transport.count == 1
    with pytest.raises(RuntimeError, match="shutdown"):
        client._executor.submit(lambda: None)
