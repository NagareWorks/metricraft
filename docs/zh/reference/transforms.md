# MetricsQL 转换

与滑动窗口计算不同，`range_*` 汇总整个 MetricsQL 返回区间，`running_*` 从区间起点开始累计。它们的含义取决于范围请求的 start、end 和 step。

```python
from metricraft import QueryBuilder as Q

query = Q.from_metric("queue_depth").keep_last_value().range_avg()
print(query.build(mode="metricsql"))
```

这些方法只构建表达式，不加载样本，也不在 Python 中执行转换。`histogram_quantiles()` 还支持显式的 Prometheus 实验形式。
