"""Parameter contracts shared by related Python methods, with explicit exceptions."""

NUMBER = ("int | float | QueryBuilder", "Numeric scalar or scalar expression; Python bool is rejected. Computed values are evaluated by the backend.")
LABEL = ("str", "Nonempty label name without control characters. The builder quotes names when required by the dialect.")
WINDOW = ("str | QueryBuilder | None", "Positive lookbehind duration, e.g. '5m' or '1h30m'. None preserves an existing range or uses MetricsQL implicit rollup; a bare selector without a window cannot build as PromQL. Duration expressions need the relevant dialect/feature support.")
PARAMETERS = {
    "label": LABEL, "destination": LABEL, "source": LABEL, "first": LABEL, "second": LABEL,
    "labels": ("str, ...", "Label names, passed separately. Grouping and matching lists must not contain duplicates. An empty grouping list is allowed; function-specific arity is checked by Rust."),
    "sources": ("str, ...", "Source label names to concatenate, in the supplied order."),
    "name": ("str", "Nonempty metric/function/binding name. It is validated by the relevant constructor, not inserted as raw query syntax."),
    "window": WINDOW,
    "duration": ("str | QueryBuilder | None", "Lookbehind duration, e.g. '5m'. Where window is also accepted, pass one name only. None preserves the current range or requests MetricsQL implicit rollup."),
    "range_duration": ("str | QueryBuilder | None", "Alias of window for subquery(). Do not supply both names."),
    "resolution": ("str | QueryBuilder | None", "Alias of step for subquery(). Do not supply both names."),
    "step": ("str | QueryBuilder | None", "Positive subquery evaluation step, e.g. '30s'. None uses the backend's default subquery resolution."),
    "q": ("int | float | QueryBuilder", "Requested quantile, normally in [0, 1]. Out-of-range values follow backend quantile semantics; the builder does not universally reject them."),
    "quantile": ("int | float | QueryBuilder | None", "Alias of q. Supply exactly one of q or quantile; normally use [0, 1]."),
    "quantiles": ("int | float | QueryBuilder, ...", "One or more requested quantiles, normally each in [0, 1]. PromQL histogram_quantiles accepts at most 10 quantiles; MetricsQL supports its own variadic form."),
    "k": ("int | float | QueryBuilder", "Number of series to select; use a positive integer for a nonempty top/bottom selection. Scalar expressions are accepted; backend conversion and edge semantics apply."),
    "ratio": ("int | float | QueryBuilder", "Sampling ratio in [-1, 1]; a negative value requests the complement. Values outside that interval use backend handling."),
    "other": ("int | float | QueryBuilder", "Right operand. Set operators and vector matching require vector expressions; arithmetic/comparisons also accept numbers. Python bool is rejected."),
    "others": ("QueryBuilder, ...", "Additional input expressions. Multiple aggregation inputs and union-style transforms are MetricsQL-only; ordinary PromQL aggregation takes just the receiver."),
    "minimum": ("int | float | QueryBuilder", "Inclusive lower sample-value bound. Use a value no greater than maximum; between() requires literal numbers."),
    "maximum": ("int | float | QueryBuilder", "Inclusive upper sample-value bound. Use a value no less than minimum; between() requires literal numbers."),
    "threshold": ("int | float | QueryBuilder", "Numeric histogram observation cutoff; vector thresholds use matching rules."),
    "lower": ("int | float | QueryBuilder", "Lower histogram observation boundary; use a value below upper, optionally negative infinity."),
    "upper": ("int | float | QueryBuilder", "Upper histogram observation boundary; use a value above lower, optionally positive infinity."),
    "bound": ("int | float | QueryBuilder", "Histogram observation boundary for the cumulative share."),
    "bounds_label": ("str | None", "Optional output label for lower/upper estimation bounds. Supplying it selects a MetricsQL-only argument form."),
    "smoothing_factor": ("int | float | QueryBuilder", "Level smoothing factor, strictly between 0 and 1. Higher values give recent samples more weight; literal factors are checked by Rust."),
    "trend_factor": ("int | float | QueryBuilder", "Trend smoothing factor, strictly between 0 and 1. Literal factors are checked by Rust."),
    "seconds": ("int | float | QueryBuilder | None", "Prediction horizon in seconds. Positive values project forward; pass either seconds or prediction_seconds, and provide one of them."),
    "prediction_seconds": ("int | float | QueryBuilder | None", "Alias of seconds; do not supply both."),
    "nearest": ("int | float | QueryBuilder | None", "Rounding multiple; None uses 1. Use a positive nonzero multiple. Do not also pass to_nearest."),
    "to_nearest": ("int | float | QueryBuilder | None", "Alias of nearest; do not supply both."),
    "direction": ("str", "Either 'asc' or 'desc'."),
    "regex": ("str", "Backend RE2 pattern. Capture references in replacements use $1 or named captures. Query quoting does not make the regex literal."),
    "replacement": ("str", "Replacement text with optional backend capture references such as '$1'. Encoded as a string literal."),
    "separator": ("str", "Literal separator between source label values; may be empty."),
    "pairs": ("tuple[str, str], ...", "Pass each mapping as a two-string tuple, in order. label_copy/move use source and destination names; label_map uses source and destination values."),
    "groups": ("int, ...", "Nonnegative, zero-based dot-separated metric-name component indexes. Use whole numbers; the SDK rejects bool but does not enforce integer/index bounds for this function."),
    "prefix": ("str", "Literal prefix for copied labels; empty means no prefix."),
    "values": ("int | float | str | QueryBuilder, ...", "Nonempty uniformly scalar or uniformly string tuple. Comparison tuples must have the appropriate numeric type."),
    "result": ("str | None", "Select 'min', 'max' or 'avg'; None emits all three result series."),
    "func": ("str | None", "Compatibility alias of result ('min', 'max', 'avg'); do not pass both."),
    "functions": ("str, ...", "One or more rollup names accepted by aggr_over_time, such as 'min_over_time' and 'max_over_time'. Each name is checked against the Rust allowlist."),
    "tolerance": ("int | float | QueryBuilder", "Multiplier applied to median absolute deviation; use a nonnegative value. Evaluated by the backend."),
    "seed": ("int | float | QueryBuilder | None", "Optional scalar random seed. None uses backend default seeding; the builder does not generate random samples locally."),
    "timezone": ("str", "IANA timezone name such as 'Europe/Paris' or 'UTC'. Existence is checked by the backend timezone database."),
    "limit": ("int | float | QueryBuilder", "Maximum number of output series; use a nonnegative integer. Backend handles computed values."),
    "offset": ("int | float | QueryBuilder", "Number of output series to skip; use a nonnegative integer."),
    "count": ("int | float", "Integer-valued aggregation output limit in [0, 4294967295] (unsigned 32-bit); nonfinite/fractional values and bool are rejected."),
    "timestamp": ("int | float | str | datetime | QueryBuilder", "Finite Unix seconds, timezone-aware datetime/ISO string, 'start'/'end' (also 'start()'/'end()'), or a supported typed scalar expression. Naive datetimes and bool are rejected."),
    "data_labels": ("QueryBuilder | None", "Optional unnamed label selector from Q.from_labels(); a named metric selector is rejected for info's second argument."),
    "kind": ("str", "Declared reference result kind: 'instant', 'range', 'scalar', or 'string'. The resolved binding must match."),
    "parameters": ("str, ...", "Unique valid MetricsQL identifiers for template parameters. They are scoped to the template body."),
    "body": ("QueryBuilder | int | float | str", "Template expression body; strings become literal values, not source code."),
    "bindings": ("QueryBuilder | int | float | str, by keyword", "Binding-name/value pairs in insertion order. Identifiers must be valid, scope must resolve, and recursive definitions are rejected."),
    "args": ("QueryBuilder | int | float | str, ...", "Typed function arguments in upstream order. Strings become literals; numeric/vector/range types and arity are checked by Rust."),
    "mode": ("QueryMode | str", "'promql' or 'metricsql' (default). Checks the entire expression, including dialect-specific argument forms."),
    "standard": ("str | None", "'promql' or 'metricsql', case-insensitive. None selects MetricsQL."),
    "strict": ("bool", "Must be True. strict=False is intentionally unsupported."),
    "max_output_bytes": ("int | None", "Positive integer byte budget; None uses the native 1 MiB default. bool and zero are rejected. Applies to UTF-8 output, not character count."),
    "max_expanded_nodes": ("int | None", "Positive integer expression-occurrence budget; None uses 100,000. Repeated references count each time rendered, even when the tree shares storage."),
    "max_items": ("int | None", "Positive diagnostic work budget; None uses the native default. Graph inspection counts nodes/edges/matcher links; position output counts rendered occurrences."),
    "experimental_functions": ("bool", "Opt into Prometheus experimental functions. The backend must also enable the corresponding feature; this flag does not configure the server."),
    "features": ("Iterable[str]", "Explicit feature names: 'promql-experimental-functions', 'promql-duration-expr', 'promql-extended-range-selectors', 'promql-binop-fill-modifiers'. Each requires matching server support. Pass a collection, not one string."),
    "build_options": ("keyword arguments", "Keyword options accepted by build(), excluding mode (use standard here). Limits and feature checks still apply."),
    "options": ("keyword arguments", "Keyword options accepted by debug_positions(), including mode, budgets and feature flags."),
    "source_code": ("str", "Exact output of this expression's build() with matching options; a different string raises ValueError."),
    "op": ("str", "One of sum, avg, min, max, count, stddev, stdvar, group, any, median, mode, mad, distinct, geomean, histogram, outliers_iqr, share, sum2, zscore. Use dedicated methods for parameterized aggregations."),
}

VALUE_OVERRIDES = {
    "from_string": ("str", "Literal string contents. Quotes, backslashes and control characters are escaped; arbitrary query text is never parsed."),
    "from_duration": ("str", "Duration literal such as '5m'. MetricsQL supports fractional and interval-relative units (for example '1.5i'); dialect checks apply at build."),
    "from_numeric_literal": ("str", "Numeric notation such as '1.25', '2K' or '4Mi'. Supported suffixes are K/M/G/T and Ki/Mi/Gi/Ti (case-sensitive); underscores are removed. Values normalize to ordinary scalars and can build in either dialect. Extra query tokens and suffix overflow are rejected."),
    "from_scalar": ("int | float", "Numeric literal, including IEEE NaN/infinity. bool is rejected; values use the native floating-point representation."),
    "count_values_over_time": ("str", "Nonempty output label name that stores the counted sample value; this parameter is a label, not a numeric threshold."),
    "duration_over_time": ("int | float | QueryBuilder", "Maximum allowed gap between samples, in seconds; use a positive scalar."),
    "hoeffding_bound_lower": ("int | float | QueryBuilder", "Confidence probability in [0, 1]. Backend handles out-of-range/computed inputs."),
    "hoeffding_bound_upper": ("int | float | QueryBuilder", "Confidence probability in [0, 1]. Backend handles out-of-range/computed inputs."),
    "range_quantile": PARAMETERS["q"],
    "range_trim_spikes": ("int | float | QueryBuilder", "Fraction of extreme samples to trim, normally in [0, 1]. Evaluated by the backend."),
    "range_trim_outliers": PARAMETERS["tolerance"],
    "range_trim_zscore": ("int | float | QueryBuilder", "Nonnegative absolute z-score threshold, such as 3."),
    "buckets_limit": ("int | float | QueryBuilder", "Maximum histogram bucket count; use a positive integer."),
    "ru": ("int | float | QueryBuilder", "Positive maximum resource capacity used as the utilization denominator."),
}

CLIENT_PARAMS = {
    "config": ("Config | None", "PrometheusConfig, VMSingleConfig or VMClusterConfig. Supply config or instance, not both; with neither, resolve the registered default."),
    "instance": ("str | None", "Name in the optional configuration registry. Unknown/unset names fail before requests."),
    "query": ("str | QueryBuilder", "Saved query text or a builder. Builders use the configured backend's dialect; strings are passed through without parsing or injection protection."),
    "time": ("int | float | str | datetime | None", "Evaluation timestamp. Numbers are Unix seconds (milliseconds when magnitude exceeds 1e10); aware datetimes and backend timestamp strings are accepted. None uses server now."),
    "start": ("int | float | str | datetime | None", "Inclusive range start or metadata lower bound. query_range defaults to one hour before end; metadata calls omit the bound when None."),
    "end": ("int | float | str | datetime | None", "Inclusive range end or metadata upper bound. query_range defaults to now; metadata calls omit the bound when None."),
    "step": ("str | None", "Positive evaluation interval such as '30s' for range queries (default: config.default_step). On instant queries this is a VictoriaMetrics-only lookback option."),
    "timeout": ("str | None", "Backend query execution timeout such as '30s'; None omits it. Configure transport socket timeouts separately with HttpClientOptions."),
    "limit": ("int | None", "Nonnegative series/metadata result limit; 0 disables the limit. Query series limits are Prometheus-specific; VictoriaMetrics may ignore them."),
    "extra_label": ("str | dict[str, str] | None", "VictoriaMetrics-only extra equality filters, e.g. {'tenant': 'demo'} or 'tenant=demo'. This is not a substitute for server authorization."),
    "extra_filters": ("str | list[str] | None", "VictoriaMetrics-only additional selector filters, e.g. '{env=\"prod\"}'. Query text in this client option is not sanitized by the builder."),
    "round_digits": ("int | None", "VictoriaMetrics response rounding precision, forwarded to the backend; no SDK numeric bound is enforced."),
    "nocache": ("bool | None", "VictoriaMetrics-only flag to bypass query cache when True."),
    "trace": ("bool | None", "VictoriaMetrics-only flag requesting execution trace details."),
    "account_id": ("int | None", "Nonnegative integer VictoriaMetrics cluster tenant ID. A per-request override is rejected for non-cluster configurations."),
    "custom_params": ("dict[str, Any] | None", "Additional request parameters merged after standard parameters, so duplicate keys can override them. Values and authorization remain caller-owned; no injection validation is performed."),
    "data": ("MetricsInsertData | Iterable[MetricsInsertData]", "Validated ingestion payload(s). Nonempty aligned timestamps/values are required. Only VictoriaMetrics ingestion is supported."),
    "match": ("str | QueryBuilder | Sequence[str | QueryBuilder] | None", "One or more series selectors, including lists and tuples; builders render using the backend dialect. series() requires this argument; labels/label_values may omit it."),
    "label_name": ("str", "Label whose known values should be returned, e.g. 'job'."),
}

CONFIG_PARAMS = {
    "url": ("str", "Nonempty backend base URL, e.g. 'http://localhost:9090'. Do not append /api/v1/query; endpoint paths are added by the client."),
    "vminsert_url": ("str", "VictoriaMetrics vminsert base URL, e.g. 'http://localhost:8480'; tenant insertion paths are added automatically."),
    "vmselect_url": ("str", "VictoriaMetrics vmselect base URL, e.g. 'http://localhost:8481'; tenant query paths are added automatically."),
    "vmstorage_url": ("str", "VictoriaMetrics vmstorage base URL, e.g. 'http://localhost:8482'."),
    "account_id": ("int", "Nonnegative integer cluster tenant ID (default 0)."),
    "default_step": ("str", "Default range-query evaluation interval, e.g. '1m'. Use a positive backend duration; syntax is ultimately checked by the backend."),
    "http_options": ("HttpClientOptions | Mapping | None", "Transport settings; None uses backend configuration defaults (30-second transport timeout)."),
    "options": ("HttpClientOptions | Mapping | None", "Replacement HTTP settings; mutates this configuration object, not query expressions."),
    "overrides": ("HttpClientOptions | Mapping | None", "Settings to merge with existing HTTP options. Headers and extras merge by key; other supplied fields override."),
    "kwargs": ("keyword arguments", "Additional connection settings. A top-level timeout is rejected: put timeout inside http_options."),
    "timeout": ("number | tuple[number, number] | None", "Positive connect/read timeouts in seconds; a scalar applies to both. None leaves timeout unspecified for the owning configuration/transport."),
    "default_headers": ("Mapping[str, str]", "Default HTTP request headers; names and values are normalized into a copied dictionary."),
    "prepare_request": ("Callable | None", "Hook for preparing the transport request before sending; must follow the selected transport's request contract."),
    "opener": ("Callable | None", "Optional urllib-compatible synchronous request opener."),
    "client": ("object | None", "Injected synchronous HTTP transport implementing the client's expected request/close protocol."),
    "async_client": ("object | None", "Injected asynchronous HTTP transport implementing async request/cleanup."),
    "client_factory": ("Callable | None", "Factory constructing a synchronous transport from the configured HTTP keyword options."),
    "async_client_factory": ("Callable | None", "Factory constructing an asynchronous transport from the configured HTTP keyword options."),
    "max_workers": ("int | None", "Positive worker count for the async fallback executor; None uses the executor default."),
    "executor": ("Executor | None", "Optional executor used by the async fallback; externally supplied executors remain caller-owned."),
    "extras": ("Mapping[str, Any]", "Additional transport-specific options copied into the configuration; their meaning belongs to the selected transport."),
    "data": ("Mapping[str, Any]", "HTTP option mapping. The headers key aliases default_headers; unrecognized keys are retained in extras."),
    "value": ("HttpClientOptions | Mapping[str, Any] | None", "Return an existing options object, convert a mapping, or use an empty options object for None."),
}


def parameter(cls, method, name):
    if cls == "DatabaseClient":
        return CLIENT_PARAMS[name]
    if cls != "QueryBuilder":
        return CONFIG_PARAMS[name]
    if method == "__init__":
        return ("not accepted", "No positional or keyword configuration is accepted. Use Q.from_metric(...) and build(mode=...).")
    if name == "value":
        if method.startswith(("count_eq_", "count_ne_", "count_gt_", "count_le_", "sum_eq_", "sum_gt_", "sum_le_", "share_eq_", "share_gt_", "share_le_")):
            return ("int | float | QueryBuilder", "Threshold compared with each raw sample in the window. Any numeric scalar is accepted; bool is rejected. Samples satisfying the named comparison contribute to the result.")
        if method.startswith("where") or method == "filter":
            return ("str", "Label value or RE2 pattern for regex matchers. Encoded as a quoted query string; empty strings are allowed.")
        return VALUE_OVERRIDES.get(method, NUMBER)
    if name == "labels" and method in ("label_set", "from_labels"):
        return ("str, by keyword", "Label-name/string-value pairs, e.g. job='api'. Use **mapping for names that are not Python identifiers.")
    if name == "other" and method.startswith(("topk_", "bottomk_")):
        return ("str | None", "Optional 'label=value' assignment identifying the combined remainder series. None omits it.")
    if name == "operator":
        return ("str", "Exactly '=', '!=', '=~' or '!~'. Raw operators or query fragments are rejected.")
    if name == "q" and method == "quantile_over_time":
        return ("int | float | QueryBuilder | None", "Quantile, normally in [0, 1]. Supply either q or quantile, never both; None is valid only when the alias provides the value.")
    if name == "smoothing_factor" and method == "smooth_exponential":
        return ("int | float | QueryBuilder", "Smoothing factor in the inclusive interval [0, 1]. Literal factors outside this range are rejected by Rust.")
    if name == "result" and method == "rollup_candlestick":
        return ("str | None", "Select 'open', 'high', 'low' or 'close'; None returns all four.")
    if name == "duration" and method == "offset":
        return ("str | QueryBuilder", "Signed duration such as '1h' or '-5m', including zero. Typed duration expressions require dialect/feature support.")
    return PARAMETERS[name]
