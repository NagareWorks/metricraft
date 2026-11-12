# Query parsing: unreleased API

The Rust core can parse a supported subset of **Prometheus 3.16.0 PromQL** into
the same immutable `Expr` graph used by the builder. This is development work
for the next minor release. The development Python and C ABI bindings expose
this parser; the published 0.3.0 package does not. Common MetricsQL queries are
also supported against **VictoriaMetrics 1.156.0 / MetricsQL parser 0.87.6**.
Existing builder and client APIs keep their behavior.

## Python

```python
from metricraft import ParseError, QueryBuilder as Q

saved = 'rate(requests_total{job="api"}[5m])'
query = Q.parse(saved, mode="promql", max_input_bytes=65_536, max_depth=32)
grouped = query.sum().by("job")
text = grouped.build("promql")
assert query.build("promql") == saved

try:
    Q.parse('{"温度"} + @')
except ParseError as error:
    print(error.kind, error.start, error.end)
```

`ParseError` is a `ValueError` subclass. Its `kind` is `syntax`, `validation`,
`dialect`, `unsupported`, `limit`, or `other`; `start` and `end` are UTF-8 byte
offsets, not Python character indexes. Python argument type errors remain
`TypeError`/`ValueError`. `None` selects native default budgets; explicit budgets
must be positive integers (not booleans), and depth must be at most 128.

Parsing returns the ordinary `QueryBuilder` and composes with its existing
methods. `parse()` defaults to PromQL, while the existing `build()` default stays
MetricsQL for compatibility: pass `build("promql")` explicitly. Parsing does not
store a dialect or feature configuration. Experimental functions and syntax need
the corresponding options on both parsing and building. String arguments to
existing builder methods still mean literal data, never implicitly parsed source.

Client-only imports do not load native code. Older ABI-4 libraries can still run
existing builder methods; calling the new parser on one reports a missing-feature
error with rebuild/reinstall guidance. No alternate Python parser is used.

### Edit a saved alert

```python
original = Q.parse('sum by (job) (rate(requests_total[5m])) > 100')
updated = original.replace_at([1], Q.from_scalar(200), mode="promql")
assert original.build("promql").endswith(" > 100)")
assert updated.build("promql").endswith(" > 200)")
assert updated.at_path([0]).shares_node(original.at_path([0]))
```

`children()` returns an ordered tuple of independent expression owners;
`at_path()` follows zero-based child indexes. An empty path selects the root.
Paths accept iterables of at most 1024 unsigned `size_t` integers, excluding
booleans. Negative indexes and missing children raise errors. Selectors and
literals are leaves: labels and literal durations are metadata, not children.
WITH nodes expose binding values in declaration order followed by their body.

`node_kind()` identifies a node such as `selector`, `aggregate` or `binary`;
`value_type()` is `scalar`, `string`, `instant`, `range` or `tuple`.
Non-root replacements must preserve the selected value type. To edit a leaf's
metadata, construct a replacement using the existing builder and replace that
occurrence. Only the chosen occurrence changes even when its node is shared at
other paths. Paths describe the current graph, not stable identifiers across edits.

`replace_at()` shares unchanged nodes and retains root identity for a same-node
replacement. It always validates the resulting root, including scopes, dialect,
feature flags and build budgets. Its mode defaults to MetricsQL, as `build()`
does; use `mode="promql"` explicitly for saved Prometheus rules. A child owner
remains usable after its parent is released. `shares_node()` tests native identity,
not semantic equality; parsing identical strings separately does not intern them.

## C ABI

The additive ABI-4 entry point `mc_expr_parse` accepts a counted UTF-8 buffer,
mode, optional `McParseOptions`, and optional caller-owned `McParseErrorInfo`.
See [the C header](../crates/metricraft-ffi/include/metricraft.h) for declarations.
Null options or zero fields select the defaults in the table below. Flags have
the same meaning as `mc_expr_build_with_options`. The input is borrowed for the
call only, and embedded NUL bytes never truncate it.

A successful call returns an owning handle released with `mc_expr_free`.
Failure returns null; `mc_last_error` returns an independent message snapshot
released with `mc_error_free`. The optional error-info output contains kind
1–5 for the parser categories above (6 for other), plus source byte offsets.
It is zeroed on entry; kind 0 means no structured parser error, including ABI
argument failures. It owns no allocation. Success clears the calling thread's
last error. Existing expression pointers, error layout and release functions
are unchanged.

The optional `mc_expr_at_path`, `mc_expr_replace_at`, `mc_expr_children`,
`mc_expr_node_info` and `mc_expr_shares_node` exports operate on the same owners.
For children, first query the count with a null output and zero capacity, then
provide an array of pointer slots. The immutable count cannot change between
calls while the parent stays live. Free every returned child with `mc_expr_free`;
the caller owns the array itself. Capacity failures leave its slots untouched.
Node-info strings use `mc_string_free`. Child counts and identity checks return
`-1` on failure; owning-pointer results return null. Use `mc_last_error` for the
message. `McBuildOptions` uses the same budgets/flags as building; zero budgets
or a null options pointer select defaults. Editing is independent of parsing and
also supports MetricsQL expressions created through the existing builder.

## Rust and subtree sharing

```rust
use metricraft_core::{Expr, Mode};
use metricraft_core::expression::BuildOptions;

let source = "sum by(job)(rate(requests_total{job=\"api\"}[5m])) > 100";
let original = Expr::parse(source, Mode::PromQl)?;
let threshold = Expr::parse("200", Mode::PromQl)?;
let edited = original.replace_at(&[1], &threshold, Mode::PromQl, BuildOptions::default())?;
assert!(edited.at_path(&[0])?.shares_node(&original.at_path(&[0])?));
let saved_text = edited.build(Mode::PromQl)?;
```

`replace_at` returns a new root and rebuilds only its ancestors. The original
query stays usable; unaffected subtrees share their `Arc` allocations. Parsing
independent strings creates independent graphs; it does not intern queries or
retain an unbounded global cache. Applications own loading and saving query text.

## Supported input

Selectors, quoted UTF-8 names and strings, label matchers, numeric and duration
literals, functions, aggregations with grouping, unary/binary operators,
vector matching, ranges/subqueries, `offset`, and `@` enter structured
nodes. Explicit build flags also govern supported experimental functions,
and binary fill modifiers. Parsing never enables them
automatically. Comments and source formatting are discarded; query evaluation
and constant folding are not performed. The full input must be consumed.

Prometheus 3.16's `anchored` and `smoothed` selectors parse without an opt-in.
Pass `features=("promql-unquoted-utf8-names",)` to parse unquoted Unicode letters
and non-leading dots in metric and label names. The rules also cover grouping
and vector matching. Combining marks, non-ASCII digits and punctuation still
require quoting; names retain their exact spelling without normalization.
Letter classification uses Unicode 17, matching the pinned Prometheus binary.
Under this opt-in, grouping and matching labels containing colons also require
quotes; the legacy mode retains the upstream's older grouping-label behavior.
The builder quotes these names, so this input-only flag need not be repeated
when building the parsed query. Numeric `Inf`/`NaN` remain literals, while
`Inf.total` and `NaN.total` are metric names.

Computed durations in range windows, subquery windows/steps and `offset` accept
`+`, `-`, `*`, `/`, `%`, `^`, parentheses, `step()`, `range()`, `min_of(a, b)` and
`max_of(a, b)`, following the pinned Prometheus 3.16 grammar. Pass
`features=("promql-duration-expr",)` to both parsing and building; the server
must enable the same feature. `@` still accepts a literal or `start()`/`end()`.
For offsets, enclose the complete duration calculation in parentheses: `up offset 1h + 2` adds two to the
selected samples, while `up offset (1h + 2)` changes the offset. Prometheus also
consumes following duration arithmetic after a leading parenthesized operand:
`up offset (1h) + 2` changes the offset too. To add to samples after a computed
offset, group the complete selector: `(up offset (1h)) + 2`. The renderer adds
this grouping when needed.

```python
from metricraft import QueryBuilder as Q

features = ("promql-duration-expr",)
query = Q.parse("rate(http_requests_total[5m * 2])", features=features)
edited = query.replace_at([0, 1, 1], Q.from_scalar(3), "promql", features=features)
assert edited.build("promql", features=features) == "rate(http_requests_total[(300 * 3)])"
assert edited.at_path([0, 0]).shares_node(query.at_path([0, 0]))
```

Computed durations are ordinary immutable children, so editing an operand shares
the selector and every unchanged operand. Literal durations remain metadata on
the existing nodes. Duration arithmetic is not constant-folded; positivity and
query-time values such as `step()` remain the server's responsibility, except
for invalid literal windows/steps and literal division or modulo by zero, which
are rejected while parsing. Redundant parentheses and literal signs may normalize.

This is not a claim of complete PromQL or MetricsQL support. Explicit
`Unsupported` errors cover
duplicate grouping labels, zero offsets or extended modifiers placed before a
range, non-finite durations, and non-UTF-8 bytes in strings. Regex validation currently supports a
conservative RE2 subset: empty quoted blocks, leading-zero repetition counts,
Unicode properties beyond general categories, nested or ambiguous bracket classes,
and patterns beyond the regex compiler's syntax or limits
are rejected without replacing or escaping their meaning. Matcher text is
preserved. These limits are tested against the pinned upstream parser.

PromQL strings containing U+FFFD are rendered with a Unicode escape, as required
by its lexer. MetricsQL's identifier decoder cannot decode this escape
in grouping or vector-matching labels; building those queries in MetricsQL mode
returns an error instead of changing the label name.

## MetricsQL parsing

Pass `mode="metricsql"` to the existing parser; the result uses the same native
nodes, ownership, traversal and path editing as PromQL. No separate parser or
AST is installed in Python, and no ABI version change is needed.

```python
from metricraft import QueryBuilder as Q

saved = 'sum by(job)(rate(requests_total{status=~"5.."})) > 100'
original = Q.parse(saved, mode="metricsql")
updated = original.replace_at([1], Q.from_scalar(200), mode="metricsql")
assert updated.at_path([0]).shares_node(original.at_path([0]))
text = updated.build("metricsql")
```

This first slice accepts ASCII metric/label names, selectors, ordinary strings,
decimal/octal scalars, supported function calls (including implicit rollup windows
and trailing commas), single-input aggregations, vector matching, and binary
operators including `default`, `if` and `ifnot`. Literal ranges/subqueries accept
lowercase fractional and step-relative durations such as `[2.5m]`, `[5m:2i]`,
`[:1m]` and `[:]`. Offsets and literal or `start()`/`end()` timestamps are supported.
Literal durations stay metadata; they do not allocate numeric expression trees.
MetricsQL function names are case-insensitive; normalization preserves the case
of metric names, labels and string values.

MetricsQL comments end at a newline, not a carriage return. Raw strings drop
carriage returns as upstream does. Unary minus and binary precedence follow
MetricsQL's zero-subtraction grammar, including enclosing right-hand operands.
The conformance job checks original and normalized queries against the pinned
Go parser and evaluates both on VictoriaMetrics; selected cases also assert
independently calculated values. These checks are separate from unit tests.

Follow-up slices will add `WITH`, selector `or`, tuples/multi-input aggregations,
computed strings and timestamps, `keep_metric_names`, aggregation limits,
join prefixes/copy-all labels, fill modifiers, extended/escaped identifiers, non-decimal integer
prefixes, scalar duration/size suffixes, placeholders and signed compound
durations. Recognized deferred constructs raise `Unsupported`; other shapes can
fail syntax or existing AST validation. In particular, zero windows/steps,
duplicate grouping labels and some implicit type conversions remain subject to
builder constraints. PromQL computed-duration syntax is not accepted in
MetricsQL mode. The PromQL experimental flags do not enable additional MetricsQL
grammar. This is a supported subset, not full MetricsQL text compatibility.

## Errors and resource limits

`ParseError` carries a `kind`, `message`, and an end-exclusive `start..end` range
of UTF-8 byte offsets into the original input. Syntax errors point at the
offending token; final whole-expression semantic checks may span the query.
Kinds distinguish syntax, validation, dialect, unsupported constructs and limits.

`Expr::parse_with_options(source, mode, ParseOptions)` accepts these budgets:

| Option | Default | Constraint |
| --- | --- | --- |
| `max_input_bytes` | 1 MiB | Nonzero UTF-8 byte count |
| `max_tokens` | 100,000 | Nonzero; excludes EOF |
| `max_depth` | 64 | Recursive grammar depth, 1–128 |
| `max_work` | 1,000,000 | Nonzero conservative construction/validation units |
| `build.limits` | 1 MiB output, 100,000 expanded nodes | Same limits as rendering |
| `build` feature flags | Disabled | Must match the caller's Prometheus server |

Budgets bound parser work; they are not wall-clock deadlines. Canonical rendering
adds explicit parentheses, so a long flat expression can need a larger depth
budget when reparsed. Exceeding a budget returns `Limit`, never a partial AST.
Successful parsing is not authorization to run a query or a backend cost estimate.
The client continues to forward saved strings under the application's contract.

`python scripts/dev.py conformance` checks native roundtrips against pinned
`promtool`, checks invalid and explicitly deferred inputs, and compares original
and rendered evaluation results on fixed samples. Native tests cover malformed
input and subtree sharing; the benchmark workflow measures retained edit memory.
The robustness workflow adds a bounded query-text fuzz target with ASan.
