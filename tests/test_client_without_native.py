"""Client-only usage must work when no native builder library is installed."""
import os
from pathlib import Path
import subprocess
import sys


def test_client_factory_and_raw_query_without_native(tmp_path):
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "python/metricraft/src")
    env["METRICRAFT_NATIVE_LIB"] = str(tmp_path / "missing-library")
    code = '''
import sys
from importlib import metadata
def no_plugins(*args, **kwargs):
    raise AssertionError('Client must not discover provider plugins')
metadata.entry_points = no_plugins
from metricraft import DatabaseClient, register_config
from metricraft.config import VMSingleConfig
from metricraft.config.http_options import HttpClientOptions
class Transport:
    def get(self, url, params=None):
        assert url == 'http://example.invalid/prometheus/api/v1/query'
        assert params['query'] == 'sum(up)'
        return {'status': 'success', 'data': {'resultType': 'vector', 'result': []}}
    def close(self):
        pass
config = VMSingleConfig('http://example.invalid', http_options=HttpClientOptions(client=Transport()))
with DatabaseClient(config) as client:
    assert client.query('sum(up)').is_success
register_config(config)
with DatabaseClient() as client:
    assert client.query('sum(up)').is_success
assert 'metricraft._legacy.native.ffi' not in sys.modules
assert 'metricraft._native' not in sys.modules
assert not any(name.startswith('metricraft._legacy') for name in sys.modules)
'''
    result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
