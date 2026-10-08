# Build from structured selections

This example maps an application's selections to metric names, allowed windows
and label filters. It produces a PromQL string without a server or client config.
The application supplies its own allowlists; label values remain literal data.

After the [development setup](../../../CONTRIBUTING.md), run from the repository root:

```sh
python docs/examples/01_configurable_query/main.py
```

If your native build is outside `target/`, set `CARGO_TARGET_DIR` or
`METRICRAFT_NATIVE_LIB` before running. Alternatively `python scripts/dev.py smoke`
builds the library and runs both examples.

Expected output:

```promql
sum by (job) (rate(http_requests_total{job="api"}[5m]))
```

`build_query()` accepts a dictionary that a web application's validated request
could supply. No web framework, dashboard, persistence or backend deployment is
required by the SDK. Add application-specific access and cost controls at that
mapping boundary. Do not treat user-supplied method names or query fragments as
operations to execute.

Next: [save the text and execute it later](../02_saved_query/README.md).

## Transform result labels in MetricsQL

Filters on a selector choose input series. Label functions can also filter or
transform labels after an aggregation. For example, an application may offer a
service selection whose public names differ from the backend's job labels:

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

`label_copy`, `label_move` and `label_map` take ordered `(source, destination)`
tuples. Copy/move refer to label names; map refers to values of the named label.
Copy/move skip missing sources. Empty mappings are valid backend operations.
Regex arguments remain regexes; their syntax and cost are backend/application
concerns. Literal escaping prevents their text from becoming query syntax.
All these extensions are checked as MetricsQL-only even when nested inside
otherwise portable operations. See the [official label functions](https://docs.victoriametrics.com/metricsql/#label-manipulation-functions).
