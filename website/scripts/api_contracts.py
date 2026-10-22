"""Return contracts, runtime boundaries and selected executable examples."""
from api_purposes import PURPOSES

CLIENT = {
    "__init__": "Create a client from an explicit configuration or registered instance. Use a context manager to release transports.",
    "query": "Execute an instant query against the configured Prometheus or VictoriaMetrics backend.",
    "query_range": "Evaluate a query repeatedly from start to end at the requested step.",
    "series": "List matching series label sets through the backend metadata API.",
    "labels": "List label names, optionally restricted by selectors and time bounds.",
    "label_values": "List known values of one label, optionally restricted by selectors and time bounds.",
    "insert": "Send samples to VictoriaMetrics' ingestion endpoint. PrometheusConfig raises NotImplementedError.",
    "health": "Check the configured backend's health endpoint and return whether it is reachable and healthy.",
    "close": "Release owned transports once. Use aclose() when asynchronous cleanup is required.",
    "aclose": "Await asynchronous cleanup and release the synchronous transport.",
    "closed": "Whether the client has been closed. Closed clients reject further requests.",
    "client": "Access the active synchronous HTTP transport.",
    "async_client": "Access the active asynchronous HTTP transport.",
    "get_connection_info": "Return a shallow copy of active backend connection settings.",
    "select_base_url": "Return the query base URL, including the configured cluster tenant path where applicable.",
    "insert_base_url": "Return the VictoriaMetrics insertion base URL; unsupported for Prometheus.",
    "storage_base_url": "Return the configured storage base URL when applicable.",
}
CONFIG = {
    "__init__": "Create connection settings for this backend. Configuration objects are mutable; immutable expression guarantees do not apply to configuration.",
    "db_type": "Return this backend's DBType discriminator.",
    "http_options": "Return the stored HttpClientOptions object.",
    "http_options_dict": "Export HTTP options as a dictionary for transport setup.",
    "set_http_options": "Replace HTTP options on this configuration object.",
    "update_http_options": "Merge HTTP options into this configuration, retaining unspecified settings.",
    "get_connection_info": "Return resolved backend connection settings and HTTP options.",
    "get_insert_url_base": "Return the insertion base URL. PrometheusConfig raises NotImplementedError because it has no VictoriaMetrics import endpoint.",
    "get_query_url_base": "Return the query base URL with any deployment/tenant prefix; the client adds the endpoint.",
    "validate": "Check required endpoints and settings; raise ValueError for invalid configuration.",
    "ensure": "Normalize None, a mapping or existing options into HttpClientOptions.",
    "from_mapping": "Create HTTP options from a mapping, normalize aliases and retain unknown transport keys in extras.",
    "merge": "Return new HTTP options with overrides. Headers and extras merge by key; non-None fields replace existing values.",
    "to_dict": "Export configured HTTP settings and extras as a dictionary.",
}
RETURNS = {
    "build": "str — validated query text, ready for storage or a client request.",
    "validate": "str — empty on success, otherwise a native validation message. Invalid Python arguments can still raise exceptions.",
    "analyze": "dict — graph counts and heuristic advice, not a server execution plan.",
    "to_debug_json": "str — JSON describing unique native nodes and their relationships.",
    "debug": "str — the same JSON graph as to_debug_json().",
    "debug_positions": "str — JSON with query text and UTF-8 byte spans, not Python character offsets.",
    "visualize_positions": "str — validated source/span JSON; no image or browser window is created.",
    "__init__": "QueryBuilder — a stateless factory; start a from_* expression before building.",
}
NOTES = {
    "by": "Apply exactly one of by()/without(), once, to an ungrouped aggregation. To create both variants, derive them independently from the same aggregate. Omitting grouping is legal in both dialects.",
    "without": "Apply exactly one of by()/without(), once, to an ungrouped aggregation. Omitting grouping is legal in both dialects.",
    "range": "With no arguments this defaults to '5m'. For a computed PromQL expression use subquery() instead.",
    "subquery": "PromQL requires an explicit positive window; MetricsQL can omit it. Duration-expression forms need the relevant feature opt-in.",
    "rollup": "Prefer rollup(window='5m', result='avg'). The compatibility form rollup('avg', '5m') is accepted. window/duration and result/func are mutually exclusive aliases.",
    "function": "Strings are literals. Use Q.from_metric('up') for an expression; function('rate', 'up[5m]') does not parse the argument as a query.",
    "from_scalar": "Native scalars use f64: Python integers outside exact IEEE-754 integer precision may round.",
    "histogram_quantile": "For classic Prometheus buckets retain the le label through aggregation. Native histogram support and interpolation belong to the backend.",
    "anchored": "Requires features=('promql-extended-range-selectors',) and matching server support. Eligible rollups include rate, increase, delta, changes and resets.",
    "smoothed": "Requires features=('promql-extended-range-selectors',) and matching server support. Eligible rollups include rate, increase and delta.",
}
for name in ("fill", "fill_left", "fill_right"):
    NOTES[name] = "Requires features=('promql-binop-fill-modifiers',) and matching server support."
EXAMPLES = {
    "from_metric": 'Q.from_metric("http_requests_total").where_eq("job", "api").build(mode="promql")',
    "from_labels": 'Q.from_labels(job="api").build(mode="promql")',
    "from_scalar": 'Q.from_scalar(42).build(mode="promql")',
    "from_duration": 'Q.from_duration("5m").build(mode="metricsql")',
    "from_numeric_literal": 'Q.from_numeric_literal("2K").build(mode="promql")',
    "function": 'Q.function("rate", Q.from_metric("requests_total").range("5m")).build(mode="promql")',
    "build": 'Q.from_metric("up").build(mode="promql", max_output_bytes=4096)',
    "by": 'Q.from_metric("requests_total").rate("5m").sum().by("job").build(mode="promql")',
    "without": 'Q.from_metric("up").sum().without("instance").build(mode="promql")',
    "rate": 'Q.from_metric("requests_total").rate("5m").build(mode="promql")',
    "count_gt_over_time": 'Q.from_metric("queue_depth").count_gt_over_time(20, window="5m").build(mode="metricsql")',
    "count_values_over_time": 'Q.from_metric("queue_depth").count_values_over_time("observed", window="5m").build(mode="metricsql")',
    "histogram_quantile": 'Q.from_metric("request_duration_seconds_bucket").rate("5m").sum().by("le").histogram_quantile(0.95).build(mode="promql")',
    "on": '(Q.from_metric("errors_total") / Q.from_metric("requests_total")).on("job").build(mode="promql")',
    "bool": 'Q.from_metric("up").eq(1).bool().build(mode="promql")',
    "label_replace": 'Q.from_metric("up").label_replace("host", "$1", "instance", "([^:]+):.*").build(mode="promql")',
    "subquery": 'Q.from_metric("requests_total").rate("5m").subquery("1h", "1m").max_over_time().build(mode="promql")',
    "at": 'Q.from_metric("up").at("2026-01-01T00:00:00Z").build(mode="promql")',
    "with_": 'Q.reference("base").sum().with_(base=Q.from_metric("up")).build(mode="metricsql")',
    "range_avg": 'Q.from_metric("queue_depth").range_avg().build(mode="metricsql")',
    "analyze": 'Q.from_metric("up").sum().analyze()',
}


def contract(cls, entry):
    name = entry["name"]
    if cls == "QueryBuilder":
        return (PURPOSES[name], RETURNS.get(name, "QueryBuilder — a new immutable expression sharing unchanged native subtrees. The receiver is unchanged; no data is queried."), NOTES.get(name, ""), EXAMPLES.get(name, ""))
    if cls == "DatabaseClient":
        purpose = CLIENT[name.removesuffix("_async")]
        if name.endswith("_async"):
            purpose += " Await this asynchronous variant."
        returns = entry.get("return_type") or {"client": "HTTP transport", "async_client": "Async HTTP transport"}[name]
        return purpose, returns, "Request methods can raise MCHTTPError, TimeoutError, ConnectionError or parameter-validation errors. Use with/async with for cleanup.", ""
    purpose = CONFIG[name]
    if cls == "HttpClientOptions" and name == "__init__":
        purpose = "Create frozen transport options. Header/extras dictionaries are copied; freezing does not recursively freeze their contents."
    return purpose, entry.get("return_type") or (cls if name == "__init__" else "HttpClientOptions"), "Configuration and transport validation are separate from query validation.", ""
