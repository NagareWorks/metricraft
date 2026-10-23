# Your first query

MetriCraft is a Python SDK for constructing PromQL and MetricsQL and querying
Prometheus or VictoriaMetrics. Rust owns the immutable expression tree;
Python provides the fluent API and an independent HTTP client.

## Install the release candidate

With Python 3.8+, install the first native release candidate from PyPI:

```sh
python -m pip install metricraft==0.3.0rc1
```

Matching wheels include the Rust core and need no Rust toolchain. This is a
prerelease; pin the version explicitly while evaluating it in your application.

## Install from source

For development, use Python 3.8+ and a Rust toolchain:

```sh
git clone https://github.com/NagareWorks/metricraft.git
cd metricraft
python -m pip install -e ".[dev]"
python scripts/dev.py build
python scripts/dev.py smoke
```

The editable install compiles the native library; `build` also prepares the
workspace library for development checks. `smoke` runs offline examples, so no metrics
server is needed. Native wheels are built and tested in CI for Linux x86_64,
Windows x86_64, macOS Intel and Apple Silicon.

The source distribution includes the Rust sources and locked Cargo dependencies.
Installing it requires Rust (`cargo` and `rustc`) and a C linker for your platform.
If a compatible wheel is available, pip uses it without requiring a Rust toolchain.
The release wheels target glibc 2.28+ on Linux x86_64, Windows x86_64 and macOS 11+
on Intel and Apple Silicon. Other platforms currently require a source build.

## Compose a query

```python
from metricraft import QueryBuilder as Q

requests = Q.from_metric("http_requests_total").where_eq("job", "api")
rate = requests.rate("5m").sum().by("job")
text = rate.build("promql")

assert text == 'sum by (job) (rate(http_requests_total{job="api"}[5m]))'
assert requests.build("promql") == 'http_requests_total{job="api"}'
```

The second assertion matters: deriving `rate` leaves `requests` unchanged.
You can reuse any expression as the starting point for another branch.

Choose `"promql"` or `"metricsql"` at build time. The default is `"metricsql"`;
being explicit makes stored queries easier to associate with their destination.
Unsupported dialect forms raise an error, including inside nested expressions.

## Execute with the client

The following example requires a reachable Prometheus server. Unlike the offline
build example, its result depends on the data in that server.

```python
from metricraft import DatabaseClient, PrometheusConfig

with DatabaseClient(PrometheusConfig("http://localhost:9090")) as client:
    result = client.query(text)
    print(result.is_success)
```

The client also accepts strings loaded from your application's storage. It does
not need a native library when used with strings alone. Use context managers to
close transports, or `async with` for asynchronous calls.

## Where to go next

- [Build queries](building-queries.md) for filtering, grouping and vector matching.
- [Query your backend](client-guide.md) for configuration and async usage.
- [From UI selections](examples/01_configurable_query/README.md) for an offline application example.
- [Language support](language-support.md) for version baselines and feature flags.

If the builder reports that its native library is missing, run `python
scripts/dev.py build` from the checkout. When using a custom build directory,
set `METRICRAFT_NATIVE_LIB` to the resulting shared library. Client-only imports
do not require this step.
