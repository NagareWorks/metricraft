# Operators & matching

Python operators construct immutable query expressions. Comparisons do not return
Python booleans, and none of these operations modifies its operands.

| Python | Query operation | Named alternative |
| --- | --- | --- |
| `a + b`, `a - b`, `a * b`, `a / b` | Arithmetic | `.add()`, `.sub()`, `.mul()`, `.div()` |
| `a % b`, `a ** b` | Remainder, exponentiation (`^` in PromQL) | `.mod()`, `.pow()` |
| `-a`, `+a` | Unary sign | `.negative()`, `.positive()` |
| `a > b`, `a >= b`, `a < b`, `a <= b` | Filtering comparison | `.gt()`, `.ge()`, `.lt()`, `.le()` |
| `a == b`, `a != b` | Filtering equality/inequality | `.eq()`, `.ne()` |
| `a & b`, `a \| b` | Vector set intersection/union | `.and_()`, `.or_()` |

A scalar can appear on either side of `+`, `-`, `*` and `/`. Reverse `%` and
`**` are not overloaded; write `Q.from_scalar(value)` explicitly on the left
when you need those forms. Python `^` is not the power operator: use `**`.

```python
from metricraft import QueryBuilder as Q

errors = Q.from_metric("errors_total").rate("5m")
requests = Q.from_metric("requests_total").rate("5m")
fraction = (errors / requests).on("service")
query = (fraction * 100) > 1
print(query.build(mode="promql"))
```

Attach matching/grouping modifiers to the binary expression. A comparison filters samples unless `.bool()` requests 0/1 values. Python `and`, `or`, `not` and `if expression` reject query expressions. Use `(a > 1) & (b < 5)` with explicit parentheses instead of chained comparisons or Python boolean operators.
