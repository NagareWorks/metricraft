# Query parsing: unreleased Rust foundation

The Rust core can parse a supported subset of **Prometheus 3.15.0 PromQL** into
the same immutable `Expr` graph used by the builder. This is development work
for the next minor release. Python, C ABI and MetricsQL parser entry points are
not available yet; the published Python SDK and client keep their existing APIs.

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
