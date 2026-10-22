# MetricsQL templates

Bindings are local to a query. No global symbol registry or raw string substitution is used. References must resolve and their declared result types must agree with the binding.

```python
from metricraft import QueryBuilder as Q

query = Q.reference("base").sum().with_(base=Q.from_metric("up"))
print(query.build(mode="metricsql"))
```

Bindings follow keyword insertion order: earlier bindings are visible to later ones. Duplicate/invalid parameter names, unresolved references and recursion are rejected.
