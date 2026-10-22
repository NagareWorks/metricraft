# Math, sorting & histograms

These methods usually consume instant vectors. Functions such as `scalar()` change the query value type; Rust checks whether subsequent composition is legal.

```python
from metricraft import QueryBuilder as Q

buckets = Q.from_metric("request_duration_seconds_bucket").rate("5m")
query = buckets.sum().by("le").histogram_quantile(0.95)
print(query.build(mode="promql"))
```

Calendar functions interpret sample **values** as Unix timestamps in UTC. They do not automatically read sample timestamps: use `.timestamp()` when that is what you want. Histogram encoding and native-histogram support depend on the backend.
