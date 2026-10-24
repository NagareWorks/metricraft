# 后端结果验证

解析器接受查询，并不能证明查询的语义。独立集成脚本 `scripts/check_backend_results.py` 会启动固定版本 Prometheus 3.15.0 和 VictoriaMetrics 1.153.0，向两者导入相同合成时间序列，并对照独立计算的预期值检查结果。

测试集覆盖有分组和无分组聚合、速率、增长量、错误率比值、直方图分位数、过滤比较与 `bool`、`group_left` 向量匹配、集合运算、offset、固定 `@` 时间、子查询、clamp、转义标签值、缺失序列和标量算术。MetricsQL 另有 `default`、`if`、`ifnot`、`union` 和 23 个标签操作样例。标签检查包含有序复制与移动、缺失标签、空映射、转义值、完整匹配、替换捕获、非数字值和指标名处理。

扩展测试还验证 WITH 值、函数、字符串过滤，选择器分支、标量聚合、元组过滤、可变参数聚合、聚合限制、位图、带前缀连接、可移植直方图分位数、时长表达式、anchored/smoothed 范围和 fill 修饰符。共有 26 个 PromQL 与 62 个 MetricsQL 数值样例，不代表两种语言数值等价。

其中 4 个 PromQL 和 19 个 MetricsQL 表达式还在三个求值时刻运行范围查询。比较要求标签集与时间戳精确相同，数值使用明确浮点容差。空、重复或不完整结果不能静默通过；工具测试还会验证故意错误的结果确实被验证器拒绝。

主路径先构建字符串、保存为 JSON、重新读取，再通过 `DatabaseClient` 执行，也检查同步和异步 SDK 表达式参数。客户端收到 SDK 构建器时，先按后端配置选择方言再发送请求；原始文本则直接传递，不解析或清理。

<a id="reproduce"></a>

## 复现

构建原生库，并用 `METRICRAFT_NATIVE_LIB` 指向它。提供真实后端可执行文件；Windows 上优先直接提供可执行文件路径，避免会注入自身服务配置的包装脚本。

```sh
python scripts/check_backend_results.py \
  --output /path/outside/checkout/new-backend-run \
  --prometheus /path/to/prometheus \
  --promtool /path/to/promtool \
  --victoria-metrics /path/to/victoria-metrics-prod
```

添加 `--matrix /path/to/generated/compatibility/matrix.json`，可将独立发现的目录样例作为即时与范围请求执行。签名是否被接受与预期数值检查分开记录。兼容性 Action 运行两个阶段并保留报告，发现出的清单不进入已安装 SDK 或单元测试。

只接受仓库之外的新输出目录。服务器在回环地址的临时端口监听，使用各自存储，无论成功或失败都会终止，不接触已有数据库。Prometheus 数据通过 promtool 导入，VictoriaMetrics 数据通过 JSON-line 端点导入。

报告包含测试数据、保存的查询字符串、预期与实际结果、日志、后端版本、修订号及源码和原生库哈希。本地存储目录会保留以便诊断；CI 产物仅保留较小的复现文件，不包含数据库存储。某次运行的存储不再需要后即可删除。

CI 的 `conformance` 任务先运行解析器检查，再验证结果。失败会阻止 `required-checks` 成功和软件包发布；即使失败，Job Summary 与 `metricraft-backend-results` 产物也会保留已有结果。这项验证独立于单元测试、计时基准和上游兼容性发现报告。版本升级必须显式重新审视语义预期。
