# 标签操作

选择器匹配器用来选择输入序列。这里的标签函数用于转换或过滤表达式结果，因此可以放在函数和聚合之后。

```python
from metricraft import QueryBuilder as Q

query = Q.from_metric("up").label_replace("host", "$1", "instance", "([^:]+):.*")
print(query.build(mode="promql"))
```

映射 API 接受显式的两个字符串组成的元组。替换值使用 `$1` 等后端捕获引用，不进行 Python 插值。仅限 MetricsQL 的操作会单独标记。
