# Contributing

MetriCraft maintains one repository for the Rust core, C ABI, Python bindings and
VictoriaMetrics client. Documentation, examples and contribution guidance are
maintained in English only.

## Set up

Use Python 3.11+ for development and an installed Rust toolchain. The package
metadata still declares Python 3.8+; changes must respect that declaration until
it is explicitly revised. Install the Python package from the repository root:

```sh
python -m pip install -e "python/metricraft[dev]"
python scripts/dev.py build
```

Set `CARGO_TARGET_DIR` before building if artifacts should live outside the
checkout. `METRICRAFT_NATIVE_LIB` can point to an explicit shared library.
Client-only imports must work without any native library.

## Architecture rules

- Support PromQL and MetricsQL through one builder and one immutable Rust AST.
- Keep transformations pure and share immutable subexpressions. Never mutate an
  expression that a caller can retain or reuse.
- Put query semantics, validation and rendering in `metricraft-core`. Keep the
  C ABI concerned with conversion, errors and ownership; Python is a fluent facade.
- Mark MetricsQL-only methods with `@vm_only` and encode the corresponding
  restriction in the Rust node. Validate nested nodes for the selected build mode.
  For shared operations with dialect-specific forms, constrain the form only.
- Treat strings as data, not syntax. Do not add implicit raw-expression fallbacks.
- Keep client I/O independent from construction. Storage, UI, authorization and
  validation of query text loaded by an application remain outside this SDK.

See [the architecture](docs/architecture.md) for supported operations and migration
boundaries. Do not expand the old SQL/Flux or provider-based query abstractions.

## Validate changes

```sh
cargo fmt --all -- --check
python scripts/dev.py rust
python scripts/dev.py query
python scripts/dev.py client
python scripts/dev.py smoke
python scripts/dev.py tests
python scripts/dev.py conformance
```

`query` runs workspace contracts for immutable expressions, literals, dialects,
modifiers and client-only imports. `client` runs mocked HTTP tests. `tests` runs
the complete unified Python collection, including source-only migration fixtures.
Obsolete provider-discovery tests were retired with that API; direct client
construction and named configuration are covered instead. `check` combines Rust,
the complete Python suite and offline examples. Test commands do not generate
coverage or bytecode files by default.

`conformance` additionally requires Go 1.24.2+ and `promtool` on PATH. CI pins Go
1.25.3, Prometheus 3.15.0 and MetricsQL v0.87.4; the MetricsQL module is test-only.
This checks generated syntax with upstream parsers, not query execution or complete
language coverage. Go caches and temporary rule files follow `CARGO_TARGET_DIR`'s
parent directory by default; `GOCACHE`/`GOMODCACHE` can override the caches.

CI also evaluates a synthetic corpus against isolated Prometheus 3.15.0 and
VictoriaMetrics 1.153.0 servers through the SDK client. This checks values, labels
and timestamps, including saved query text, sync/async calls and range evaluation.
See [backend result validation](docs/backend-validation.md) for local reproduction.
Backend failures block the existing conformance job and release gate; generated
reports stay in Actions artifacts, outside the library and unit-test collection.

The independent [compatibility workflow](.github/workflows/compatibility.yml)
discovers official PromQL/MetricsQL capabilities and publishes a Job Summary plus
the `metricraft-upstream-compatibility` Actions artifact. The artifact contains
`matrix.md`, `matrix.json`, verified upstream source snapshots and the run log.
Reports, inventories and comparison snapshots are generated outputs, never committed.
This workflow is separate from unit tests and the pinned release parser corpus.

For local reproduction, build the native SDK and run
`python scripts/compatibility/check.py --output /path/outside/checkout/compatibility`.
It requires curl, Go and promtool 3.15.0. `--offline` reuses that directory's verified
source snapshot. To check drift, download a previous artifact and pass
`--compare /download/matrix.json --check`; no repository baseline is maintained.
Missing signatures, unmatched topics and parser-rejected output fail. Backend-owned
semantics, canonical formatting and unreleased additions are explicitly classified. `sampled` means the listed witnesses parsed, not complete language or
backend-semantic support. Network/extraction failures never silently use stale data.

Add focused regression tests for behavior changes. For performance work, measure
representative construction and rendering separately from HTTP I/O; include the
revision, build profile and workload. Do not infer speedups from the use of Rust.
Native wheel publication requires the bundled library and an installed-wheel test.
After building distributions, run `python scripts/check_python_package.py <dist>`
to verify the installed SDK without source imports or native code. This also
checks that historical fixtures and provider entry points are not shipped.
Use `--require-bundled-native` to additionally verify the packaged Rust builder.

## GitHub Actions

A maintainer with write access must approve workflow execution through the
`ci-review` environment before repository code is checked out or executed.
All external contributors also require GitHub's fork-workflow approval.
The `release` environment separately protects package publication. Repository
administrators must keep environment reviewers limited to current maintainers
with write access; adding a collaborator does not automatically add a reviewer.


`Benchmarks` uses `python scripts/run_benchmarks.py --output <external-directory>`
on Linux and Windows for relevant pull requests, branch pushes and manual runs.
It compares pure Rust, ctypes and historical Python, then runs synthetic application
workloads and memory/lifetime probes. Timings are reported for review; failed
correctness or release checks fail the workflow. See the
[benchmark guide](benchmarks/README.md) for reproduction and artifact details.

`Native robustness` runs Rust tests with AddressSanitizer/leak detection on Linux,
followed by a bounded libFuzzer session. It is separate from timing measurement and
runs for relevant pull requests or manual dispatch. Deterministic composition seeds
also run in ordinary Rust regression tests. The shared oracle checks immutable
inputs, cached sizes, build limits and release paths; it does not prove backend
semantics. Logs, corpus and crash inputs are uploaded as Actions artifacts.
Reproduce the nightly sanitizer and fuzz commands from
[the workflow](.github/workflows/robustness.yml); generated corpus/build output
belongs outside the checkout. A configured workflow is not execution evidence.

`CI` runs on pushes to development/release branches, pull requests and manual
dispatch. It checks workflow syntax and Rust formatting, tests Python 3.8 through
3.13, and runs the pinned PromQL/MetricsQL parser corpus. Set branch protection's
required status to `required-checks`; failures, cancellations and skipped required
jobs all prevent success.

The reusable `Packages` workflow tests the Rust core/ABI and builds wheels for
Linux x86_64, Windows x86_64, macOS Intel and macOS Apple Silicon. Linux builds run
inside manylinux_2_28 and pass `auditwheel repair`. Each wheel contains one native
library and its source SHA; validation checks platform metadata, RECORD hashes,
client-only usage and installed native query construction without source fallbacks.
The staging `py3-none-any` wheel is never uploaded as a release artifact.

Artifacts are named `metricraft-dist-<platform>` and `metricraft-dist-sdist` and
are retained for 14 days. The sdist is the lightweight Python source distribution;
it contains no native payload or Rust sources. A Git checkout is required to build
the Rust core locally. Historical Python AST fixtures remain source-checkout only.

`Release` reuses the complete CI workflow at the selected commit, then publishes
the already-tested artifacts without rebuilding them. A pushed `v*` tag triggers
publication after version/source checks pass. Manual dispatch defaults to build
only; publication requires selecting an existing version tag and setting `publish`.
Configure PyPI Trusted Publishing for `release.yml`, or provide `PYPI_API_TOKEN`
(`PYPI_PASSWORD` is accepted for existing token configurations). Regular CI uses
read-only permissions and does not need publication credentials.

## Submit a change

Create a focused branch and pull request. Changes to `main` require a current
approval from someone with write access, approval of the latest push by someone
other than its pusher, resolved review conversations and successful
`required-checks`. New commits dismiss stale approvals. Only maintainers with
write access can merge, using squash (preferred) or rebase; merge commits,
force pushes and branch deletion are disabled on `main`.

 Describe the problem, resulting behavior,
compatibility impact and checks performed. Keep unrelated formatting out of the
change. Update the relevant example when an API changes; keep README short.
Use descriptive commit subjects (for example `fix(query): preserve shared selectors`).

Unless explicitly stated otherwise, contributions submitted for inclusion are
licensed under [Apache 2.0](LICENSE), the same license as the project.
No separate CLA is required. Contributors are credited through GitHub history.
Do not include credentials, private deployment addresses, or company-specific
configuration in examples or test fixtures.
