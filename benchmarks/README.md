# Performance work

## Unified suite

Run the same entry point locally and in the [Benchmarks Action](../.github/workflows/benchmarks.yml):

```sh
python scripts/run_benchmarks.py --output /path/outside/checkout/new-run --memory-seconds 180
```

The runner builds the release library, selects it explicitly and runs:

- Pure Rust and Python/ctypes timings for equivalent selector/rate/aggregation shapes.
- Historical Python comparisons, including shared selectors and 1, 8 and 32 labels.
- Synthetic error-rate, histogram-quantile and 16-query configurable dashboard workloads.
- Native allocation accounting, retained Python owners and concurrent build/error/release probes.

Reports must use a new or empty directory outside the checkout. `CARGO_TARGET_DIR`
can reuse an existing build directory; otherwise builds go beside the reports.
`--iterations` and `--rounds` control timing samples; `--memory-seconds` and
`--workers` control concurrent stress. Defaults are 200 iterations, five rounds,
60 seconds and four workers. Memory tracing is excluded from timing comparisons.

The Action runs on relevant pull requests and development/release branch pushes,
or by manual dispatch, on Linux and Windows with Python 3.12. It publishes a Job
Summary and `metricraft-benchmarks-<os>` artifacts retained for 30 days. Reports
include environment/source/binary identity, phase measurements, memory samples
and subprocess logs. Failed checks propagate a failure and preserve partial reports.
Generated measurements are not committed or packaged. Timing regressions require
review; shared-runner noise is not treated as a deterministic performance gate.
Ownership, immutable-input and allocation-release assertions do fail the job.

The synthetic workloads replace the unavailable original application trace for
local acceptance work. They contain no HTTP I/O and do not establish application
end-to-end latency or backend result equivalence.

## Individual timing probes

`compare_immutable.py` compares the current Rust-backed facade with the historical
Python builder for the same selector/rate/aggregation workloads. It measures
construction plus release, repeated rendering, construction/render/release, and
branching from a shared selector at 1, 8 and 32 labels. There is no HTTP I/O.

```sh
cargo build --release --workspace --locked
# Set METRICRAFT_NATIVE_LIB to that release build's metricraft_ffi library.
python benchmarks/compare_immutable.py --iterations 300 --rounds 5 --output /path/to/timings.json
```

GC stays enabled. Each result records round-level median/min/max time per operation,
Python/platform information, native binary hash, revision and source hashes
(including new files). Both render paths validate; the new core performs more checks
during construction, so per-phase ratios are not equal-work comparisons. The complete
construction/render/release workload is the primary comparison.

These are local microbenchmarks, not an application speedup or latency guarantee.
The original application flame graph is unavailable. Use the synthetic workloads
as reproducible proxies, and collect application traces when they become available.
Measure pure Rust and Python/FFI separately before optimizing batching, arenas or
caches. Keep wide/deep trees, reuse, concurrency, allocations and release in scope.

Strict FP remains a requirement: no speedup may rely on mutating a shared query,
skipping validation or leaking native nodes.

## Memory

```sh
cargo run -p metricraft-core --release --example memory_profile --locked
python benchmarks/python_memory.py --branches 2000 --batches 10 --output /path/to/memory.json
python benchmarks/threaded_memory.py --seconds 180 --workers 4 --output /path/to/threaded-memory.json
```

The native probe counts requested allocation bytes with an instrumented system
allocator in a standalone process. It checks sharing versus independent construction,
retained versions, repeated build/release, deep chains and exponential expansion
rejection. It asserts that live allocation bytes return to baseline after each
scenario and runs automatically as part of `cargo test --workspace`.

The Python probe uses the real release library, weak references, `tracemalloc` and
process memory (Windows private/working-set bytes or Linux RSS). The Python samples
cover selector, label-copy and WITH branches, including per-call string owners.
Native probes check 10,000 label/template branches sharing a large selector and
release a 100,000-deep WITH chain.
These probes run through the same unified benchmark Action. The Python samples
include measurement records and allocator caches. They are not native allocation
counts; RSS need not return to its initial value after objects are released.
See [memory behavior and measured results](../docs/memory.md).

`python_baseline_timings.py` is the historical benchmark and does not define the
acceptance criteria for this migration.
