# HTTP 客户端与请求

客户端可独立于原生构建器接收查询字符串，不解析或清理已保存的查询文本。应用授权与持久化仍由应用负责。

```python
from metricraft import DatabaseClient, PrometheusConfig

with DatabaseClient(PrometheusConfig("http://localhost:9090")) as client:
    result = client.query("up")
    print(result.result)
```

异步方法可以等待，支持 `async with DatabaseClient(...)`。使用 [`MetricsQueryResult`](../models.md) 检查返回数据。查询和元数据支持两种后端，写入仅限 VictoriaMetrics。网络示例需要运行中的后端。
