# 时间与子查询

范围从选择器中选取原始样本，子查询则重复计算一个已组合的表达式。两者都不是客户端请求；`DatabaseClient.query_range()` 才是执行 I/O 的操作。

```python
from metricraft import QueryBuilder as Q

query = (Q.from_metric("requests_total").rate("5m")
         .subquery("1h", "1m").max_over_time())
print(query.build(mode="promql"))
```

使用 `5m`、`1h30m` 等正时长字符串。Prometheus 的时长表达式与扩展范围选择器需要显式启用相应功能，服务器也必须启用同一功能。
