# MetricsQL 模板

绑定仅在当前查询中有效，不使用全局符号注册表或原始字符串替换。引用必须能够解析，声明的结果类型也必须与绑定一致。

```python
from metricraft import QueryBuilder as Q

query = Q.reference("base").sum().with_(base=Q.from_metric("up"))
print(query.build(mode="metricsql"))
```

绑定遵循关键字插入顺序：更早的绑定对后面的绑定可见。重复或无效的参数名、未解析引用及递归会被拒绝。
