# 速率与窗口统计

从即时选择器开始时应给出窗口，也可以对已有范围表达式应用窗口函数。裸选择器不指定窗口时，会选择 MetricsQL 的隐式 rollup 行为，无法构建为 PromQL。

```python
from metricraft import QueryBuilder as Q

counter = Q.from_metric("requests_total")
print(counter.rate("5m").build(mode="promql"))
gauge = Q.from_metric("temperature_celsius")
print(gauge.avg_over_time("10m").build(mode="promql"))
```

计数器使用 rate、increase，仪表值使用 delta、deriv。函数同名不代表 Prometheus 和 VictoriaMetrics 的窗口边界行为相同。`window` 与兼容别名 `duration` 互斥。
