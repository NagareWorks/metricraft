# 运算符与匹配

Python 运算符构建不可变查询表达式。比较操作不返回 Python 布尔值，这些操作都不会修改操作数。

| Python | 查询操作 | 命名方法 |
| --- | --- | --- |
| `a + b`, `a - b`, `a * b`, `a / b` | 算术 | `.add()`, `.sub()`, `.mul()`, `.div()` |
| `a % b`, `a ** b` | 余数、乘方（PromQL 中为 `^`） | `.mod()`, `.pow()` |
| `-a`, `+a` | 一元符号 | `.negative()`, `.positive()` |
| `a > b`, `a >= b`, `a < b`, `a <= b` | 过滤式比较 | `.gt()`, `.ge()`, `.lt()`, `.le()` |
| `a == b`, `a != b` | 相等或不等过滤 | `.eq()`, `.ne()` |
| `a & b`, `a \| b` | 向量集合交集或并集 | `.and_()`, `.or_()` |

标量可以放在 `+`、`-`、`*`、`/` 任意一侧。SDK 没有重载反向 `%` 与 `**`；需要这些形式时，在左侧显式写 `Q.from_scalar(value)`。Python 的 `^` 不是乘方运算符，请使用 `**`。

```python
from metricraft import QueryBuilder as Q

errors = Q.from_metric("errors_total").rate("5m")
requests = Q.from_metric("requests_total").rate("5m")
fraction = (errors / requests).on("service")
query = (fraction * 100) > 1
print(query.build(mode="promql"))
```

匹配与分组修饰符应加在二元表达式上。比较默认过滤样本，调用 `.bool()` 才会请求 0/1 结果。Python 的 `and`、`or`、`not`、`if expression` 会拒绝查询表达式。请使用显式括号，例如 `(a > 1) & (b < 5)`，不要使用链式比较或 Python 布尔运算符。
