# Python API

Import the public entry points from `metricraft`. Use `QueryBuilder` for immutable
construction and `DatabaseClient` for I/O. All configurations live in the same
package.

## Python type hints

MetriCraft 0.3.0 includes inline type hints and a `py.typed` marker for type
checkers and editors.

Fluent calls, Python operators and dialect-marked methods return `QueryBuilder`;
`build()` returns `str`. Client calls return `MetricsQueryResult` or the matching
metadata result, including when awaited. The installed-wheel CI checks these
contracts and ensures invalid argument types are rejected by mypy and Pyright.

Signatures use a few shared input aliases:

| Type | Accepted Python values |
| --- | --- |
| `Number` | `int` or `float` (runtime checks reject booleans) |
| `ScalarInput` | A number or `QueryBuilder` expression |
| `StringInput` | A string or a string-valued expression |
| `QueryInput` | A number, string or `QueryBuilder` expression |
| `Window` | A duration string or duration expression |
| `BuildMode` | `QueryMode` or the literal `"promql"` / `"metricsql"` |
| `MatchInput` | A selector string, `QueryBuilder`, or a sequence (such as a list or tuple) containing either |

Python annotations check argument shapes and preserve chained return types. Rust
still validates expression kinds, allowed values, dialects and feature flags.
For example, a `QueryBuilder` used as a scalar argument must represent a scalar
in the selected language. HTTP adapter inputs use read-only mappings; decoded response values have type
`object` and need narrowing before use. See [transport contracts](client-guide.md#replace-the-http-transport).
Other dynamic data, such as diagnostics, can still contain `Any` values.

## Reading the reference

The reference is divided into category pages. Signatures, parameter names,
defaults and declaration links come from the Python source; each method also
has an editorial purpose, parameter types, accepted values and return contract.
The documentation build fails if a new method or parameter lacks a contract.

Distinguish SDK validation from backend semantics. For example, a quantile is
normally in `[0, 1]`, but a backend may define results outside that interval;
the reference does not claim that every recommended range is rejected locally.
All builder composition returns a new shared expression. Client requests perform
I/O and configuration objects have their own mutability contracts.

`vm_only` marks a MetricsQL-only method; `prom_only` marks a PromQL-only method.
`prom_experimental` requires an explicit Prometheus feature opt-in. A missing
badge does not promise every argument form works in both languages: Rust checks
the complete expression at build time. See [language support](language-support.md).

## Main entry points

| Entry point | Purpose |
| --- | --- |
| `QueryBuilder` | Factories, immutable composition and `.build(mode)` |
| `DatabaseClient` | Query, metadata and VictoriaMetrics ingestion requests |
| `PrometheusConfig` | Standard Prometheus endpoints |
| `VMSingleConfig` | VictoriaMetrics single-node endpoints |
| `VMClusterConfig` | VictoriaMetrics cluster endpoints and tenant selection |
| `HttpClientOptions` | Timeouts, headers and custom transports |
| `register_config`, `get_config`, `set_default_instance` | Optional named configuration registry |
| `MetricsQueryResult`, `MetricsInsertData`, `TimeValue` | Client result, ingestion and time contracts |

Start with the [building guide](building-queries.md) or
[client guide](client-guide.md) for connected examples. The
[builder source](../python/metricraft/src/metricraft/builder/query_builder.py)
and [client source](../python/metricraft/src/metricraft/client/db_client.py)
remain available when reading this document on GitHub.
