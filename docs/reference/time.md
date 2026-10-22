# Time & subqueries

A range selects raw samples from a selector. A subquery repeatedly evaluates a computed expression. Neither is a client request: `DatabaseClient.query_range()` is the I/O operation.

```python
from metricraft import QueryBuilder as Q

query = (Q.from_metric("requests_total").rate("5m")
         .subquery("1h", "1m").max_over_time())
print(query.build(mode="promql"))
```

Use positive duration strings such as `5m` or `1h30m`. Explicit feature opt-ins are required for supported Prometheus duration expressions and extended range selectors. A server must enable the matching feature too.
