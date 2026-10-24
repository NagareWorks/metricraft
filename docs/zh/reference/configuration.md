# 连接配置

每个后端使用一份配置。PrometheusConfig 使用标准 API 路径；VMSingleConfig 与 VMClusterConfig 提供 VictoriaMetrics 对应部署的路径。客户端负责拼接端点后缀。

```python
from metricraft import PrometheusConfig, HttpClientOptions

config = PrometheusConfig(
    "http://localhost:9090",
    default_step="30s",
    http_options=HttpClientOptions(timeout=(3, 20)),
)
config.validate()
```

超时应放在 `http_options` 中，顶层 timeout 关键字参数会被拒绝。配置对象可以更新。HttpClientOptions 是冻结容器，其字典会复制，但并非递归不可变。可选注册辅助函数见[模型与公共类型](../models.md)。

HTTP 传输插槽使用公开的同步、异步 Protocol 和工厂契约。适配器签名、工厂参数及资源归属见[替换 HTTP 传输](../client-guide.md#replace-the-http-transport)。
