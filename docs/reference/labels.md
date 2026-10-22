# Label operations

Selector matchers choose input series. Label functions here transform or filter the result of an expression, so they can be applied after functions and aggregation.

```python
from metricraft import QueryBuilder as Q

query = Q.from_metric("up").label_replace("host", "$1", "instance", "([^:]+):.*")
print(query.build(mode="promql"))
```

Mapping APIs take explicit two-string tuples. Replacements use backend capture references such as `$1`; Python interpolation is not involved. MetricsQL-only operations are marked individually.
