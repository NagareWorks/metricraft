# Connection configuration

Use one configuration per backend. PrometheusConfig uses standard API paths; VMSingleConfig and VMClusterConfig supply the VictoriaMetrics deployment paths. The client resolves endpoint suffixes.

```python
from metricraft import PrometheusConfig, HttpClientOptions

config = PrometheusConfig(
    "http://localhost:9090",
    default_step="30s",
    http_options=HttpClientOptions(timeout=(3, 20)),
)
config.validate()
```

Put timeouts inside `http_options`; top-level timeout kwargs are rejected. Configuration objects can be updated. HttpClientOptions is a frozen container with copied dictionaries, not a recursively immutable object. For optional registry helpers, see [models and shared types](../models.md).
