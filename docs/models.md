# Models and shared types

## Query responses

`MetricsQueryResult.from_dict(response_data: dict[str, Any]) -> MetricsQueryResult`
converts a decoded backend response. Pass the complete response with `status`
and `data`; optional error, warning and VictoriaMetrics fields are preserved.
`result.to_dict() -> dict[str, Any]` converts it back to the response shape.
Prefer this factory over constructing the dataclass's internal underscored fields.

| Property | Type | Meaning |
| --- | --- | --- |
| `status` | `str` | Backend status, normally `success` or `error` |
| `is_success`, `is_error` | `bool` | Whether status equals the corresponding value |
| `data` | `dict[str, Any] \| None` | Decoded `resultType` and `result` object |
| `result_type` | `str \| None` | `vector`, `matrix`, `scalar` or `string`, if supplied |
| `result` | `list \| None` | Backend samples; shape follows `result_type` |
| `error`, `error_type` | `str \| None` | Backend error text and classification |
| `warnings` | `list[str] \| None` | Nonfatal backend warnings |
| `is_partial` | `bool` | VictoriaMetrics partial-response flag; defaults to false |
| `stats` | `dict[str, Any] \| None` | VictoriaMetrics execution statistics |
| `trace` | `dict[str, Any] \| None` | VictoriaMetrics trace tree when requested |
| `execution_time_ms` | `float \| None` | Convenience access to `stats.executionTimeMsec` |
| `series_fetched` | `int \| str \| None` | Convenience access to `stats.seriesFetched` |

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

An instant vector uses `[{"metric": labels, "value": [timestamp, "value"]}]`.
A matrix uses `values` containing a list of timestamp/value pairs. Scalars and
strings use `[timestamp, "value"]`. Values remain backend strings, which can
represent nonfinite values. A frozen result wrapper does not recursively freeze
the dictionaries and lists it contains.

## Metadata responses

Import `SeriesResult`, `LabelsResult` and `LabelValuesResult` from
`metricraft.models`. Each supports
`from_dict(response: dict)`, `to_dict() -> dict`, and construction with
`(status: str, data=None, error: str | None=None, error_type: str | None=None)`.
Use `status="success"` with the corresponding list shape below, or `"error"`
with error details. The wrapper does not validate arbitrary backend payloads
against a schema.

| Class | Typed accessor | Successful data shape |
| --- | --- | --- |
| `SeriesResult` | `.series` | `list[dict[str, str]]` of series labels |
| `LabelsResult` | `.labels` | `list[str]` of label names |
| `LabelValuesResult` | `.values` | `list[str]` of values for the requested label |

All expose `.status: str`, `.is_success: bool`, `.is_error: bool`, `.data: Any`,
`.error: str | None`, and `.error_type: str | None`. Typed list accessors return
an empty list for errors or missing data. `from_dict()` defaults a missing status
to `"error"`; it does not make a request.

## Ingestion payloads

```python
from metricraft import MetricsInsertData

payload = MetricsInsertData(
    query='queue_depth{job="api"}',
    times=[1767225600, 1767225660],
    values=[4, 6],
)
payload.validate()
```

| Constructor parameter | Type | Meaning and constraints |
| --- | --- | --- |
| `query` | `str` | Nonempty metric/label text for the VictoriaMetrics import payload; not an expression to evaluate |
| `times` | `list[TimeValue]` | Nonempty timestamps, one for each value |
| `values` | `list[int \| float \| str]` | Nonempty numeric values or backend numeric strings, same length as `times` |

Construction and `.validate() -> None` check nonempty fields and equal lengths;
they do not parse metric text or provide builder injection protection. Invalid
structure raises `ValueError`. The frozen dataclass still contains ordinary lists.
Send it using `DatabaseClient.insert()` or `insert_async()` with VictoriaMetrics.

## Time and dialect types

`TimeValue` is `int | float | str | datetime | None`. Query timestamps use Unix
seconds; numeric magnitudes above `1e10` are treated as milliseconds. Prefer
timezone-aware datetimes or RFC3339 strings. Strings are forwarded to the
backend, so relative-time syntax is backend-specific. `None` selects the endpoint's
documented default. Ingestion and query timestamp conversion are distinct paths.

`QueryMode.PROMQL` is `"promql"`; `QueryMode.METRICSQL` is `"metricsql"`.
These select the query language at build time. `DBType.PROMETHEUS` is
`"prometheus"`; `DBType.VM` is `"vm"`. These identify HTTP backend configurations.

`vm_only(method)` and `prom_only(method)` attach dialect metadata and return the
same callable. They do not validate user functions or enable arbitrary new
native functions. Enforcement of SDK expression capabilities belongs to Rust.

## Optional configuration registry

Explicit configuration passed to `DatabaseClient(config)` is usually easiest.
The shared registry is optional, process-local and protected by a lock.

| Function | Parameters and behavior | Returns |
| --- | --- | --- |
| `register_config(config, instance="default", *, set_default=True)` | `config: Config` is validated; `instance: str` names it within its DBType; `set_default: bool` selects it as that backend's default. Duplicate names for that backend raise `RuntimeError`. | `None` |
| `get_config(db_type=None, instance=None)` | `db_type: DBType \| None`; `instance: str \| None`. Omitted values must resolve unambiguously; missing or ambiguous configurations raise `RuntimeError`. | `Config` |
| `set_default_instance(db_type, instance)` | `db_type: DBType`; `instance: str` must already exist in that backend's registry. Unknown names raise `RuntimeError`. | `None` |

`Config` is the common configuration protocol/base used by these functions;
instantiate `PrometheusConfig`, `VMSingleConfig` or `VMClusterConfig` for actual
endpoints. Their methods are on the [configuration page](reference/configuration.md).

## Errors

Builder input and native validation use Python `TypeError` and `ValueError`.
HTTP exceptions are exported from `metricraft` and inherit `MetriCraftError`:

| Exception | Constructor / useful fields |
| --- | --- |
| `MCHTTPError` | `(status_code: int, message: str, response_data: dict \| None=None)`; exposes `.status_code`, `.message`, `.response_data` (empty dict when omitted) |
| `TimeoutError` | Transport/query timeout; accepts ordinary exception message arguments |
| `ConnectionError` | Transport connection failure; accepts ordinary exception message arguments |

These `TimeoutError` and `ConnectionError` names are SDK exception classes,
distinct from Python's built-in exceptions with the same names.
