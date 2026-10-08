# Historical builder migration ledger

Snapshot: 2026-10-08. The historical `_legacy/builder/{impl,mixins}` surface has
173 method/operator names: 159 expression-producing entries, seven build/diagnostic
entries, and seven explicitly retired entries. Every retained name has a native
witness. This is a functional surface audit, not a claim of source compatibility,
backend equivalence, full language coverage or production performance acceptance.

The executable disposition is [migration.py](../tests/conformance/migration.py).
The [migration contract tests](../tests/test_migration_contract.py) compare its
entries with the historical definitions, exercise calling conventions and verify
diagnostic limits. The upstream parser corpus consumes the same expression
witnesses. A string literal is checked inside a function because recording rules
require numeric/vector output. Historical tests importing `_legacy` remain
comparison fixtures; their passing count does not establish native coverage.

## Compatibility rules

- Construction uses `Q.from_metric(name)` or another stateless factory. No
  configuration/provider/subtype dispatch, mutable AST or retargeting method remains.
- Composition returns a new owner sharing immutable Rust children. Repeated label
  constraints are conjunctions. They do not silently replace earlier matchers.
- Unary signs apply immediately with normal expression semantics. They are not
  deferred mutable sign state. Explicit parentheses do not change expression type.
- Binary operands are numbers or builders. Replace `a + "metric_name"` with
  `a + Q.from_metric("metric_name")`; no string is interpreted as query code.
- Comparisons and `&`/`|` construct query expressions. Queries have no Python
  truth value and are unhashable; use `is` for owner identity.
- Common rollups use an existing range if present. On instant inputs an omitted
  window means MetricsQL implicit rollup, unlike the old default of five minutes.
  Use `rate(duration="5m")` or `range("5m").rate()` for portable explicit intent.
  `range()`, `moving_average()` and `holt_winters()` retain their five-minute
  convenience default. A range cannot be replaced in place; derive from its
  original selector. Computed-vector windows use `subquery()`.
- Aggregation methods take no `by=` or `without=` arguments. Use `sum().by("job")`
  or `sum().without("instance")`; plain `sum()` is valid in both dialects.
  Grouping is selected once per aggregation. A grouped expression rejects another
  `by()` or `without()` call. Derive alternative groupings from the ungrouped root.
  Empty `by()` and `without()` retain their distinct language semantics. Modifiers
  are legal only on matching expression kinds; invalid old output is rejected.
- Optional duration aliases, `prediction_seconds=`, `quantile=`,
  `to_nearest=`, `range_duration=`, `resolution=`, `rollup(func=...)`,
  `sort("desc")` and scalar instance `.vector()` are retained.
- Other parameter names were normalized: `label_name` becomes `label` in
  matchers/count_values, regex `pattern` becomes `value`,
  `target_label/source_label` become `destination/source`,
  `min_value/max_value` become `minimum/maximum`, and
  `min_threshold/max_threshold` become `minimum/maximum`.
  Binary `default(value=...)` and `atan2(x=...)` now use `other=...`.
  Update old keyword calls accordingly; positional calls still work.
- Timestamps accept numeric seconds, timezone-aware datetime/ISO values, and
  `start`/`end` (also with parentheses). Naive dates, arbitrary raw fragments
  and guessed millisecond units are not retained.
- `build()` always validates and explicitly selects the dialect. It has no
  `validate=False` or custom visitor escape hatch. `validate(standard=...)`
  returns an error string for native validation failures, but `strict=False`
  is rejected. Errors use Python TypeError/ValueError, not legacy AST exception
  classes or mutable error positions.
- Backend/version validity takes precedence over old output: `holt_winters`
  is MetricsQL-only under the pinned Prometheus baseline; relevant PromQL
  experimental operations require explicit opt-in. `moving_average` expands to
  `avg_over_time`. Invalid rollup result names such as `p95` are rejected.

## Diagnostics and memory

`debug()` and `to_debug_json()` now return schema-1 graph JSON. Children and
persistent matcher links reference IDs; shared data is emitted once. `analyze()`
returns a detached summary with unique-node counts, metric/label/function names,
structural complexity and heuristic findings. These are not measured backend costs.

Graph and analysis defaults are 1 MiB output and 10,000 work items (root, child
edges and unique matcher links). Traversal, depth analysis and release are iterative.
Explicit positive `max_output_bytes`/`max_items` override the defaults per call.
A 61-node DAG with exponential textual expansion can still be inspected.

`debug_positions()` returns source and UTF-8 byte spans for each rendered
expression occurrence. It observes the same native renderer and dialect checks as
`build()`. Matcher details live in graph diagnostics; they are not separate span
entries. `visualize_positions(source_code)` returns this source/span JSON after
checking the exact source string. The old caret/tree presentation is retired;
applications can present these spans themselves. Span diagnostics necessarily
expand occurrences and enforce both work and serialized-output limits.

None of these calls adds cached strings or diagnostic fields to persistent nodes.
Snapshots are detached return values; applications own their retention.

## Method-by-method disposition

| Historical entry | Disposition | Contract |
| --- | --- | --- |
| `__add__` | Migrated | Typed immutable operation; see compatibility rules above. |
| `__and__` | Migrated | Typed immutable operation; see compatibility rules above. |
| `__eq__` | Migrated | Builds a query; Python truth conversion is rejected. |
| `__ge__` | Migrated | Typed immutable operation; see compatibility rules above. |
| `__getattribute__` | Retired | Internal subtype dispatch retired. |
| `__gt__` | Migrated | Typed immutable operation; see compatibility rules above. |
| `__le__` | Migrated | Typed immutable operation; see compatibility rules above. |
| `__lt__` | Migrated | Typed immutable operation; see compatibility rules above. |
| `__mod__` | Migrated | Typed immutable operation; see compatibility rules above. |
| `__mul__` | Migrated | Typed immutable operation; see compatibility rules above. |
| `__ne__` | Migrated | Builds a query; Python truth conversion is rejected. |
| `__neg__` | Migrated | Typed immutable operation; see compatibility rules above. |
| `__or__` | Migrated | Typed immutable operation; see compatibility rules above. |
| `__pos__` | Migrated | Typed immutable operation; see compatibility rules above. |
| `__pow__` | Migrated | Typed immutable operation; see compatibility rules above. |
| `__radd__` | Migrated | Typed immutable operation; see compatibility rules above. |
| `__rmul__` | Migrated | Typed immutable operation; see compatibility rules above. |
| `__rsub__` | Migrated | Typed immutable operation; see compatibility rules above. |
| `__rtruediv__` | Migrated | Typed immutable operation; see compatibility rules above. |
| `__sub__` | Migrated | Typed immutable operation; see compatibility rules above. |
| `__truediv__` | Migrated | Typed immutable operation; see compatibility rules above. |
| `abs` | Migrated | Typed immutable operation; see compatibility rules above. |
| `acos` | Migrated | Typed immutable operation; see compatibility rules above. |
| `acosh` | Migrated | Typed immutable operation; see compatibility rules above. |
| `add` | Migrated | Typed immutable operation; see compatibility rules above. |
| `alias` | Migrated | Typed immutable operation; see compatibility rules above. |
| `analyze` | Migrated, format/contract adjusted | Native unique-node analysis, not expanded-tree counts. |
| `and_` | Migrated | Typed immutable operation; see compatibility rules above. |
| `any` | Migrated | Typed arguments; grouping via .by() or .without(). |
| `asin` | Migrated | Typed immutable operation; see compatibility rules above. |
| `asinh` | Migrated | Typed immutable operation; see compatibility rules above. |
| `ast_node` | Retired | Use read-only native diagnostics. |
| `at` | Migrated | Explicit timezone or numeric seconds; start/end tokens accepted. |
| `atan` | Migrated | Typed immutable operation; see compatibility rules above. |
| `atan2` | Migrated | Typed immutable operation; see compatibility rules above. |
| `atanh` | Migrated | Typed immutable operation; see compatibility rules above. |
| `avg` | Migrated | Typed arguments; grouping via .by() or .without(). |
| `avg_over_time` | Migrated | Typed range input; duration keyword retained. |
| `between` | Migrated | Inclusive value-preserving comparisons. |
| `bool` | Migrated | Typed immutable operation; see compatibility rules above. |
| `bottomk` | Migrated | Typed arguments; grouping via .by() or .without(). |
| `build` | Migrated, format/contract adjusted | Dialect and expansion budgets; no custom visitor or validation bypass. |
| `by` | Migrated | Typed immutable operation; see compatibility rules above. |
| `ceil` | Migrated | Typed immutable operation; see compatibility rules above. |
| `changes` | Migrated | Typed range input; duration keyword retained. |
| `clamp_max` | Migrated | Typed immutable operation; see compatibility rules above. |
| `clamp_min` | Migrated | Typed immutable operation; see compatibility rules above. |
| `cos` | Migrated | Typed immutable operation; see compatibility rules above. |
| `cosh` | Migrated | Typed immutable operation; see compatibility rules above. |
| `count` | Migrated | Typed arguments; grouping via .by() or .without(). |
| `count_over_time` | Migrated | Typed range input; duration keyword retained. |
| `count_values` | Migrated | Typed arguments; grouping via .by() or .without(). |
| `day_of_month` | Migrated | Typed immutable operation; see compatibility rules above. |
| `day_of_week` | Migrated | Typed immutable operation; see compatibility rules above. |
| `day_of_year` | Migrated | Typed immutable operation; see compatibility rules above. |
| `debug` | Migrated, format/contract adjusted | Bounded unique-node JSON graph. |
| `debug_positions` | Migrated, format/contract adjusted | UTF-8 byte spans of rendered expression occurrences. |
| `dedup` | Retired | Old expansion was unsupported; backend deduplication is outside the builder. |
| `default` | Migrated | Typed immutable operation; see compatibility rules above. |
| `deg` | Migrated | Typed immutable operation; see compatibility rules above. |
| `delta` | Migrated | Typed range input; duration keyword retained. |
| `deriv` | Migrated | Typed range input; duration keyword retained. |
| `div` | Migrated | Typed immutable operation; see compatibility rules above. |
| `eq` | Migrated | Typed immutable operation; see compatibility rules above. |
| `exp` | Migrated | Typed immutable operation; see compatibility rules above. |
| `floor` | Migrated | Typed immutable operation; see compatibility rules above. |
| `from_end` | Migrated | Stateless immutable factory. |
| `from_expr` | Retired | Old string wrapper was not a parser; pass saved text to the client. |
| `from_metric` | Migrated | Stateless immutable factory. |
| `from_now` | Migrated | Stateless immutable factory. |
| `from_scalar` | Migrated | Stateless immutable factory. |
| `from_start` | Migrated | Stateless immutable factory. |
| `from_string` | Migrated | Stateless immutable factory. |
| `from_time` | Migrated | Stateless immutable factory. |
| `ge` | Migrated | Typed immutable operation; see compatibility rules above. |
| `get_builder` | Retired | Provider/subtype registry retired. |
| `group` | Migrated | Typed arguments; grouping via .by() or .without(). |
| `group_left` | Migrated | Typed immutable operation; see compatibility rules above. |
| `group_right` | Migrated | Typed immutable operation; see compatibility rules above. |
| `gt` | Migrated | Typed immutable operation; see compatibility rules above. |
| `histogram_quantile` | Migrated | Typed arguments; grouping via .by() or .without(). |
| `holt_winters` | Migrated | Typed range input; duration keyword retained. |
| `hour` | Migrated | Typed immutable operation; see compatibility rules above. |
| `idelta` | Migrated | Typed range input; duration keyword retained. |
| `ignoring` | Migrated | Typed immutable operation; see compatibility rules above. |
| `increase` | Migrated | Typed range input; duration keyword retained. |
| `irate` | Migrated | Typed range input; duration keyword retained. |
| `keep_metric_names` | Migrated | Typed immutable operation; see compatibility rules above. |
| `label_del` | Migrated | Typed immutable operation; see compatibility rules above. |
| `label_join` | Migrated | Typed immutable operation; see compatibility rules above. |
| `label_replace` | Migrated | Typed immutable operation; see compatibility rules above. |
| `label_set` | Migrated | Typed immutable operation; see compatibility rules above. |
| `last_over_time` | Migrated | Typed range input; duration keyword retained. |
| `le` | Migrated | Typed immutable operation; see compatibility rules above. |
| `limitk` | Migrated | Typed immutable operation; see compatibility rules above. |
| `ln` | Migrated | Typed immutable operation; see compatibility rules above. |
| `log10` | Migrated | Typed immutable operation; see compatibility rules above. |
| `log2` | Migrated | Typed immutable operation; see compatibility rules above. |
| `lt` | Migrated | Typed immutable operation; see compatibility rules above. |
| `mad` | Migrated | Typed arguments; grouping via .by() or .without(). |
| `mad_over_time` | Migrated | Typed range input; duration keyword retained. |
| `max` | Migrated | Typed arguments; grouping via .by() or .without(). |
| `max_over_time` | Migrated | Typed range input; duration keyword retained. |
| `median` | Migrated | Typed arguments; grouping via .by() or .without(). |
| `median_over_time` | Migrated | Typed range input; duration keyword retained. |
| `metric` | Retired | Use from_metric; metric identity is fixed. |
| `min` | Migrated | Typed arguments; grouping via .by() or .without(). |
| `min_over_time` | Migrated | Typed range input; duration keyword retained. |
| `minute` | Migrated | Typed immutable operation; see compatibility rules above. |
| `mod` | Migrated | Typed immutable operation; see compatibility rules above. |
| `mode` | Migrated | Typed arguments; grouping via .by() or .without(). |
| `mode_over_time` | Migrated | Typed range input; duration keyword retained. |
| `month` | Migrated | Typed immutable operation; see compatibility rules above. |
| `moving_average` | Migrated | Renders avg_over_time with an explicit window. |
| `mul` | Migrated | Typed immutable operation; see compatibility rules above. |
| `ne` | Migrated | Typed immutable operation; see compatibility rules above. |
| `negative` | Migrated | Typed immutable operation; see compatibility rules above. |
| `offset` | Migrated | Typed immutable operation; see compatibility rules above. |
| `on` | Migrated | Typed immutable operation; see compatibility rules above. |
| `or_` | Migrated | Typed immutable operation; see compatibility rules above. |
| `outliersk` | Migrated | Typed immutable operation; see compatibility rules above. |
| `parenthesize` | Migrated | Explicit immutable parentheses node. |
| `positive` | Migrated | Typed immutable operation; see compatibility rules above. |
| `pow` | Migrated | Typed immutable operation; see compatibility rules above. |
| `predict_linear` | Migrated | Typed range input; duration keyword retained. |
| `present_over_time` | Migrated | Typed range input; duration keyword retained. |
| `quantile` | Migrated | Typed arguments; grouping via .by() or .without(). |
| `quantile_over_time` | Migrated | Typed range input; duration keyword retained. |
| `rad` | Migrated | Typed immutable operation; see compatibility rules above. |
| `range` | Migrated | Typed range input; duration keyword retained. |
| `rate` | Migrated | Typed range input; duration keyword retained. |
| `rate_over_sum` | Migrated | Typed range input; duration keyword retained. |
| `register_builder` | Retired | Provider/subtype registry retired. |
| `resets` | Migrated | Typed range input; duration keyword retained. |
| `rollup` | Migrated | func/duration and window/result forms; only min, max, avg. |
| `rollup_rate` | Migrated | Typed range input; duration keyword retained. |
| `round` | Migrated | Typed immutable operation; see compatibility rules above. |
| `sin` | Migrated | Typed immutable operation; see compatibility rules above. |
| `sinh` | Migrated | Typed immutable operation; see compatibility rules above. |
| `smooth_exponential` | Migrated | Typed immutable operation; see compatibility rules above. |
| `sort` | Migrated | asc/desc direction retained. |
| `sort_by_label` | Migrated | Typed immutable operation; see compatibility rules above. |
| `sort_by_label_desc` | Migrated | Typed immutable operation; see compatibility rules above. |
| `sort_by_label_numeric` | Migrated | Typed immutable operation; see compatibility rules above. |
| `sort_by_label_numeric_desc` | Migrated | Typed immutable operation; see compatibility rules above. |
| `sort_desc` | Migrated | Typed immutable operation; see compatibility rules above. |
| `sqrt` | Migrated | Typed immutable operation; see compatibility rules above. |
| `stddev` | Migrated | Typed arguments; grouping via .by() or .without(). |
| `stddev_over_time` | Migrated | Typed range input; duration keyword retained. |
| `stdvar` | Migrated | Typed arguments; grouping via .by() or .without(). |
| `stdvar_over_time` | Migrated | Typed range input; duration keyword retained. |
| `sub` | Migrated | Typed immutable operation; see compatibility rules above. |
| `subquery` | Migrated | Typed immutable operation; see compatibility rules above. |
| `sum` | Migrated | Typed arguments; grouping via .by() or .without(). |
| `sum_over_time` | Migrated | Typed range input; duration keyword retained. |
| `tan` | Migrated | Typed immutable operation; see compatibility rules above. |
| `tanh` | Migrated | Typed immutable operation; see compatibility rules above. |
| `timestamp` | Migrated | Typed immutable operation; see compatibility rules above. |
| `to_debug_json` | Migrated, format/contract adjusted | Bounded unique-node JSON graph. |
| `topk` | Migrated | Typed arguments; grouping via .by() or .without(). |
| `union` | Migrated | Typed immutable operation; see compatibility rules above. |
| `unless` | Migrated | Typed immutable operation; see compatibility rules above. |
| `validate` | Migrated, format/contract adjusted | Native checks; strict=False rejected. |
| `vector` | Migrated | Both scalar.vector() and QueryBuilder.vector(number). |
| `visualize_positions` | Migrated, format/contract adjusted | Source/span JSON; source must match the exact rendered query. |
| `where` | Migrated | Typed immutable operation; see compatibility rules above. |
| `where_eq` | Migrated | Typed immutable operation; see compatibility rules above. |
| `where_ne` | Migrated | Typed immutable operation; see compatibility rules above. |
| `where_not_regex` | Migrated | Typed immutable operation; see compatibility rules above. |
| `where_regex` | Migrated | Typed immutable operation; see compatibility rules above. |
| `without` | Migrated | Typed immutable operation; see compatibility rules above. |
| `year` | Migrated | Typed immutable operation; see compatibility rules above. |
| `zscore_over_time` | Migrated | Typed range input; duration keyword retained. |

## Acceptance still outside this ledger

Application workload performance, real backend result comparison, extended
multi-thread stress and sanitizer/fuzz validation remain separate acceptance work.
Do not use this table to claim that every old invalid input should remain accepted
or that PromQL/MetricsQL is fully implemented. See [migration status](rust-migration.md).
