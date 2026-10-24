# Your first query

MetriCraft is a Python SDK for constructing PromQL and MetricsQL and querying
Prometheus or VictoriaMetrics. Rust owns the immutable expression tree;
Python provides the fluent API and an independent HTTP client.

## Install from PyPI

Requires Python 3.8+. We recommend [uv](https://docs.astral.sh/uv/) to manage
your project's dependencies and environment. In an existing uv project, run the
command below; for a new project, run `uv init` first:

```sh
uv add metricraft
```

Or use pip in a virtual environment. Create one in your application directory:

```sh
python -m venv .venv
```

Activate it with `.venv\Scripts\Activate.ps1` in Windows PowerShell, or
`source .venv/bin/activate` on Linux/macOS, then install:

```sh
python -m pip install metricraft
```

The regression suite covers CPython 3.8–3.15 with the GIL enabled. Python 3.14
and 3.15 also run isolated installed-wheel checks on every precompiled platform.

Matching wheels include the Rust core: you do not
need Rust, Cargo, a compiler, or a clone of this repository to use them.
With uv, run the Python examples using `uv run python` in place of `python`.

### Precompiled platforms

| System | Python architecture | Minimum runtime |
| --- | --- | --- |
| Windows | x86_64 (64-bit) | Windows with 64-bit Python |
| Linux | x86_64 | glibc 2.28 or newer |
| macOS | x86_64 (Intel) | macOS 11 or newer |
| macOS | arm64 (Apple Silicon) | macOS 11 or newer |

The wheel must match the running Python interpreter, including its architecture.
Linux ARM64, Alpine/musl and 32-bit Windows do not currently have precompiled
wheels. Source installations require Rust and a platform C linker; see
[source setup](../CONTRIBUTING.md#set-up) if you need to build the SDK.

To require a precompiled wheel and avoid a source build:

```sh
python -m pip install --only-binary=:all: metricraft
```

If pip reports no matching distribution, check Python's version and architecture
and your package index. A mirror may not have synchronized the release yet;
retry with `--index-url https://pypi.org/simple` when appropriate.

### Free-threaded CPython

CPython 3.14t and 3.15t are tested with the GIL disabled, including installed
wheels. They use the same platform wheel: the bundled Rust library uses a C ABI
and does not link to CPython's extension ABI. Free threading became an officially
supported, optional CPython build in [Python 3.14](https://peps.python.org/pep-0779/).

Check the actual running mode; a free-threaded interpreter can also enable the GIL:

```sh
python -c "import sys, sysconfig; print(sysconfig.get_config_var('Py_GIL_DISABLED'), sys._is_gil_enabled())"
```

For free-threaded execution the result is `1 False`. Immutable query expressions
can be shared between threads. Configure clients before use, finish outstanding
requests before closing them, and use thread-safe custom transports when sharing
a client. Concurrent client cleanup releases each owned transport once; it does
not make user-provided callbacks or mutable configuration thread-safe.

## Compose a query

```python
from metricraft import QueryBuilder as Q

requests = Q.from_metric("http_requests_total").where_eq("job", "api")
rate = requests.rate("5m").sum().by("job")
text = rate.build("promql")

assert text == 'sum by (job) (rate(http_requests_total{job="api"}[5m]))'
assert requests.build("promql") == 'http_requests_total{job="api"}'
print(text)
```

Save this as `first_query.py` and run `python first_query.py`. It runs offline
and prints `sum by (job) (rate(http_requests_total{job="api"}[5m]))`.

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

## Check which package is loaded

If an existing development installation is still loading a local checkout:

```sh
python -m pip show metricraft
python -c "import metricraft; print(metricraft.__file__)"
```

An `Editable project location` points at source code. To replace that installation
with the published wheel in the same environment:

```sh
python -m pip install --force-reinstall --only-binary=:all: --index-url https://pypi.org/simple metricraft
```

Restart an existing Python process or notebook kernel after replacing the package.
Release wheels load their own native library. Remove a development-only
`METRICRAFT_NATIVE_LIB` override if it points to an old or missing library.
Keep source development installations in a separate virtual environment.

## Where to go next

- [Build queries](building-queries.md) for filtering, grouping and vector matching.
- [Query your backend](client-guide.md) for configuration and async usage.
- [From UI selections](examples/01_configurable_query/README.md) for an offline application example.
- [Language support](language-support.md) for version baselines and feature flags.
