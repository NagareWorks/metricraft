# 数学、排序与直方图

这些方法通常接收即时向量。`scalar()` 等函数会改变查询值类型，Rust 会检查后续组合是否合法。

```python
from metricraft import QueryBuilder as Q

buckets = Q.from_metric("request_duration_seconds_bucket").rate("5m")
query = buckets.sum().by("le").histogram_quantile(0.95)
print(query.build(mode="promql"))
```

日历函数把样本的**值**解释为 UTC Unix 时间戳，不会自动读取样本本身的时间戳；需要后者时使用 `.timestamp()`。直方图编码与原生直方图支持取决于后端。
