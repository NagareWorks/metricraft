# Selectors & filters

Apply matchers before transforming a selector. Equality values are escaped; regex methods accept intentional RE2 patterns. A regex may match many values even though its query-string representation is safely quoted.

```python
from metricraft import QueryBuilder as Q

query = (Q.from_metric("http_requests_total")
         .where_eq("environment", "production")
         .where_regex("status", "5.."))
print(query.build(mode="promql"))
```

All matchers on one selector must hold. An absent label behaves as an empty value. Application code still chooses which metric names, operations and label names users may select.
