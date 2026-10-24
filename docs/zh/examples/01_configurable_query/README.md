# 从结构化选项构建查询

本示例将应用选项映射为指标名、允许的窗口和标签过滤器，不需要服务器或客户端配置即可生成 PromQL 字符串。允许列表由应用提供，标签值始终作为字面量数据处理。

在应用的虚拟环境中安装已发布的软件包：

```sh
python -m pip install metricraft
```

将[完整示例](../../../examples/01_configurable_query/main.py)保存为 `main.py`，运行 `python main.py`。如果已有仓库，可以在根目录运行 `python docs/examples/01_configurable_query/main.py`。匹配平台的 wheel 包含原生库，不需要构建 Rust 或启动服务器。支持的平台与 uv 用法见[安装指南](../../getting-started.md)。

预期输出：

```promql
sum by (job) (rate(http_requests_total{job="api"}[5m]))
```

`build_query()` 接受一个字典，可来自 Web 应用已经验证过的请求。SDK 不要求 Web 框架、仪表盘、持久化方案或后端部署。请在映射边界加入应用自己的权限与成本控制，不要将用户提供的方法名或查询片段直接当作待执行操作。

下一步：[保存文本并稍后执行](../02_saved_query/README.md)。

<a id="transform-result-labels-in-metricsql"></a>

## 在 MetricsQL 中转换结果标签

选择器过滤用于选择输入序列。标签函数也可以在聚合后过滤或转换结果标签。例如，应用公开的服务名称与后端 job 标签不同：

```python
from metricraft import QueryBuilder as Q

rates = Q.from_metric("http_requests_total").rate("5m").sum().by("job")
services = rates.label_copy(("job", "service")).label_map(
    "service", ("api", "public-api"), ("worker", "background")
)
selected = services.label_match("service", "public-api")
text = selected.build("metricsql")  # Store this string using your own persistence.

# Both inputs remain reusable; rates still builds in PromQL mode.
assert rates.build("promql") == "sum by (job) (rate(http_requests_total[5m]))"
```

`label_copy`、`label_move`、`label_map` 接受有顺序的 `(source, destination)` 元组。copy/move 操作标签名，map 操作指定标签的值。copy/move 会跳过不存在的源标签，空映射也是有效后端操作。

正则参数仍然是正则，其语法与成本由后端和应用负责；字面量转义防止文本变成查询语法。这些扩展即使嵌入其他可移植操作，也会被检查为仅限 MetricsQL。参见[官方标签函数](https://docs.victoriametrics.com/metricsql/#label-manipulation-functions)。
