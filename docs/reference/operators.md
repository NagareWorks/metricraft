# Operators & matching

Python `+`, `-`, `*`, `/`, `%` and `**` construct arithmetic expressions. Named aliases are documented below. Comparisons construct expressions too; they do not return Python booleans. Use `.and_()` / `.or_()` for query set operations.

```python
from metricraft import QueryBuilder as Q

errors = Q.from_metric("errors_total").rate("5m")
requests = Q.from_metric("requests_total").rate("5m")
query = (errors / requests).on("service").gt(0.01)
print(query.build(mode="promql"))
```

Attach matching/grouping modifiers to the binary expression. A comparison filters samples unless `.bool()` requests 0/1 values. Python `and`, `or`, `not` and `if expression` reject query expressions.
