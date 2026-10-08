"""Invalid construction arguments are rejected before transport allocation."""
import pytest
from metricraft import DatabaseClient, VMSingleConfig


@pytest.mark.parametrize("kwargs", [
    {"config": "vm"},
    {"unknown": 1},
    {"db_type": "vm"},
    {"config": VMSingleConfig("http://example.invalid"), "instance": "prod"},
])
def test_constructor_rejects_invalid_arguments_without_allocating_transport(monkeypatch, kwargs):
    def unexpected(**options):
        pytest.fail("Transport allocated before argument validation")
    monkeypatch.setattr("metricraft.client.db_client.SyncHTTPClient", unexpected)
    with pytest.raises(TypeError):
        DatabaseClient(**kwargs)
