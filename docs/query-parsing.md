# Query parsing: unreleased API

The Rust core can parse a supported subset of **Prometheus 3.15.0 PromQL** into
the same immutable `Expr` graph used by the builder. This is development work
for the next minor release. The development Python and C ABI bindings expose
this parser; the published 0.3.0 package does not. MetricsQL parsing is not
implemented yet. Existing builder and client APIs keep their behavior.

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
vector matching, literal ranges/subqueries, `offset`, and `@` enter structured
nodes. Explicit build flags also govern supported experimental functions,
extended range selectors and binary fill modifiers. Parsing never enables them
automatically. Comments and source formatting are discarded; query evaluation
and constant folding are not performed. The full input must be consumed.

This is not a claim of complete PromQL or MetricsQL support. Explicit
`Unsupported` errors cover MetricsQL mode, computed duration expressions,
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
