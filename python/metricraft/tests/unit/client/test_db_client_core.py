"""Connection settings exposed by the concrete SDK client."""
from types import SimpleNamespace

from metricraft import DatabaseClient, HttpClientOptions, VMSingleConfig


def test_connection_info_is_a_detached_shallow_copy():
    config = VMSingleConfig(
        "http://example.invalid",
        http_options=HttpClientOptions(client=SimpleNamespace(), async_client=SimpleNamespace()),
    )
    with DatabaseClient(config) as client:
        info = client.get_connection_info()
        assert info == client.connection_info
        info["url"] = "http://changed.invalid"
        assert client.get_connection_info()["url"] == "http://example.invalid"
