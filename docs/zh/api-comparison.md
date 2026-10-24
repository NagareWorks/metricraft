# 调用方式：Grafana 与 MetriCraft

此对比使用 Grafana promql-builder 修订版 [`4febee560d00c40d20b36093ff5e9d5879b4c738`](https://github.com/grafana/promql-builder/tree/4febee560d00c40d20b36093ff5e9d5879b4c738)。这里比较 SDK，不是在比较 Grafana 仪表盘，也不要求部署 Grafana。

| 方面 | Grafana promql-builder | MetriCraft 当前方式与方向 |
| --- | --- | --- |
| 组合 | 嵌套函数调用加修饰方法 | 链式不可变表达式 |
| 输出 | `build()` 返回模型，`str(query)` 渲染文本 | `build(mode=...)` 返回文本 |
| 表达式复用 | 所检查修订版使用可变构建器 | Rust 结构共享，转换返回新值 |
| 语言 | PromQL | PromQL 与 MetricsQL 共用一个核心 |
| 执行 | 查询构建 | 独立的同步、异步 Prometheus/VictoriaMetrics 客户端 |
| 动态配置 | 应用将选项映射为调用 | 相同；持久化与策略由应用负责 |

例如，Grafana 使用 `sum(rate(vector(...).range("5m"))).by(["job"])`，MetriCraft 使用 `Q.from_metric(...).rate("5m").sum().by("job")`。调用风格本身并不能保证动态配置的可行性或安全性，关键在于具体的字面量处理和应用映射。

如果应用只需要 Grafana 已支持的 PromQL 构建能力，Grafana 可能更直接。MetriCraft 将不可变构建、显式方言校验与独立客户端结合起来。选择仍取决于应用：偏好链式还是嵌套组合、需要哪些方言、所有权保证和传输能力。

将 Grafana 与 MetriCraft 客户端组合使用时，请显式传入 `str(grafana_query)`，因为两者的 `.build()` 含义不同。
