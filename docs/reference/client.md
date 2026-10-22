# Client & requests

The client accepts query strings independently of the native builder. It does not parse or sanitize stored query strings. Application authorization and persistence remain with your application.

```python
from metricraft import DatabaseClient, PrometheusConfig

with DatabaseClient(PrometheusConfig("http://localhost:9090")) as client:
    result = client.query("up")
    print(result.result)
```

Async methods are awaitable and support `async with DatabaseClient(...)`. Use [`MetricsQueryResult`](../models.md) to inspect returned data. Queries and metadata work with both backends; insertion is VictoriaMetrics-specific. Network examples require a running backend.
