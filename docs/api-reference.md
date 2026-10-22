# Python API

Import the public entry points from `metricraft`. Use `QueryBuilder` for immutable
construction and `DatabaseClient` for I/O. All configurations live in the same
package.

## Reading the reference

The web documentation builds its searchable signature index directly from the
Python source. Signatures and declaration links are generated; no native library
is needed to build the documentation.

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
