# Factories & building

Every expression starts with a factory. Import `QueryBuilder as Q`; a Python string passed to `function()` is a literal, never a parsed query. Building returns text and does not perform I/O.

```python
from metricraft import QueryBuilder as Q

base = Q.from_metric("http_requests_total").where_eq("job", "api")
query = base.rate("5m").sum().by("job")
print(query.build(mode="promql"))
```

The default dialect is MetricsQL. Select PromQL explicitly for Prometheus. Type checks can happen during construction; dialect and output-budget checks also inspect the complete expression at build time. `TypeError` signals incompatible Python inputs; `ValueError` reports invalid native construction or build constraints.
