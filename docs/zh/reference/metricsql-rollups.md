# MetricsQL 窗口计算

这些辅助方法需要 `mode="metricsql"`。它们在回看窗口内工作；转换分类中的 `range_*` 则作用于整个查询区间。

```python
from metricraft import QueryBuilder as Q

query = Q.from_metric("queue_depth").count_gt_over_time(20, window="5m")
print(query.build(mode="metricsql"))
```

这里的 `value=20` 是数值阈值，`window="5m"` 是时长。相对地，`count_values_over_time(value="observed", ...)` 的 `value` 表示输出**标签名**。参数表会明确区分这些含义。
