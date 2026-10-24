# 聚合与分组

两种方言都支持不分组的聚合。`.by()` 保留指定标签，`.without()` 移除指定标签。在聚合之后选择其中一种方式，不要对同一个结果同时调用两者。

```python
from metricraft import QueryBuilder as Q

aggregate = Q.from_metric("requests_total").rate("5m").sum()
by_service = aggregate.by("service")
without_instance = aggregate.without("instance")
print(by_service.build(mode="promql"))
print(without_instance.build(mode="promql"))
```

两种分组形式共享原始表达式。额外的聚合输入（`*others`）需要 MetricsQL。下方数字参数的建议范围描述后端中有用的取值域；SDK 没有强制限制的地方会明确说明。
