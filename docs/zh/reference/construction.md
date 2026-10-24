# 创建与构建表达式

表达式从工厂方法开始。导入 `QueryBuilder as Q`；传给 `function()` 的 Python 字符串始终是字面量，不会被解析为查询。构建返回文本，不执行 I/O。

```python
from metricraft import QueryBuilder as Q

base = Q.from_metric("http_requests_total").where_eq("job", "api")
query = base.rate("5m").sum().by("job")
print(query.build(mode="promql"))
```

默认方言为 MetricsQL，面向 Prometheus 时请显式选择 PromQL。类型检查可能发生在构建表达式时；方言和输出预算还会在最终构建时检查完整表达式。`TypeError` 表示 Python 输入不兼容，`ValueError` 表示原生构建或输出约束不满足。
