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
