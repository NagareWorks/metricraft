"""Release real client resources through explicit close, contexts and GC."""
import asyncio
import gc
import weakref
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from metricraft import DatabaseClient, HttpClientOptions, VMSingleConfig
from metricraft.client import AsyncHTTPClient


def make_client(sync_transport, async_transport):
    options = HttpClientOptions(client=sync_transport, async_client=async_transport)
    return DatabaseClient(VMSingleConfig("http://example.invalid", http_options=options))


def test_close_is_idempotent_and_detaches_finalizer():
    sync_transport = SimpleNamespace(close=Mock())
    async_transport = SimpleNamespace(close=Mock())
    client = make_client(sync_transport, async_transport)
    finalizer = client._finalizer
    client.close()
    client.close()
    assert client.closed
    assert not finalizer.alive
    sync_transport.close.assert_called_once_with()
    async_transport.close.assert_called_once_with()


@pytest.mark.parametrize("cycle", [False, True])
def test_gc_releases_transports_without_retaining_client(cycle):
    sync_transport = SimpleNamespace(close=Mock())
    async_transport = SimpleNamespace(close=Mock())
    client = make_client(sync_transport, async_transport)
    if cycle:
        client.cycle = client
    client_ref = weakref.ref(client)
    del client
    gc.collect()
    assert client_ref() is None
    sync_transport.close.assert_called_once_with()
    async_transport.close.assert_called_once_with()


def test_default_async_wrapper_does_not_close_shared_sync_transport_twice():
    sync_transport = SimpleNamespace(close=Mock())
    config = VMSingleConfig(
        "http://example.invalid", http_options=HttpClientOptions(client=sync_transport)
    )
    client = DatabaseClient(config)
    executor = client.async_client._executor
    client.close()
    sync_transport.close.assert_called_once_with()
    with pytest.raises(RuntimeError, match="shutdown"):
        executor.submit(lambda: None)


def test_sync_context_closes_on_exception_without_suppressing_it():
    sync_transport = SimpleNamespace(close=Mock())
    async_transport = SimpleNamespace(close=Mock())
    with pytest.raises(ValueError, match="body failed"):
        with make_client(sync_transport, async_transport) as client:
            assert not client.closed
            raise ValueError("body failed")
    assert client.closed
    sync_transport.close.assert_called_once_with()
    async_transport.close.assert_called_once_with()


@pytest.mark.asyncio
async def test_aclose_prefers_async_cleanup_and_is_idempotent():
    sync_transport = SimpleNamespace(close=Mock())
    async_transport = SimpleNamespace(aclose=AsyncMock(), close=Mock())
    client = make_client(sync_transport, async_transport)
    await client.aclose()
    await client.aclose()
    client.close()
    assert client.closed
    assert not client._finalizer.alive
    sync_transport.close.assert_called_once_with()
    async_transport.aclose.assert_awaited_once_with()
    async_transport.close.assert_not_called()


@pytest.mark.asyncio
async def test_async_context_closes_async_only_transport_on_exception():
    sync_transport = SimpleNamespace(close=Mock())
    async_transport = SimpleNamespace(aclose=AsyncMock())
    with pytest.raises(ValueError, match="body failed"):
        async with make_client(sync_transport, async_transport) as client:
            assert not client.closed
            raise ValueError("body failed")
    assert client.closed
    sync_transport.close.assert_called_once_with()
    async_transport.aclose.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_async_close_falls_back_to_sync_close():
    sync_transport = SimpleNamespace(close=Mock())
    async_transport = SimpleNamespace(close=Mock())
    client = make_client(sync_transport, async_transport)
    await client.aclose()
    sync_transport.close.assert_called_once_with()
    async_transport.close.assert_called_once_with()


@pytest.mark.asyncio
async def test_cancelled_async_close_still_releases_sync_resources():
    sync_transport = SimpleNamespace(close=Mock())
    async_transport = SimpleNamespace(aclose=AsyncMock(side_effect=asyncio.CancelledError), close=Mock())
    client = make_client(sync_transport, async_transport)
    with pytest.raises(asyncio.CancelledError):
        await client.aclose()
    assert client.closed
    assert not client._finalizer.alive
    sync_transport.close.assert_called_once_with()
    async_transport.close.assert_called_once_with()


@pytest.mark.asyncio
async def test_failed_async_close_still_releases_other_resources():
    sync_transport = SimpleNamespace(close=Mock())
    async_transport = SimpleNamespace(aclose=AsyncMock(side_effect=ValueError("close failed")), close=Mock())
    client = make_client(sync_transport, async_transport)
    await client.aclose()
    sync_transport.close.assert_called_once_with()
    async_transport.close.assert_called_once_with()


def test_failed_transport_factory_closes_already_created_transport():
    sync_transport = SimpleNamespace(close=Mock())

    def failing_factory(**kwargs):
        raise ValueError("factory failed")

    options = HttpClientOptions(client=sync_transport, async_client_factory=failing_factory)
    with pytest.raises(ValueError, match="factory failed"):
        DatabaseClient(VMSingleConfig("http://example.invalid", http_options=options))
    sync_transport.close.assert_called_once_with()


@pytest.mark.asyncio
async def test_async_wrapper_borrows_external_transport_and_executor():
    sync_transport = SimpleNamespace(request=Mock(return_value={"ok": True}), close=Mock())
    with ThreadPoolExecutor(max_workers=1) as executor:
        transport = AsyncHTTPClient(sync_client=sync_transport, executor=executor)
        assert await transport.get("http://example.invalid") == {"ok": True}
        await transport.aclose()
        sync_transport.close.assert_not_called()
        assert executor.submit(lambda: "still open").result() == "still open"
