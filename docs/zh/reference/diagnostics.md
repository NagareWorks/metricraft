# 验证与诊断

诊断是只读操作，不向服务器发送查询。结构分析描述表达式图，不是执行计划，也不承诺后端成本。

```python
from metricraft import QueryBuilder as Q

query = Q.from_metric("up").sum().by("job")
assert query.validate("promql") == ""
print(query.analyze())
print(query.debug_positions(mode="promql"))
```

图诊断对共享节点只计数一次。渲染源码位置描述每次出现，使用 UTF-8 字节偏移。两类诊断都受输出与工作预算约束。

`debug()` 和 `to_debug_json()` 返回 schema-1 图 JSON，子节点和持久化匹配器链接使用 ID 引用。`analyze()` 返回独立摘要，包含唯一节点、名称、结构复杂度和启发式发现。图与分析默认限制为 1 MiB 输出和 10,000 个工作项（根节点、子边和唯一匹配器链接）。单次调用可用正的 `max_output_bytes`、`max_items` 覆盖。

`debug_positions()` 使用与 `build()` 相同的原生渲染器和方言检查。范围信息描述表达式的各次出现，匹配器细节属于图诊断。`visualize_positions(source_code)` 先核对传入文本与渲染查询完全一致，再返回源码与范围 JSON，应用可自行呈现。位置诊断展开每次出现，同时限制工作量和序列化输出。快照是独立返回值，不向持久节点增加缓存字符串或诊断字段。
