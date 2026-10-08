"""Install the SDK wheel in isolation and verify client-only execution."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile
import venv
import zipfile


SMOKE = '''
import asyncio
from importlib import metadata
import sys

def no_plugins(*args, **kwargs):
    raise AssertionError("The SDK must not discover provider plugins")
metadata.entry_points = no_plugins

from metricraft import (DatabaseClient, PrometheusConfig, VMSingleConfig,
                       VMClusterConfig, HttpClientOptions, QueryBuilder)
import metricraft

assert metadata.version("metricraft")
assert not metadata.distribution("metricraft").entry_points
assert not hasattr(metricraft, "register_provider")
for retired in ("ProviderLoadError", "RegistryError", "NotConfiguredError", "QueryBuilderError",
                "PositionalError", "InvalidParameterError", "QueryResult", "InsertData"):
    assert not hasattr(metricraft, retired), retired

class Transport:
    def get(self, url, params=None):
        assert params["query"] == "sum(up)"
        assert url == expected_url
        return {"status": "success", "data": {"resultType": "vector", "result": []}}
    def close(self):
        pass

class AsyncTransport:
    async def get(self, url, params=None):
        return Transport().get(url, params)
    async def aclose(self):
        pass

options = HttpClientOptions(client=Transport(), async_client=AsyncTransport())
configs = [
    (PrometheusConfig("http://prometheus.invalid", http_options=options),
     "http://prometheus.invalid/api/v1/query"),
    (VMSingleConfig("http://single.invalid", http_options=options),
     "http://single.invalid/prometheus/api/v1/query"),
    (VMClusterConfig(vmselect_url="http://select.invalid", vminsert_url="http://insert.invalid",
                     vmstorage_url="http://storage.invalid", account_id=42, http_options=options),
     "http://select.invalid/select/42/prometheus/api/v1/query"),
]
async def check_async(config):
    async with DatabaseClient(config) as client:
        assert (await client.query_async("sum(up)")).is_success

for config, expected_url in configs:
    with DatabaseClient(config) as client:
        assert client.query("sum(up)").is_success
    asyncio.run(check_async(config))

assert "metricraft._native" not in sys.modules
assert not any(name.startswith("metricraft._legacy") for name in sys.modules)
print("Installed SDK: sync/async HTTP works for all three configurations without native code or plugins.")
'''


BUILDER_SMOKE = '''
from metricraft import QueryBuilder as Q
base = Q.from_metric('up').where_eq('job', 'api')
assert Q.__module__ == 'metricraft.builder.query_builder'
assert not hasattr(base, '__dict__')
assert base.sum().build('promql') == 'sum (up{job="api"})'
assert base.sum().by('job').build('promql') == 'sum by (job) (up{job="api"})'
assert base.build('promql') == 'up{job="api"}'
extension = base.default(0)
assert 'default' in extension.build('metricsql')
try:
    extension.build('promql')
except ValueError:
    pass
else:
    raise AssertionError('Dialect validation did not run in packaged native core')
template = Q.template('x', body=Q.reference('x').rate('5m'))
assert Q.template_call('f', base).with_(f=template).build().startswith('WITH (f(x) = rate(x[5m]))')
assert base.range(Q.step().max_of(60)).rate().build(
    'promql', features=('promql-duration-expr',))
assert base.histogram_quantiles('phi', 0.5).build(
    'promql', experimental_functions=True).startswith('histogram_quantiles(up')
assert base.rollup_candlestick('5m').build().startswith('rollup_candlestick(')
assert base.range_normalize().build().startswith('range_normalize(')
print('Installed builder validates extended syntax, dialects and immutable query semantics.')
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dist", type=Path)
    parser.add_argument("--native-library", type=Path)
    parser.add_argument("--require-bundled-native", action="store_true")
    args = parser.parse_args()
    dist = args.dist.resolve()
    wheels = list(dist.glob("metricraft-*.whl"))
    if len(wheels) != 1:
        raise SystemExit("Expected exactly one metricraft wheel in " + str(dist))
    wheel = wheels[0]
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        root = Path(__file__).resolve().parents[1]
        for notice in ("LICENSE", "NOTICE"):
            candidates = [name for name in names
                          if ".dist-info/" in name and name.endswith("/" + notice)]
            assert len(candidates) == 1, "Missing or ambiguous packaged " + notice
            expected = (root / notice).read_text(encoding="utf-8")
            assert archive.read(candidates[0]).decode("utf-8").replace("\r\n", "\n") == expected
            assert (root / "python/metricraft" / notice).read_text(encoding="utf-8") == expected
        assert not any(name.startswith(("metricraft_vm/", "metricraft/_legacy/")) for name in names)
        assert "metricraft/client/db_client.py" in names
        assert "metricraft/client/_resources.py" in names
        assert "metricraft/client/_base.py" not in names
        assert "metricraft/config/prometheus.py" in names
        assert "metricraft/builder/query_builder.py" in names
        assert "metricraft/builder/aggregation.py" in names
        for module in ("templates", "transforms", "extended_rollups"):
            assert "metricraft/builder/" + module + ".py" in names
        assert "metricraft/models/query_result.py" in names
        assert "metricraft/models/ingestion.py" in names
        assert "metricraft/models/metadata.py" in names
        assert "metricraft/models/types.py" in names
        assert "metricraft/models/base.py" not in names
        assert "metricraft/exceptions/builder.py" not in names
        assert "metricraft/exceptions/utils.py" not in names
        assert "metricraft/query.py" not in names
        assert not any(name.startswith("metricraft/models/families/") for name in names)
    # Keep installation artifacts beside the caller-selected distribution directory.
    with tempfile.TemporaryDirectory(prefix="package-check-", dir=dist.parent) as work:
        work = Path(work)
        venv.EnvBuilder(with_pip=True).create(work / "venv")
        python = work / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["METRICRAFT_NATIVE_LIB"] = str(work / "missing-native-library")
        subprocess.run([str(python), "-I", "-m", "pip", "install", "--no-deps", "--no-index", str(wheel)],
                       env=env, cwd=work, check=True)
        subprocess.run([str(python), "-I", "-B", "-c", SMOKE], env=env, cwd=work, check=True)
        if args.require_bundled_native:
            env.pop("METRICRAFT_NATIVE_LIB", None)
            env.pop("CARGO_TARGET_DIR", None)
            subprocess.run([str(python), "-I", "-B", "-c", '''
from pathlib import Path
from metricraft import QueryBuilder as Q
from metricraft import _native
import metricraft
assert Path(_native.lib._name).resolve().parent == Path(metricraft.__file__).resolve().parent / 'native'
''' + BUILDER_SMOKE], env=env, cwd=work, check=True)
        if args.native_library:
            env["METRICRAFT_NATIVE_LIB"] = str(args.native_library.resolve())
            subprocess.run([str(python), "-I", "-B", "-c", BUILDER_SMOKE],
                           env=env, cwd=work, check=True)


if __name__ == "__main__":
    main()
