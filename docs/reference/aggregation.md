# Aggregation & grouping

Aggregation without grouping is valid in both dialects. `.by()` retains selected labels; `.without()` drops selected labels. Choose one after the aggregation; do not call both on the same result.

```python
from metricraft import QueryBuilder as Q

aggregate = Q.from_metric("requests_total").rate("5m").sum()
by_service = aggregate.by("service")
without_instance = aggregate.without("instance")
print(by_service.build(mode="promql"))
print(without_instance.build(mode="promql"))
```

Both variants share the original expression. Additional aggregation inputs (`*others`) require MetricsQL. Numeric parameter recommendations below describe useful backend domains; where no literal bound is enforced by the SDK, that distinction is stated.
