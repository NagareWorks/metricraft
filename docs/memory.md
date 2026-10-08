# Immutable expressions and memory

Expression derivation shares immutable children through `Arc`; it does not deep-copy
the tree. Selector matchers form a persistent linked chain, and binary modifiers
share their label lists. There are no parent links, mutable arenas, global node
registries, global string interners or rendered-string caches keeping old queries alive.
The [Rust Arc contract](https://doc.rust-lang.org/std/sync/struct.Arc.html) defines
shared ownership and release after the final owner is dropped.

Each derived expression still needs its new nodes, literal data and Python owner.
Keeping every historical root keeps the union of their reachable nodes alive.
Deleting a parent cannot release children still referenced by a different root.
This is retained application state, not automatically a leak.

## Query construction contract

Choose a source metric once with `Q.from_metric(name)`. There is no `.metric()`
setter/replacement method or native `rename_metric` operation. Reuse selection
rules as immutable data and pure application functions:

```python
from metricraft import QueryBuilder as Q

filters = (("job", "api"), ("env", "prod"))

def select(name, filters):
    query = Q.from_metric(name)
    for label, value in filters:
        query = query.where_eq(label, value)
    return query

requests = select("http_requests_total", filters)
errors = select("http_errors_total", filters)
rate = requests.rate("5m")  # requests is unchanged
```

Different metrics constructed this way are separate selectors. No hidden interning
is promised across independently constructed queries. Derivations from the same
expression do share the relevant children and selector data.

## Expansion limits and deep trees

A small shared DAG can generate enormous text: repeatedly composing `q + q` doubles
the output while adding only one binary node. Every node therefore caches saturating
output-byte and expanded-node counts, without storing its rendered text. `build()`
checks these before reserving the output buffer.

Defaults are 1 MiB UTF-8 output and 100,000 expanded node occurrences, including
matchers. Override budgets for a known workload on a single build call:

```python
text = rate.build("promql", max_output_bytes=2 * 1024 * 1024,
                  max_expanded_nodes=200_000)
```

These limits do not cap the number of live Python expressions or total process memory.
Native rendering and last-owner release are iterative. Destruction dismantles only
uniquely owned nodes after their lifetime ends; it never mutates any live shared query.
Tests build/render/drop 100,000-deep function and matcher chains on a 256 KiB thread
stack, and cover concurrent last owners and overflowed expansion counts.

## Measurements on 2026-10-08

The unified suite measures release builds with validation and garbage collection
active. Its reports retain source and binary hashes. These synthetic workloads
replace the unavailable application trace; they do not establish production latency.

Read-only graph diagnostics visit unique nodes and matcher links without recreating
a Python AST. Rendered position diagnostics expand occurrences and use the same
native build limits. See the [diagnostic contract](legacy-api-migration.md#diagnostics-and-memory).

The native allocation probe starts from 256 labels with 128-byte values. Counts
include requested native allocations and retained root containers, but exclude
allocator overhead, Python heaps and OS RSS. Windows GNU release measurements:

| Workload | Retained native bytes | Bytes above baseline after release |
| --- | ---: | ---: |
| 512 branches from one selector | 179,900 | 0 |
| 512 independently constructed selectors with equivalent filters | 30,620,050 | 0 |
| 1,000 branches from one selector | 294,580 | 0 |
| 10,000 branches from one selector | 2,418,580 | 0 |
| 10,000 label-copy branches sharing the source | 1,679,943 | 0 |
| 10,000 WITH branches sharing a binding | 2,629,932 | 0 |
| 1,000 retained selector versions | 235,234 | 0 |
| 10,000 create/build/drop operations, keeping the base | 7,566 | 0 |
| 100,000-deep function chain | 13,100,152 | 0 |
| 100,000-deep WITH chain | 24,900,393 | 0 |
| 60 shared self-compositions, rejected before rendering | 7,412 | 0 |
| 1,000 bounded graph snapshots of a shared DAG | 14,826 | 0 |
| 256 selector OR self-compositions with a common filter, rejected before rendering | 94,752 | 0 |

All thirteen cases returned to their native allocation baseline. Structural sharing
substantially reduces retained data, but every new root and operation still costs
memory. Defaults reject expanded text from the deep WITH chain before rendering;
last-owner release remains iterative. WITH bindings are emitted, not expanded in
the SDK, so build budgets do not constrain the backend's macro-expansion work.

Selector OR alternatives and common filters also remain shared nodes. An observed
fuzzer timeout exposed eager alternative-list expansion; the failing input is now
a regression case. Composition and adding a filter do not enumerate alternatives.
The renderer distributes filters iteratively only after checking cached expansion
budgets, including nested OR branches and computed string values.

A Python 3.13/Windows run retained, rendered and released 2,000 branches per batch,
ten batches each for selector, label-copy and WITH branches: 60,000 owners in total.
Every sampled owner became unreachable. After selector batches, traced Python live
memory ranged from 75,417 to 79,235 bytes; after WITH batches it ranged from 157,766
to 161,153 bytes, including accumulated measurement records. Process private memory
after the WITH batches ranged from about 23.5 to 25.1 MiB. Allocator high-water
memory is distinct from reachable query data.

A four-worker Python/ctypes run released 83,456 query owners and handled 93,888
expected validation/budget failures over 60.1 seconds. Each batch checked owner
weak references and the unchanged shared base. Post-batch process private memory
ranged from about 21.3 to 22.4 MiB and ended at 21.6 MiB after releasing workers and
the base, compared with 20.6 MiB after warmup. Traced Python live memory ended at
42,778 bytes, including measurement records. This bounded run showed no continuing
growth in retained query state; it is not an application-wide memory guarantee.

Linux ASan with leak detection passed all 26 Rust tests and the thirteen native
allocation scenarios for the current implementation, including small-stack and
concurrent last-owner release tests.
A subsequent libFuzzer run completed 100,950 inputs in 181 seconds without a
failure, seeded with the earlier corpus and the selector-OR timeout input.
The timeout input also runs deterministically in the normal Rust regression suite.

Reproduce these checks with the [benchmark commands](../benchmarks/README.md#memory).
The benchmark Action records the full concurrent memory curve. Native allocation
checks, weak-reference assertions, sanitizer execution and fuzzing provide different
evidence; none alone proves every workload or arbitrary FFI misuse safe.
