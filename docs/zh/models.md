# 模型与公共类型

<a id="query-responses"></a>

## 查询响应

`MetricsQueryResult.from_dict(response_data: dict[str, Any]) -> MetricsQueryResult` 将解码后的后端响应转换为结果对象。请传入包含 `status` 和 `data` 的完整响应；可选错误、警告和 VictoriaMetrics 字段会保留。`result.to_dict() -> dict[str, Any]` 可转换回原响应结构。建议使用该工厂，而不是手动填写 dataclass 内部以下划线开头的字段。

| 属性 | 类型 | 含义 |
| --- | --- | --- |
| `status` | `str` | 后端状态，通常为 `success` 或 `error` |
| `is_success`, `is_error` | `bool` | 状态是否等于对应值 |
| `data` | `dict[str, Any] \| None` | 解码后的 `resultType` 与 `result` 对象 |
| `result_type` | `str \| None` | 若存在，为 `vector`、`matrix`、`scalar` 或 `string` |
| `result` | `list \| None` | 后端样本，结构由 `result_type` 决定 |
| `error`, `error_type` | `str \| None` | 后端错误文本与分类 |
| `warnings` | `list[str] \| None` | 后端非致命警告 |
| `is_partial` | `bool` | VictoriaMetrics 部分响应标记，默认 false |
| `stats` | `dict[str, Any] \| None` | VictoriaMetrics 执行统计 |
| `trace` | `dict[str, Any] \| None` | 请求跟踪时返回的 VictoriaMetrics 跟踪树 |
| `execution_time_ms` | `float \| None` | 便捷读取 `stats.executionTimeMsec` |
| `series_fetched` | `int \| str \| None` | 便捷读取 `stats.seriesFetched` |

```python
from metricraft import MetricsQueryResult

result = MetricsQueryResult.from_dict({
    "status": "success",
    "data": {"resultType": "vector", "result": [
        {"metric": {"job": "api"}, "value": [1767225600, "1"]}
    ]},
})
assert result.is_success
print(result.result)
```

即时向量格式为 `[{"metric": labels, "value": [timestamp, "value"]}]`。矩阵使用包含时间戳和值对列表的 `values`；标量与字符串使用 `[timestamp, "value"]`。值保留为后端字符串，可以表示非有限数。冻结的结果包装器不会递归冻结其中的字典与列表。

<a id="metadata-responses"></a>

## 元数据响应

从 `metricraft.models` 导入 `SeriesResult`、`LabelsResult`、`LabelValuesResult`。它们都支持 `from_dict(response: dict)`、`to_dict() -> dict`，以及构造参数 `(status: str, data=None, error: str | None=None, error_type: str | None=None)`。

成功时使用 `status="success"` 和下表对应的列表结构；失败时使用 `"error"` 及错误详情。包装器不会按 schema 验证任意后端载荷。

| 类 | 有类型的访问器 | 成功数据结构 |
| --- | --- | --- |
| `SeriesResult` | `.series` | 序列标签列表 `list[dict[str, str]]` |
| `LabelsResult` | `.labels` | 标签名列表 `list[str]` |
| `LabelValuesResult` | `.values` | 所请求标签的值列表 `list[str]` |

它们都提供 `.status: str`、`.is_success: bool`、`.is_error: bool`、`.data: Any`、`.error: str | None` 和 `.error_type: str | None`。发生错误或缺少数据时，有类型的列表访问器返回空列表。`from_dict()` 在缺少状态时默认为 `"error"`，不会发送请求。

<a id="ingestion-payloads"></a>

## 写入载荷

```python
from metricraft import MetricsInsertData

payload = MetricsInsertData(
    query='queue_depth{job="api"}',
    times=[1767225600, 1767225660],
    values=[4, 6],
)
payload.validate()
```

| 构造参数 | 类型 | 含义与约束 |
| --- | --- | --- |
| `query` | `str` | VictoriaMetrics 导入载荷的非空指标与标签文本，不是待求值表达式 |
| `times` | `Sequence[TimeValue]` | 非空时间戳序列，每个值对应一个时间戳 |
| `values` | `Sequence[int \| float \| str]` | 非空数值或后端数值字符串序列，长度与 `times` 相同 |

构造与 `.validate() -> None` 检查字段非空且长度一致，不解析指标文本，也不提供构建器的注入防护。结构无效时抛出 `ValueError`。dataclass 虽被冻结，传入的序列本身不因此变为不可变。使用 VictoriaMetrics 的 `DatabaseClient.insert()` 或 `insert_async()` 发送。

<a id="time-and-dialect-types"></a>

## 时间与方言类型

`TimeValue` 为 `int | float | str | datetime | None`。查询时间戳使用 Unix 秒，绝对值大于 `1e10` 时按毫秒处理。建议使用带时区 datetime 或 RFC3339 字符串。字符串转交后端，因此相对时间语法与后端有关。`None` 选择端点文档规定的默认值；写入和查询的时间戳转换是不同路径。

`QueryMode.PROMQL` 为 `"promql"`，`QueryMode.METRICSQL` 为 `"metricsql"`，用于构建时选择查询语言。`DBType.PROMETHEUS` 为 `"prometheus"`，`DBType.VM` 为 `"vm"`，用于标识 HTTP 后端配置。

`vm_only(method)` 与 `prom_only(method)` 添加方言元数据并返回原可调用对象。它们不验证用户函数，也不会启用任意新原生函数。SDK 表达式能力约束由 Rust 执行。

<a id="optional-configuration-registry"></a>

## 可选配置注册表

向 `DatabaseClient(config)` 显式传入配置通常最直接。共享注册表是可选功能，仅在当前进程内有效，并受锁保护。

| 函数 | 参数与行为 | 返回值 |
| --- | --- | --- |
| `register_config(config, instance="default", *, set_default=True)` | 验证 `config: Config`；`instance: str` 在该 DBType 内命名；`set_default: bool` 选择后端默认实例。同一后端名称重复时抛出 `RuntimeError`。 | `None` |
| `get_config(db_type=None, instance=None)` | `db_type: DBType \| None`，`instance: str \| None`。省略的值必须能无歧义地解析；配置缺失或歧义时抛出 `RuntimeError`。 | `Config` |
| `set_default_instance(db_type, instance)` | `db_type: DBType`；`instance: str` 必须已存在于该后端注册表，未知名称抛出 `RuntimeError`。 | `None` |

`Config` 是这些函数共用的配置协议与基类。实际端点请实例化 `PrometheusConfig`、`VMSingleConfig` 或 `VMClusterConfig`，方法见[配置参考](reference/configuration.md)。

<a id="errors"></a>

## 异常

构建器输入与原生验证使用 Python `TypeError` 和 `ValueError`。HTTP 异常从 `metricraft` 导出，继承 `MetriCraftError`：

| 异常 | 构造参数与常用字段 |
| --- | --- |
| `MCHTTPError` | `(status_code: int, message: str, response_data: dict \| None=None)`；提供 `.status_code`、`.message`、`.response_data`（省略时为空字典） |
| `TimeoutError` | 传输或查询超时，接受普通异常消息参数 |
| `ConnectionError` | 传输连接失败，接受普通异常消息参数 |

这里的 `TimeoutError` 和 `ConnectionError` 是 SDK 异常类，与 Python 内置的同名异常不同。
