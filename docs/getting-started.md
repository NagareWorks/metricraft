# Your first query

MetriCraft is a Python SDK for constructing PromQL and MetricsQL and querying
Prometheus or VictoriaMetrics. Rust owns the immutable expression tree;
Python provides the fluent API and an independent HTTP client.

## Install from source

These docs describe the development branch. A native release has not yet been
published. Start with Python 3.8+ and a Rust toolchain:

```sh
git clone https://github.com/NagareWorks/metricraft.git
cd metricraft
python -m pip install -e "python/metricraft[dev]"
python scripts/dev.py build
python scripts/dev.py smoke
```

`build` compiles the Rust library. `smoke` runs offline examples, so no metrics
server is needed. Native wheels are built in CI for Linux x86_64, Windows x86_64,
macOS Intel and Apple Silicon; they are not yet a published package release.

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
