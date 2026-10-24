# Contributing

MetriCraft maintains one repository for the Rust core, C ABI, Python bindings and
VictoriaMetrics client. Documentation, examples and contribution guidance are
maintained in English and Chinese. Keep executable examples and API names consistent
across languages.

## Set up

Use Python 3.11+ for development and an installed Rust toolchain. The package
metadata still declares Python 3.8+; changes must respect that declaration until
it is explicitly revised. Use a dedicated virtual environment so an editable
development install does not replace the published package used by your other
applications. From the repository root:

```sh
python -m venv .venv
```

Activate with `.venv\Scripts\Activate.ps1` in Windows PowerShell or
`source .venv/bin/activate` on Linux/macOS, then:

```sh
python -m pip install -e ".[dev]"
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
- Mark MetricsQL-only methods with `@vm_only` and PromQL-only methods with
  `@prom_only`, and encode the corresponding
  restriction in the Rust node. Validate nested nodes for the selected build mode.
  For shared operations with dialect-specific forms, constrain the form only.
- Treat strings as data, not syntax. Do not add implicit raw-expression fallbacks.
- Keep client I/O independent from construction. Storage, UI, authorization and
  validation of query text loaded by an application remain outside this SDK.

See [the architecture](docs/architecture.md) for supported operations and responsibility
boundaries. Keep the query language scope focused on PromQL and MetricsQL.

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
the complete current SDK Python collection. API contracts use executable witnesses
against the Rust builder, and cover direct client construction and named configuration.
`check` combines Rust,
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
Build distributions from the repository root with `python -m build`. The Python
metadata lives beside the Rust workspace so source archives can be built on their
own. The C ABI is independent of CPython, so wheels use `py3-none` with a platform
tag. Python package versions are explicit in `pyproject.toml`; release tags must
match them exactly.
After building distributions, run `python scripts/check_python_package.py <dist>`
to verify client-only use of the installed SDK without source imports or native code.
Use `--require-bundled-native` to additionally verify the packaged Rust builder.
Add `--typing` to run the installed-wheel consumer contracts with mypy (Python
3.11+ for this check). The check runs outside the checkout and verifies fluent
return types, decorated methods, operators, client calls and rejected arguments.
Both `py.typed` and the inline annotations must ship in the wheel and sdist.
The typing CI job checks the built Linux wheel with mypy and Pyright. All
native-wheel jobs execute the three downloadable examples against the installed
package without a source or native-path fallback.

For a standalone typing check after building a wheel:

```sh
python scripts/check_python_typing.py /path/to/metricraft.whl
```

Install `pyright` and Node.js to add `--pyright`, matching the typing CI job.

Keep public builder annotations complete, including aliases and special methods.
Python types describe accepted argument shapes and return values; Rust still
checks expression kinds, dialect restrictions, feature flags and value ranges.

## Documentation website

English Markdown in `docs/` and Chinese Markdown in `docs/zh/` are shared with the
custom Astro site in `website/`. Maintain both languages when adding pages or API
contracts; translated headings keep the same explicit anchors as their English counterparts.
Use Node.js 24+ and Python 3.11+ to run `npm ci`, `npm run check` and
`npm run build` from `website/`. The build generates API signatures from source,
indexes local search and checks links, fragments and assets. CI includes these
checks in `required-checks`. See [the website guide](website/README.md) for
preview and contribution instructions.

## GitHub Actions

CI runs automatically for maintainers with write access and contributors who have
already had a commit or pull request merged into this repository. Configure
GitHub Actions' fork-workflow policy to **Require approval for first-time
contributors**. A maintainer with write access must review and approve workflows
from contributors without a prior merged contribution. Opening a second pull
request does not by itself remove that requirement.

The `release` environment separately protects package publication. Repository
administrators must keep its reviewers limited to current maintainers with write
access; adding a collaborator does not automatically add a release reviewer.

`Benchmarks` uses `python scripts/run_benchmarks.py --output <external-directory>`
on Linux and Windows for relevant pull requests, branch pushes and manual runs.
It measures pure Rust and the current Python/ctypes facade, then runs synthetic application
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
3.15, and runs the pinned PromQL/MetricsQL parser corpus. Set branch protection's
required status to `required-checks`; failures, cancellations and skipped required
jobs all prevent success.

The reusable `Packages` workflow tests the Rust core/ABI and builds wheels for
Linux x86_64, Windows x86_64, macOS Intel and macOS Apple Silicon. Linux builds run
inside manylinux_2_28 and pass `auditwheel repair`. Each wheel contains one native
library and its source SHA; validation checks platform metadata, RECORD hashes,
client-only usage and installed native query construction without source fallbacks.
Every built wheel contains the native library and has a platform tag. The built
wheels are also installed into isolated Python 3.14 and 3.15 environments on all
four platforms, without requiring a source checkout or a Rust toolchain.

Free-threaded Python 3.14t and 3.15t run the complete Python suite with
`PYTHON_GIL=0` and `METRICRAFT_REQUIRE_FREE_THREADED=1`. Session guards fail if the
interpreter is not a free-threaded build or the GIL is enabled. The same wheel
installation matrix includes both free-threaded runtimes; its subprocesses
explicitly keep the GIL disabled even under Python's isolated mode.

Artifacts are named `metricraft-dist-<platform>` and `metricraft-dist-sdist` and
are retained for 14 days. The sdist includes the Python SDK, Rust sources and Cargo
lockfile. CI rebuilds and installs it outside the checkout with a fresh native
build directory. Source installations require Rust and a platform C linker;
missing toolchains fail installation instead of installing an unusable builder.

`Release` reuses the complete CI workflow at the selected commit, then publishes
the already-tested artifacts without rebuilding them. A pushed `v*` tag triggers
publication after version/source checks pass. Manual dispatch defaults to build
only; publication requires selecting an existing version tag and setting `publish`.
Configure PyPI Trusted Publishing for `NagareWorks/metricraft`, `release.yml`,
environment `release`. Publication uses GitHub OIDC, with no long-lived PyPI token.
Regular CI uses read-only permissions and does not need publication credentials.
After publication, all four platforms download their wheel from public PyPI,
compare its SHA-256 with the tested artifact and run the isolated installation
checks again. A successful upload alone is not release completion.

## Submit a change

Create a focused branch and pull request. Changes to `main` require resolved
review conversations and successful `required-checks`. Maintainers with write
access can merge, including their own pull requests; a separate approving review
is not required. Use squash (preferred) or rebase. Merge commits, force pushes
and branch deletion are disabled on `main`.

Describe the problem, resulting behavior,
compatibility impact and checks performed. Keep unrelated formatting out of the
change. Update the relevant example when an API changes; keep README short.
Use descriptive commit subjects (for example `fix(query): preserve shared selectors`).

Unless explicitly stated otherwise, contributions submitted for inclusion are
licensed under [Apache 2.0](LICENSE), the same license as the project.
No separate CLA is required. Contributors are credited through GitHub history.
Do not include credentials, private deployment addresses, or company-specific
configuration in examples or test fixtures.
