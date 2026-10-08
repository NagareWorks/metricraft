"""Source checkout imports and isolated default HTTP configuration."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from metricraft import VMSingleConfig
from metricraft.config import register_config, reset_config, HttpClientOptions


@pytest.fixture(autouse=True)
def default_configuration():
    reset_config()
    register_config(VMSingleConfig("http://localhost:8428", default_step="1m",
                                  http_options=HttpClientOptions(timeout=1.0)))
    yield
    reset_config()


@pytest.fixture
def no_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise RuntimeError("Network disabled in tests")
    monkeypatch.setattr("urllib.request.urlopen", blocked)
    return True
