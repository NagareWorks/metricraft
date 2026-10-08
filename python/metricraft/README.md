# metricraft

One SDK for immutable PromQL/MetricsQL construction and synchronous/asynchronous
Prometheus/VictoriaMetrics HTTP requests. Import `QueryBuilder`, `DatabaseClient`,
`PrometheusConfig`, `VMSingleConfig` and `VMClusterConfig` from `metricraft`.

Query construction uses the Rust library bundled in platform wheels. Source
checkouts require a local Rust build. Client-only use with query strings needs no native library or provider
registration. Applications own query persistence and authorization.

See the [repository](https://github.com/NagareWorks/metricraft) for source
installation, examples and contributing guidance.
GitHub Actions assembles native platform wheels and validates the supported
Prometheus 3.15.0 / VictoriaMetrics 1.153.0 catalogs and syntax. The sdist contains Python sources only. Historical
AST implementations under `_legacy` are source-only test and benchmark fixtures,
excluded from both the wheel and source distribution.

Query timestamps preserve fractional seconds. Numeric times are epoch seconds;
values whose magnitude exceeds `1e10` are interpreted as milliseconds. Ingestion
converts numeric or absolute ISO/datetime inputs to exposition milliseconds;
relative time strings are supported only for queries. Custom transports used for
health checks should implement `get_text(url)` for plain-text health responses.
