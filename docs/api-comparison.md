# Calling conventions: Grafana and MetriCraft

The historical comparison used Grafana promql-builder revision
[`4febee560d00c40d20b36093ff5e9d5879b4c738`](https://github.com/grafana/promql-builder/tree/4febee560d00c40d20b36093ff5e9d5879b4c738).
This compares SDKs, not Grafana dashboards or a deployment requirement.

| Concern | Grafana promql-builder | MetriCraft direction and current new path |
| --- | --- | --- |
| Composition | Nested function calls plus modifier methods | Fluent immutable expressions |
| Output | `build()` returns a model; `str(query)` renders text | `build(mode=...)` returns text |
| Reusing expressions | Mutable builders in the inspected revision | Rust structural sharing; transformations return new values |
| Languages | PromQL | One common core for PromQL and MetricsQL |
| Execution | Query construction | Separate sync/async Prometheus/VictoriaMetrics client |
| Dynamic configuration | Application maps selections to calls | Same; application owns persistence and policy |
| Present coverage | Broader than our early native prototype | Migrated Rust core; pinned PromQL/MetricsQL catalog and syntax checks |

For example, Grafana uses `sum(rate(vector(...).range("5m"))).by(["job"])`;
MetriCraft uses `Q.from_metric(...).rate("5m").sum().by("job")`.
Neither style alone makes dynamic configuration possible or safe: the concrete
literal handling and application mapping matter.

Grafana can be the simpler fit for an application that only needs its supported
PromQL construction surface. MetriCraft aims to combine immutable construction,
explicit dialect checks and an independent client. The preferred API still depends on the application:
fluent or nested composition, required dialects, ownership guarantees and transport.

When combining Grafana with the MetriCraft client, pass `str(grafana_query)`
explicitly because the libraries give `.build()` different meanings.
