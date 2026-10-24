# 选择器与过滤

应在转换选择器之前添加匹配器。等值匹配会转义值，正则方法接受有意提供的 RE2 模式。即使查询中的字符串已经安全引用，正则仍可能匹配大量值。

```python
from metricraft import QueryBuilder as Q

query = (Q.from_metric("http_requests_total")
         .where_eq("environment", "production")
         .where_regex("status", "5.."))
print(query.build(mode="promql"))
```

同一个选择器的所有匹配器必须同时满足。不存在的标签按空值处理。应用代码仍需决定用户可选择的指标名、操作和标签名。
