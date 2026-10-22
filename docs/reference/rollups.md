# Rates & window statistics

Give a window when starting from an instant selector, or apply a rollup to an existing range. Omitting a window on a bare selector selects MetricsQL implicit-rollup behavior and cannot build as PromQL.

```python
from metricraft import QueryBuilder as Q

counter = Q.from_metric("requests_total")
print(counter.rate("5m").build(mode="promql"))
gauge = Q.from_metric("temperature_celsius")
print(gauge.avg_over_time("10m").build(mode="promql"))
```

Use rates and increases with counters, and delta/deriv with gauges. Equal function names do not imply identical Prometheus and VictoriaMetrics sample-edge behavior. `window` and its compatibility alias `duration` are mutually exclusive.
