# Python API

从 `metricraft` 导入公共入口。`QueryBuilder` 负责不可变构建，`DatabaseClient` 负责 I/O，所有配置也都在同一个包中。

<a id="python-type-hints"></a>

## Python 类型提示

下一个版本将包含内联类型提示和供类型检查器、编辑器使用的 `py.typed` 标记。这些改动已进入主线，但尚未包含在已发布的 `0.3.0rc1` wheel 中。

链式调用、Python 运算符以及带方言标记的方法返回 `QueryBuilder`，`build()` 返回 `str`。客户端调用返回 `MetricsQueryResult` 或对应元数据结果，异步等待后的类型也相同。安装包 CI 会验证这些约定，并确保 mypy 和 Pyright 拒绝无效参数类型。

签名使用以下公共输入形式（对应共享类型别名）：

| 类型 | 可接受的 Python 值 |
| --- | --- |
| `Number` | `int` 或 `float`（运行时拒绝布尔值） |
| `ScalarInput` | 数字或 `QueryBuilder` 表达式 |
| `StringInput` | 字符串或字符串值表达式 |
| `QueryInput` | 数字、字符串或 `QueryBuilder` 表达式 |
| `Window` | 时长字符串或时长表达式 |
| `BuildMode` | `QueryMode`，或字面量 `"promql"` / `"metricsql"` |
| `MatchInput` | 选择器字符串、`QueryBuilder`，或包含两者的序列，例如列表、元组 |

Python 注解检查参数形式并保留链式返回类型。表达式种类、允许的值、方言和功能开关仍由 Rust 验证。例如，作为标量参数的 `QueryBuilder` 必须在所选语言中表示标量。诊断信息与自定义 HTTP 载荷含动态数据，因此相应字典有意保留 `Any` 值。

<a id="reading-the-reference"></a>

## 阅读参考手册

参考手册按分类组织。签名、参数名、默认值和声明链接直接来自 Python 源码；每个方法还包含用途、参数类型、允许值和返回约定。新增方法或参数缺少说明时，文档构建会失败。

请区分 SDK 校验和后端语义。例如，分位数通常在 `[0, 1]` 内，但后端可能定义范围之外的结果；参考手册不会把所有建议范围都描述为本地强制校验。所有构建器组合都返回新的共享表达式；客户端请求执行 I/O，配置对象则有各自的可变性约定。

`vm_only` 表示仅限 MetricsQL，`prom_only` 表示仅限 PromQL，`prom_experimental` 要求显式启用 Prometheus 实验功能。没有标记并不保证每一种参数形式都适用于两种语言：Rust 会在构建时检查完整表达式。参见[语言支持](language-support.md)。

<a id="main-entry-points"></a>

## 主要入口

| 入口 | 用途 |
| --- | --- |
| `QueryBuilder` | 工厂方法、不可变组合与 `.build(mode)` |
| `DatabaseClient` | 查询、元数据和 VictoriaMetrics 写入请求 |
| `PrometheusConfig` | 标准 Prometheus 端点 |
| `VMSingleConfig` | VictoriaMetrics 单机端点 |
| `VMClusterConfig` | VictoriaMetrics 集群端点与租户选择 |
| `HttpClientOptions` | 超时、请求头与自定义传输 |
| `register_config`, `get_config`, `set_default_instance` | 可选的命名配置注册表 |
| `MetricsQueryResult`, `MetricsInsertData`, `TimeValue` | 客户端结果、写入数据与时间约定 |

连贯示例见[构建指南](building-queries.md)和[客户端指南](client-guide.md)。在 GitHub 阅读时，也可以查看[构建器源码](../../python/metricraft/src/metricraft/builder/query_builder.py)与[客户端源码](../../python/metricraft/src/metricraft/client/db_client.py)。
