# MetricsQL rollups

These helpers require `mode="metricsql"`. They operate within a lookbehind window; the `range_*` transforms on the transforms page operate across the full query interval instead.

```python
from metricraft import QueryBuilder as Q

query = Q.from_metric("queue_depth").count_gt_over_time(20, window="5m")
print(query.build(mode="metricsql"))
```

Here `value=20` is a numeric threshold and `window="5m"` is a duration. In contrast, `count_values_over_time(value="observed", ...)` uses its `value` parameter as an output **label name**. The parameter table records these differences explicitly.
