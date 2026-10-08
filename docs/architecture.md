# Architecture

## Scope and repository

MetriCraft is a query construction SDK and a Prometheus/VictoriaMetrics HTTP client. Query
languages are limited to PromQL and MetricsQL. There is no SQL/Flux abstraction,
server, dashboard or storage service in the product.

Rust and Python stay in one repository so AST, ABI, bindings and tests can change
in the same commit. The Git history is preserved; older commits use the older layout.

```text
crates/metricraft-core/   immutable expressions, query validation and rendering
crates/metricraft-ffi/    C ABI, errors and ownership
python/metricraft/       one Python distribution: builder, client, config and models
  src/metricraft/builder/ public class, stateless operation groups, native owner
  src/metricraft/models/ query results, ingestion payloads, metadata responses
  src/metricraft/_legacy/ source-only migration fixtures, excluded from packages
docs/examples/          runnable application integration examples
```

## One builder, two modes

`builder/query_builder.py` defines the public class. Operation groups live beside it
in `aggregation.py`, `operators.py`, `rollups.py`, `functions.py`, `selectors.py`,
`temporal.py`, `labels.py`, `transforms.py`, `extended_rollups.py`, `templates.py`
and `diagnostics.py`. They have empty slots and no instance state.
`_expression.py` owns construction, the native handle and its lifetime; `_native.py`
owns ctypes. The public class composes these operations statically, without dynamic
registration, a Python AST or a separate top-level `query.py` implementation.

Imports flow from public exports to builder composition, operation modules and the
native boundary. Operation modules do not import the public class at runtime or
depend on client/config/model modules. Models have no query-language family layer;
their modules follow HTTP response/payload responsibilities.

The public `metricraft.QueryBuilder` constructs queries without server configuration
or provider registration. `build(mode="promql")` and `build(mode="metricsql")` return strings; the
compatibility default is MetricsQL. Select the mode explicitly when saving text.

`@vm_only` marks extension methods; the Rust node carries the actual requirement
and every nested node is checked during build. Function signatures also carry
requirements: `rate(selector)` uses MetricsQL's implicit range, while
`rate(selector[5m])` is accepted in both modes. This is one method with different
call forms, not two builders.

The pinned MetricsQL parser does not implement PromQL's `histogram_count` or
`histogram_sum`. Those methods are marked `@prom_only` and the core rejects them
in MetricsQL mode, including through the generic `function()` entry point.
Metadata is checked in Rust rather than trusting decorators in Python.

## Aggregation and grouping

Plain aggregation is valid in both dialects. Grouping is a separate, exclusive
operation, not two optional parameters on every aggregation method:

```python
from metricraft import QueryBuilder as Q

aggregate = Q.from_metric("http_requests_total").rate("5m").sum()
total = aggregate.build("promql")
per_job = aggregate.by("job").build("promql")
per_other_labels = aggregate.without("instance").build("metricsql")
```

`sum(by=..., without=...)` is not accepted. Once an aggregation is grouped,
another `by()`/`without()` call is rejected by Rust, including repeated calls of
the same kind. Derive alternatives from the ungrouped expression. Empty `by()`
and `without()` remain distinct: the former groups by no labels; the latter
excludes no labels from the grouping key. Parameterized aggregations use the same
shape, for example `topk(3).by("job")`.

## Functional core and ownership

The new core uses private nodes behind `Arc`. Every transformation returns a new
expression and shares existing immutable children. No mutation of public expressions,
parent links, mutable AST registry, or Python copy of the AST is used by this path.

Selectors share a persistent matcher chain and an immutable metric name. Binary
modifiers share their label lists. The source metric is chosen only with
`from_metric()`; `.metric()` and the native `rename_metric` operation are removed.
Reusable selection logic belongs in a pure function over immutable application
parameters. MetricsQL `alias()` is a query transform of result names, not a way to
change the original source selector.

The C ABI borrows child pointers during a call and returns an owning opaque pointer.
Rust retains shared children independently of Python objects. Python finalizers free
each owner; freeing an intermediate Python expression does not invalidate its parents.
Client-only imports do not load the native library. Unsafe C callers must respect
pointer validity and release each returned expression exactly once.

Validation and rendering live in the core. Python handles argument adaptation and
convenience methods; the ABI handles strings, errors and lifetimes. No Python renderer
is used as a fallback. The mutable Rust prototype, global node registry and its old
Python binding have been removed. The native library exposes only the immutable
expression ABI. Python checks `mc_abi_version()` before binding expression functions
and gives a rebuild/reinstall error for an incompatible library.

Constructor and build failures use owned, thread-local error snapshots. Recoverable
Rust panics are caught at those ABI boundaries. This does not make invalid C pointers,
allocation failure or recursive stack exhaustion recoverable; complexity and memory
stress behavior is handled separately. Rendering and last-owner destruction now
use iterative traversal, including persistent matcher chains.

Each node stores two size counters rather than cached query text. `build()` checks
the expanded text size before allocation, with defaults of 1 MiB UTF-8 output and
100,000 expanded node occurrences (including matchers). These can be overridden
per call with positive `max_output_bytes` and `max_expanded_nodes` values. Reusing
a subtree does not eliminate its repeated occurrences in the output string.
The budgets are not a process-wide memory quota. See [memory behavior](memory.md).

## Implemented surface

The common Rust core now provides:

- Named selectors and unnamed equality selectors via `from_labels(**labels)`,
  conjunctive equality/inequality/regex matchers, finite scalar
  and string literals.
- Positive constant selector ranges, subqueries with explicit or default resolution,
  positive/negative `offset`, and numeric or `start()`/`end()` timestamps.
- Unary signs, arithmetic, comparisons with `bool`, set operators,
  `on`/`ignoring`, and `group_left`/`group_right` with structural checks.
- Standard aggregations including `group`, `topk`, `bottomk`, `quantile`, and
  `count_values`, with `by`/`without` (including empty label lists).
- A typed function catalog covering rollups, math, sorting, time/date functions,
  scalar/vector conversion, histogram helpers, clamp/round and label functions.
- MetricsQL `default`, `if`, `ifnot`, `keep_metric_names`, `label_set`, `label_del`,
  `label_keep`, and implicit range arguments for supported rollup signatures.
- MetricsQL label copying/moving, case conversion, value mapping, regex filtering
  and replacement, numeric extraction, equality checks, Graphite name grouping
  and common-label removal. These functions share their input expressions.
- MetricsQL `mad_over_time`, `median_over_time`, `mode_over_time`, `zscore_over_time`,
  `rate_over_sum`, `rollup`, `rollup_rate`, `union`, `alias`, and aggregations
  `any`, `median`, `mode`, `mad` and `outliersk` under the supported dialect baseline.
- Optional explicit windows on common rollup helpers, and fluent date helpers.
- Label sorting, smoothing, time factories, `between`, and `moving_average` as
  `avg_over_time`. `limitk`, `limit_ratio`, `info` and timestamp rollups extend the
  PromQL baseline with explicit experimental opt-in.

`build("promql", experimental_functions=True)` permits cataloged experimental
functions for that call only. The server must also enable
`--enable-feature=promql-experimental-functions`. This option does not bypass
dialect or type validation. `holt_winters` retains the MetricsQL spelling;
PromQL uses `double_exponential_smoothing` with an explicit range. `mad_over_time`
and ordinary label sorting work in both dialects, with the PromQL experimental gate.
Numeric label sorting remains MetricsQL-only. `start()`, `end()` and `step()` also
work in Prometheus 3.15.0 with experimental-functions enabled. Zero-label ordinary
sorting is PromQL-only; VictoriaMetrics requires at least one label.

`QueryBuilder.function(name, *args)` calls only cataloged functions and treats
strings as literals. Fluent methods use the same Rust signature validation.
The maintained signature list is in
[`functions.rs`](../crates/metricraft-core/src/expression/functions.rs) and its
[`label signatures`](../crates/metricraft-core/src/expression/functions/labels.rs).

Repeated `.where_*()` calls add simultaneous constraints, including on the same
label. They never silently replace a tenant or other application filter.
To start a different selection, derive it from the desired earlier expression.

The [stable language baseline](language-support.md) now includes the complete
function/aggregation catalogs and structured extensions: unnamed/regex selectors,
UTF-8 names, MetricsQL duration and matching forms, implicit conversions and WITH
expressions, plus Prometheus experimental duration/extended-range/fill syntax.
Template bindings stay in the same shared native tree and use lexical scopes.
There is no raw-expression parser or server-side query evaluator.

The independent compatibility workflow discovers official capabilities and fails
on missing signatures, unmatched topics or rejected parser/backend witnesses.
Evaluation/storage behavior is explicitly backend-owned; unreleased upstream
features are reported separately. Reports and source snapshots remain Actions
artifacts. Passing examples are bounded evidence, not proof of every expression.

Historical Python builders and visitors are isolated under `metricraft/_legacy`.
They remain available from a source checkout for regression tests and benchmarks
and are excluded from distribution packages. All public QueryBuilder imports
point to the immutable class. The mutable Rust ABI, placeholder Rust VM crate and
Python provider registry are removed.

## Client and packaging

There is one distribution and namespace: `metricraft`. Endpoint configurations
`PrometheusConfig`, `VMSingleConfig` and `VMClusterConfig` select HTTP routing;
they do not select the builder's query mode. `DatabaseClient(config)` constructs
the concrete client directly. No entry points, plugin discovery, factory metaclass
or installation of a second package is required.

Sync/async querying, range queries, metadata, VictoriaMetrics ingestion, cluster
account routing, custom transports and result models share that client. The optional
named registry remains for existing multi-instance applications:
`register_config(config, instance="prod")`, then `DatabaseClient(instance="prod")`.
All three concrete configurations directly inherit the shared `Config` endpoint
contract. The registry distinguishes `DBType.VM` from `DBType.PROMETHEUS`; these
identify backends, not query languages. Without a backend filter, an instance name
must match exactly one backend. With no instance name, only a single registered
backend can supply its default. Ambiguous selections raise before transport
allocation; use a unique instance name or pass a config directly. Explicit lookup
remains available through `get_config(DBType.PROMETHEUS, instance="prod")`.

`DatabaseClient`, `SyncHTTPClient` and `AsyncHTTPClient` are concrete classes without
provider base classes. Custom transports are injected through `HttpClientOptions`
as ordinary objects implementing the required `get`/`post` methods. Factories remain
available for applications that need to create transports from connection settings.
The client composes a transport owner for idempotent cleanup rather than inheriting
lifecycle hooks. Use `with` or explicit `close()` for synchronous use; use `async with`
or `aclose()` for async-only transports. Garbage collection provides best-effort
synchronous cleanup. The default async wrapper borrows the client's sync transport,
so the owner closes it once; a standalone wrapper also leaves an injected transport
or executor under its caller's ownership.

When a client receives a `QueryBuilder`, it builds using its configured dialect,
including selectors supplied to metadata APIs. Unsupported SDK expressions fail
before the HTTP request. Saved strings and external text producers retain their
own validation contract; the client does not parse or sanitize their output.

`MetricsQueryResult` and `MetricsInsertData` are concrete frozen dataclasses.
The former `QueryResult` and `InsertData` ABCs and HTTP transport ABCs are retired;
use concrete result types and transport injection instead. Configuration inheritance
still expresses three endpoint layouts, and metadata result subclasses still share
response parsing; those relationships have actual multiple implementations.

## Performance and next work

Public query validation raises `TypeError` or `ValueError`; native loading failures
raise `RuntimeError`. Historical Python AST exception types are private fixtures.
The public exception package contains `MetriCraftError` and its HTTP subclasses
`MCHTTPError`, `TimeoutError` and `ConnectionError`. Plugin-loader and registry error
classes are retired with provider discovery; the public enum package contains `DBType`.

Application profiling identified Python AST overhead as the reason for migration.
The new structure avoids Python AST traversal and full-tree cloning during
composition. [Local microbenchmarks](../benchmarks/README.md) compare construction,
rendering, release and reuse with the historical Python implementation. The unified
suite also measures synthetic configurable-monitoring workloads and concurrent
memory behavior. These substitute for the unavailable original trace, and do not
establish production application or HTTP latency.

The [migration checklist](rust-migration.md) records the migrated behavior and
release gates. Historical Python fixtures remain source-only regression and
benchmark references; they are excluded from installed packages. HTTP transport
stays in Python. See [language support](language-support.md) for the current baseline.

## Migration compatibility

The old configured query factory (`db_type`, `instance`, `get_instance`) is retired
from the public builder. Use `QueryBuilder.from_metric(...)` without registration;
`QueryBuilder().from_metric(...)` also works as a stateless factory. Client
configuration classes are now imported from `metricraft`. `validate(standard=...)`
delegates to native checks, while `build(mode=...)` raises on invalid queries.
Neither supports a validation bypass or custom Python visitor. Read-only diagnostics
use bounded native traversal and require binding ABI 4. See the
[legacy API ledger](legacy-api-migration.md) for calling and format changes.
The `metricraft_vm` namespace and provider registration/discovery APIs are
retired, including `get_builder_for`, `get_client_for`, `DatabaseClient(db_type=...)`
and `DatabaseClient.get_instance(...)`. Replace them with direct construction or
`DatabaseClient(instance=...)`. Public Python AST visitor hooks and family ABCs
are now private migration fixtures. Unsupported native methods fail explicitly.

The native library is bundled under `metricraft/native/` by GitHub Actions.
The C ABI uses no CPython extension API, so wheels are tagged `py3-none-<platform>`.
The release gate checks source identity, wheel integrity and installed behavior.
The sdist remains Python-only; local Rust builds use the monorepo checkout.
See [the workflow guide](../CONTRIBUTING.md#github-actions) for targets and triggers.

MetricsQL extension syntax follows the
[VictoriaMetrics reference](https://docs.victoriametrics.com/metricsql/).
