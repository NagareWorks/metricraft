# MetricsQL transforms

Unlike sliding rollups, `range_*` transforms summarize the entire returned MetricsQL interval. `running_*` transforms accumulate from the start of that interval. Their meaning depends on the range request's start, end and step.

```python
from metricraft import QueryBuilder as Q

query = Q.from_metric("queue_depth").keep_last_value().range_avg()
print(query.build(mode="metricsql"))
```

These methods construct expressions. They do not load samples or execute transformations in Python. `histogram_quantiles()` also supports an explicit Prometheus experimental form.
