import pytest
from metricraft import DatabaseClient


@pytest.mark.asyncio
async def test_health_async_guard_path(monkeypatch):
    c = DatabaseClient()
    # Force None to trigger RuntimeError guard
    object.__setattr__(c, 'async_client', None)
    with pytest.raises(RuntimeError):
        await c.health_async()
