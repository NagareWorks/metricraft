from unittest.mock import patch

from metricraft.client import SyncHTTPClient
from metricraft.config.http_options import HttpClientOptions
from metricraft import DatabaseClient


class DummyConfig:
    def __init__(self, info, http_options=None):
        self._info = info
        self._http_options = HttpClientOptions.ensure(http_options) if http_options is not None else None

    def get_connection_info(self):
        return self._info

    @property
    def http_options(self):
        return self._http_options


def _make_base_connection(http_options=None):
    return {
        "type": "single",
        "url": "http://example",
        "timeout": 15.0,
        "default_step": "30s",
        "http_options": http_options or {},
    }


def test_http_options_default_headers_and_timeout_tuple():
    http_options = {
        "timeout": (2, 5),
        "default_headers": {"Authorization": "token"},
    }
    cfg = DummyConfig(_make_base_connection(http_options))

    with patch("metricraft.client.db_client.get_config", return_value=cfg):
        client = DatabaseClient()

    assert isinstance(client.client, SyncHTTPClient)
    assert client.client.connect_timeout == 2.0
    assert client.client.timeout == 5.0
    assert client.timeout == 5.0
    assert client.client._default_headers["Authorization"] == "token"
    assert client.http_options["default_headers"]["Authorization"] == "token"


def test_http_options_custom_factories():
    class CustomSyncClient:
        def __init__(self):
            self.calls = []

        def get(self, *args, **kwargs):
            self.calls.append(("get", args, kwargs))
            return {}

        def post(self, *args, **kwargs):
            self.calls.append(("post", args, kwargs))
            return {}

    class CustomAsyncClient:
        async def get(self, *args, **kwargs):  # pragma: no cover - trivial coroutine
            return {}

        async def post(self, *args, **kwargs):  # pragma: no cover - trivial coroutine
            return {}

    def sync_factory(**kwargs):
        return CustomSyncClient()

    def async_factory(**kwargs):
        return CustomAsyncClient()

    http_options = {
        "client_factory": sync_factory,
        "async_client_factory": async_factory,
    }
    cfg = DummyConfig(_make_base_connection(http_options))

    with patch("metricraft.client.db_client.get_config", return_value=cfg):
        client = DatabaseClient()

    assert isinstance(client.client, CustomSyncClient)
    assert isinstance(client.async_client, CustomAsyncClient)


def test_http_options_alias_headers_and_prepare_hook():
    def hook(request):
        request.add_header("X-Hook", "1")

    http_options = {
        "headers": {"X-Token": "abc"},
        "prepare_request": hook,
    }
    cfg = DummyConfig(_make_base_connection(http_options))

    with patch("metricraft.client.db_client.get_config", return_value=cfg):
        client = DatabaseClient()

    assert isinstance(client.client, SyncHTTPClient)
    assert client.client._default_headers["X-Token"] == "abc"
    assert client.client._prepare_request_hook is hook


def test_http_options_direct_instances():
    class CustomSyncClient:
        def get(self, *args, **kwargs):
            return {}

        def post(self, *args, **kwargs):
            return {}

    class CustomAsyncClient:
        async def get(self, *args, **kwargs):  # pragma: no cover - trivial coroutine
            return {}

        async def post(self, *args, **kwargs):  # pragma: no cover - trivial coroutine
            return {}

    custom_sync = CustomSyncClient()
    custom_async = CustomAsyncClient()
    http_options = {
        "client": custom_sync,
        "async_client": custom_async,
    }
    cfg = DummyConfig(_make_base_connection(http_options))

    with patch("metricraft.client.db_client.get_config", return_value=cfg):
        client = DatabaseClient()

    assert client.client is custom_sync
    assert client.async_client is custom_async


def test_http_options_merge_config_and_overrides():
    base_options = HttpClientOptions.ensure({
        "timeout": (1, 2),
        "default_headers": {"Base": "1"},
    })
    overrides = {
        "timeout": (3, 4),
    }
    cfg = DummyConfig(_make_base_connection(overrides), http_options=base_options)

    with patch("metricraft.client.db_client.get_config", return_value=cfg):
        client = DatabaseClient()

    assert client.client.connect_timeout == 3.0
    assert client.timeout == 4.0
    assert client.http_options["default_headers"] == {"Base": "1"}


def test_http_options_legacy_header_support():
    conn = _make_base_connection()
    conn["http_headers"] = {"X-Token": "legacy"}
    cfg = DummyConfig(conn)

    with patch("metricraft.client.db_client.get_config", return_value=cfg):
        client = DatabaseClient()

    assert client.client._default_headers["X-Token"] == "legacy"
