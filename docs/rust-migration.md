# Rust migration status

The public builder is fully backed by the immutable Rust core. The retained
historical surface is [audited](legacy-api-migration.md); broader language support
now targets [Prometheus 3.15.0 and VictoriaMetrics 1.153.0](language-support.md).
There is one Python distribution containing the builder and the independent
sync/async HTTP client. The historical Python AST is an unshipped test fixture.

## Architecture

- Native nodes and persistent selector chains share immutable children through
  `Arc`. Operators, signatures, aggregation, syntax, templates, rendering and
  diagnostics have separate modules. Python operation groups are stateless.
- No Python AST traversal, global node/symbol registry, mutable metric setter or
  deep tree clone is used by the public builder. Last-owner release is iterative.
- The C ABI owns returned handles and strings, borrows children during a call,
  checks ABI 4, and isolates errors per thread. Callers must respect pointer lifetimes.
- Rendering checks exact cached output size and expanded-node budgets before
  allocating. Diagnostics have their own bounded unique-node traversal.
- WITH bindings and functions remain native shared nodes with lexical scope checks;
  building does not expand macros or retain a global template cache.

## Validation

The workspace runs native regression/allocation tests, Python 3.8+ contracts,
upstream parser checks, and real-backend integration. The compatibility Action
also discovers current official capabilities and submits catalog witnesses to
both pinned backends. Reports are generated artifacts, not library data or unit tests.

The unified benchmark entry point covers pure Rust, ctypes, historical Python,
shared selectors/labels/templates, and concurrent create/build/error/release loops.
The unavailable original internal trace is replaced by synthetic application
workloads; these cannot establish production or HTTP end-to-end performance.

Linux ASan/leak detection and bounded libFuzzer runs exercise the same native
composition oracle. See [memory measurements](memory.md) and
[backend verification](backend-validation.md) for evidence and limitations.

## Release work

The multi-platform native wheel build and installation checks are configured in
GitHub Actions. They still need to pass for the exact release revision before
publication. No migrated release has been published from this working tree.
Future upstream versions are separate compatibility updates; main-branch
capabilities absent from the stable baseline remain explicit in generated reports.
