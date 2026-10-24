# Validation & diagnostics

Diagnostics are read-only and do not send a query to a server. Structural analysis describes the expression graph, not an execution plan or a promise of backend cost.

```python
from metricraft import QueryBuilder as Q

query = Q.from_metric("up").sum().by("job")
assert query.validate("promql") == ""
print(query.analyze())
print(query.debug_positions(mode="promql"))
```

Graph diagnostics count shared nodes once. Rendered source positions describe each occurrence and use UTF-8 byte offsets. Output and work budgets bound both kinds of diagnostics.

`debug()` and `to_debug_json()` return schema-1 graph JSON with IDs for children
and persistent matcher links. `analyze()` returns a detached summary of unique
nodes, names, structural complexity and heuristic findings. Graph and analysis
defaults are 1 MiB output and 10,000 work items (the root, child edges and unique
matcher links). Positive `max_output_bytes` and `max_items` override these per call.

`debug_positions()` uses the same native renderer and dialect checks as `build()`.
Its spans describe expression occurrences; matcher details belong to graph
diagnostics. `visualize_positions(source_code)` verifies that the supplied text
matches the exact rendered query before returning source/span JSON. Applications
can display those spans themselves. Position diagnostics expand occurrences and
enforce both work and serialized-output limits. Snapshots are detached values;
they do not add cached strings or diagnostic fields to persistent nodes.
