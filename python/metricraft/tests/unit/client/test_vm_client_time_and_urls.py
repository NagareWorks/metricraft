from datetime import datetime, timezone

UTC = timezone.utc

import pytest

from metricraft.client.db_client import DatabaseClient
from metricraft import register_config
from metricraft.config import reset_config


class DummyClient:
    def __init__(self, data):
        self.data = data
    def get(self, url, params=None):
        return {"status": "ok", "url": url, "params": params or {}}
    async def get_async(self, url, params=None):
        return self.get(url, params)
    def post(self, url, data=None):
        return {"status": "ok", "url": url, "data": data}


def setup_module(_):
    # Configure single profile using the project's helper configs in conftest
    # If a config is already registered by conftest, this call is a no-op or will be skipped by tests that reuse it.
    try:
        from metricraft.config.single import VMSingleConfig
        reset_config()
        register_config(VMSingleConfig('http://single:8428'))
    except Exception:
        # It's fine if already configured
        pass


def test_vm_client_base_urls_and_time_normalization(monkeypatch):
    c = DatabaseClient()
    # Stub http clients
    monkeypatch.setattr(c, 'client', DummyClient({}))
    monkeypatch.setattr(c, 'async_client', DummyClient({}))

    # URLs now include /prometheus or /select/0/prometheus prefix
    assert any(c.select_base_url.endswith(suf) for suf in (':8428/prometheus', ':8481/select/0/prometheus'))
    assert any(c.insert_base_url.endswith(suf) for suf in (':8428/prometheus', ':8480/insert/0/prometheus'))
    assert any(c.storage_base_url.endswith(suf) for suf in (':8428', ':8400', ':8482'))

    # Time normalization
    assert c._normalize_time(None) is None
    assert c._normalize_time('2024-01-01T00:00:00Z') == '2024-01-01T00:00:00Z'
    assert c._normalize_time(1700000000) == str(1700000000)
    assert c._normalize_time(1700000000000) == str(1700000000)
    ts = c._normalize_time(datetime.fromtimestamp(1700000000, UTC))
    assert ts == str(1700000000)


def test_vm_client_query_and_range_and_health(monkeypatch):
    c = DatabaseClient()
    monkeypatch.setattr(c, 'client', DummyClient({}))

    res = c.query('up')
    assert res is not None
    res = c.query('up', time=1700000000)
    assert res is not None

    res2 = c.query_range('up', start=1700000000, end=1700003600, step='30s')
    assert res2 is not None

    # health should return bool
    assert isinstance(c.health(), bool)
