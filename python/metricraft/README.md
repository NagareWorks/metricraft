# metricraft

One SDK for immutable PromQL/MetricsQL construction and synchronous/asynchronous
Prometheus/VictoriaMetrics HTTP requests. Import `QueryBuilder`, `DatabaseClient`,
`PrometheusConfig`, `VMSingleConfig` and `VMClusterConfig` from `metricraft`.

Requires Python 3.8+. We recommend [uv](https://docs.astral.sh/uv/) to manage
your project's dependencies and environment:

```sh
uv add metricraft
```

Or use pip:

```sh
python -m pip install metricraft
```

Matching wheels support Windows x86_64, Linux x86_64 with glibc 2.28+, and
macOS 11+ on Intel or Apple Silicon. They require no Rust toolchain or source
checkout. See the [installation guide](https://nagareworks.github.io/metricraft/getting-started/)
for a virtual environment setup and an offline first query.

Query construction uses the Rust library bundled in platform wheels. Source
installations compile the included Rust sources and require Rust and a platform C linker.
Client-only use with query strings needs no native library or provider
registration. Applications own query persistence and authorization.

See the [documentation](https://nagareworks.github.io/metricraft/) for
installation and examples, and the [repository](https://github.com/NagareWorks/metricraft)
for contributing guidance.
GitHub Actions assembles native platform wheels and validates the supported
Prometheus 3.15.0 / VictoriaMetrics 1.153.0 catalogs and syntax. The sdist includes
the Python SDK, both Rust crates and the Cargo lockfile.

Query timestamps preserve fractional seconds. Numeric times are epoch seconds;
values whose magnitude exceeds `1e10` are interpreted as milliseconds. Ingestion
converts numeric or absolute ISO/datetime inputs to exposition milliseconds;
relative time strings are supported only for queries. When a range query uses
a relative `end`, provide `start` explicitly. Custom transports used for
health checks should implement `get_text(url)` for plain-text health responses.

The built-in transport supports separate `(connect, read)` timeout budgets,
including TLS connection setup. A custom urllib opener accepts one timeout;
use equal budgets with it, or supply a custom HTTP client for separate phases.
