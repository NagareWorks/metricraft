# Backend result validation

Parser acceptance does not establish the meaning of a query. The separate
`scripts/check_backend_results.py` integration runner starts pinned Prometheus 3.15.0
and VictoriaMetrics 1.153.0 processes, loads the same synthetic time series into
both, and checks results against independently calculated expectations.

The corpus includes grouping and ungrouped aggregation, rates, increases, an error
ratio, histogram quantiles, comparison filtering and `bool`, vector matching with
`group_left`, set operations, offset, fixed `@` time, subqueries, clamps, escaped
label values, missing series and scalar arithmetic. MetricsQL additionally checks
`default`, `if`, `ifnot`, `union`, and 23 label-operation witnesses. Label checks
include ordered copies/moves, missing labels, empty mappings, escaped values,
anchored matching, replacement captures, nonnumeric values and metric-name handling.
The extended corpus also verifies WITH values/functions/string filters, selector
alternatives, scalar aggregation, tuple filtering, variadic aggregation, aggregation
limits, bitmap operations, prefixed joins, portable histogram quantiles, duration
expressions, anchored/smoothed ranges and fill modifiers. There are 26 PromQL and
62 MetricsQL value witnesses; this is not numerical equivalence of the languages.

Four PromQL and nineteen MetricsQL expressions also run as range queries over three evaluation
times. Comparisons check exact label sets and timestamps, plus numeric values with
an explicit floating-point tolerance. Empty, duplicate and partial results cannot
silently pass. Tooling tests verify that deliberately wrong results fail the oracle.

The main path builds strings, saves them as JSON, reads them back and executes them
through `DatabaseClient`. Sync/async SDK expression arguments are checked too. When
given an SDK builder, the client selects the configured backend's build mode before
the request. Raw text is passed through without parsing or sanitizing it.

## Reproduce

Build the native library and set `METRICRAFT_NATIVE_LIB` to it. Supply real backend
executables; on Windows, prefer executable paths over wrappers that inject their
own service configuration.

```sh
python scripts/check_backend_results.py \
  --output /path/outside/checkout/new-backend-run \
  --prometheus /path/to/prometheus \
  --promtool /path/to/promtool \
  --victoria-metrics /path/to/victoria-metrics-prod
```

Add `--matrix /path/to/generated/compatibility/matrix.json` to execute the
independently discovered catalog witnesses as instant/range requests. This records
signature acceptance separately from expected-value checks. The compatibility
Action runs both stages and retains their reports; no discovery inventory enters
the installed SDK or unit tests.

Only a new output directory outside the checkout is accepted. Servers listen on
loopback at temporary ports, have separate storage and are terminated on success
or failure. No existing database is contacted. Prometheus data is imported with
promtool; VictoriaMetrics data is imported through its JSON-line endpoint.

Reports contain fixture data, saved query strings, expected/actual results, logs,
backend versions, revision and source/native hashes. Local storage directories are
retained for diagnosis; CI artifacts include only the small reproducibility files,
not database storage. Remove a run's storage after it is no longer needed.

The existing CI `conformance` job runs parser checks first, then result validation.
Failures block `required-checks` and package publication. Job Summary and the
`metricraft-backend-results` artifact preserve available results even after failure.
This is separate from unit tests, benchmark timing and the upstream compatibility
discovery report. Version upgrades must revisit semantic expectations explicitly.
