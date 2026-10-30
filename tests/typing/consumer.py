"""Static consumer contract, checked against an installed wheel outside the repo."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Tuple, Union, assert_type

from metricraft import (
    Config, DatabaseClient, DBType, HttpClientOptions, MetricsInsertData,
    MetricsQueryResult, PrometheusConfig, QueryBuilder as Q, QueryMode,
    VMClusterConfig, VMSingleConfig, get_config, prom_only, register_config,
    set_default_instance, vm_only, SyncHTTPTransport, AsyncHTTPTransport,
    SyncHTTPTransportFactory, AsyncHTTPTransportFactory,
)
from metricraft.client import SyncHTTPClient, AsyncHTTPClient
from metricraft.transports import HTTPBody, HTTPHeaders, HTTPParams, HTTPResponse, HTTPTimeout
from metricraft.models import LabelsResult, LabelValuesResult, SeriesResult
from metricraft import ParseError
from metricraft.builder.parsing import ParseErrorKind
from metricraft.builder.editing import ValueType


base = Q.from_metric("http_requests_total").where_eq("job", "api")
assert_type(Q.parse("up", "promql", max_depth=32), Q)
assert_type(base.at_path([]), Q)
assert_type(base.children(), Tuple[Q, ...])
assert_type(base.node_kind(), str)
assert_type(base.value_type(), ValueType)
assert_type(base.shares_node(base), bool)
assert_type(base.replace_at([], Q.from_metric("other"), "promql"), Q)
try:
    Q.parse("up + @")
except ParseError as parse_error:
    assert_type(parse_error.kind, ParseErrorKind)
    assert_type(parse_error.start, int)
    assert_type(parse_error.end, int)
assert_type(Q().from_metric("up"), Q)
assert_type(base, Q)
assert_type(base.where_regex("instance", "api-.*"), Q)
rate = base.rate("5m").sum().by("job")
assert_type(rate, Q)
assert_type(rate.build("promql"), str)
assert_type(rate.build(QueryMode.PROMQL, features=("promql-duration-expr",)), str)
assert_type(base.avg().without("instance"), Q)
assert_type(base.topk(3).by("job"), Q)
assert_type(base.topk_avg(3, other="other"), Q)
assert_type(base.default(0).keep_metric_names(), Q)
assert_type(Q.time(), Q)
assert_type(Q.now(), Q)
assert_type(Q.from_time(), Q)
assert_type(Q.query_range(), Q)
assert_type(Q.from_scalar(1), Q)
assert_type(Q.vector(1), Q)
assert_type(Q.from_scalar(1).vector(), Q)
assert_type(Q.function("rate", base.range("5m")), Q)
assert_type(Q.from_labels(job="api"), Q)
assert_type(base + 1, Q)
assert_type(2 * base, Q)
assert_type(base > 1, Q)
assert_type(base == 1, Q)
assert_type(base != 1, Q)
assert_type((base > 1) & (base < 10), Q)
assert_type(base.add(1).on("job").group_left("instance"), Q)
assert_type(base.range(Q.step().max_of(60)).rate(), Q)
assert_type(base.subquery("1h", resolution="1m").offset("5m"), Q)
assert_type(base.at(datetime.now(timezone.utc)), Q)
assert_type(base.at(Q.start()), Q)
assert_type(base.label_copy(("job", "service")).label_map("service", ("api", "public")), Q)
assert_type(base.histogram_quantile(0.95, bounds_label="bound"), Q)
assert_type(base.histogram_quantiles("phi", 0.5, 0.95), Q)
assert_type(base.count_values_over_time("value", "5m"), Q)
assert_type(base.ascent_over_time("5m").range_normalize(), Q)
assert_type(base.quantile_over_time(quantile=0.9, duration="5m"), Q)
assert_type(base.rollup_candlestick("5m", result="open"), Q)
assert_type(Q.rand(seed=2).range_trim_outliers(3), Q)
assert_type(Q.timezone_offset("UTC"), Q)
template = Q.template("x", body=Q.reference("x").rate("5m"))
assert_type(template, Q)
assert_type(Q.template_call("f", base).with_(f=template), Q)
prefix = Q.reference("prefix", kind="string")
assert_type(Q.from_labels().where_eq("__name__", prefix + "requests_total"), Q)
assert_type(base.validate("promql"), str)
assert_type(base.debug_positions(mode="promql"), str)
assert_type(base.to_debug_json(), str)
assert_type(base.debug(), str)
assert_type(base.analyze(), Dict[str, Any])
assert_type(base.validate("PromQL"), str)
assert_type(base.sum().limit(3.0), Q)
assert_type(base.range("5m").holt_winters(None), Q)
assert_type(base.range("5m").moving_average(None), Q)
assert_type(base.rollup("5m", result=Q.from_string("min")), Q)
assert_type(base.rollup("5m", func=Q.from_string("min")), Q)
assert_type(base.rollup_rate("5m", result=Q.from_string("min")), Q)
assert_type(base.rollup_candlestick("5m", result=Q.from_string("open")), Q)
assert_type(base.rollup_delta("5m", result=Q.from_string("min")), Q)
assert_type(base.aggr_over_time(Q.from_string("rate"), window="5m"), Q)
assert_type(base.label_graphite_group(Q.from_scalar(1)), Q)
assert_type(base.drop_common_labels(1), Q)
string_reference = Q.reference("s", kind="string")
assert_type(base.label_set(job=string_reference).with_(s="api"), Q)
assert_type(base.label_del(string_reference).with_(s="job"), Q)
assert_type(base.label_keep(string_reference).with_(s="job"), Q)
assert_type(base.label_lowercase(string_reference).with_(s="job"), Q)
assert_type(base.label_uppercase(string_reference).with_(s="job"), Q)
assert_type(base.label_map(string_reference, ("api", "public")).with_(s="job"), Q)
assert_type(base.label_match(string_reference, "api").with_(s="job"), Q)
assert_type(base.label_mismatch(string_reference, "api").with_(s="job"), Q)
assert_type(base.label_transform(string_reference, "api", "public").with_(s="job"), Q)
assert_type(base.label_value(string_reference).with_(s="job"), Q)
assert_type(base.labels_equal(string_reference, "instance").with_(s="job"), Q)
assert_type(base.alias(string_reference).with_(s="renamed"), Q)
assert_type(base.sort_by_label(string_reference).with_(s="job"), Q)
assert_type(base.sort_by_label_desc(string_reference).with_(s="job"), Q)
assert_type(base.sort_by_label_numeric(string_reference).with_(s="job"), Q)
assert_type(base.sort_by_label_numeric_desc(string_reference).with_(s="job"), Q)
assert_type(base.histogram_quantiles(string_reference, 0.5).with_(s="phi"), Q)
assert_type(base.quantiles_over_time(string_reference, 0.5, window="5m").with_(s="phi"), Q)
assert_type(MetricsInsertData(query="up", times=[0], values=[1]), MetricsInsertData)
sample_times = [0, 1]
sample_values = [1.0, 2.0]
assert_type(MetricsInsertData(query="up", times=sample_times, values=sample_values), MetricsInsertData)
assert_type(MetricsInsertData(query="up", times=(0, 1), values=(1.0, 2.0)), MetricsInsertData)


@vm_only
def vm_expression(value: Q) -> Q:
    return value.default(0)


@prom_only
def prom_expression(value: Q) -> Q:
    return value.histogram_count()


assert_type(vm_expression(base), Q)
assert_type(prom_expression(base), Q)
options = HttpClientOptions(timeout=(1.0, 10.0), default_headers={"X-Application": "example"})
assert_type(HttpClientOptions(timeout=5), HttpClientOptions)
assert_type(HttpClientOptions(timeout=0.5), HttpClientOptions)
assert_type(options.timeout, Optional[Tuple[Union[int, float], Union[int, float]]])
if options.timeout is not None:
    connect_timeout, read_timeout = options.timeout
    assert_type(connect_timeout, Union[int, float])
    assert_type(read_timeout, Union[int, float])
    assert_type(options.timeout[0], Union[int, float])
prometheus = PrometheusConfig("http://localhost:9090", http_options=options)
assert_type(prometheus, PrometheusConfig)
assert_type(VMSingleConfig("http://localhost:8428"), VMSingleConfig)
assert_type(VMClusterConfig(vmselect_url="http://select:8481", vminsert_url="http://insert:8480",
                          vmstorage_url="http://storage:8482", account_id=1), VMClusterConfig)
register_config(prometheus, instance="example")
set_default_instance(DBType.PROMETHEUS, "example")
assert_type(get_config(DBType.PROMETHEUS, "example"), Config)

with DatabaseClient(prometheus) as client:
    assert_type(client, DatabaseClient)
    result = client.query(rate)
    assert_type(result, MetricsQueryResult)
    assert_type(result.is_success, bool)
    assert_type(result.error, Optional[str])
    assert_type(client.query_range(rate, start=0, end=60, step="15s"), MetricsQueryResult)
    assert_type(client.series([base, "up"]), SeriesResult)
    assert_type(client.labels(match=base), LabelsResult)
    assert_type(client.label_values("job", match=base), LabelValuesResult)
    assert_type(client.labels(match=base).labels, List[str])
    selectors = [base]
    assert_type(client.series(selectors), SeriesResult)
    mixed_selectors: List[Q | str] = [base, "up"]
    assert_type(client.series(mixed_selectors), SeriesResult)
    assert_type(client.series((base, "up")), SeriesResult)
    assert_type(client.query(base, extra_filters=("{job=\"api\"}",)), MetricsQueryResult)


async def async_usage() -> MetricsQueryResult:
    async with DatabaseClient(prometheus) as client:
        assert_type(client, DatabaseClient)
        result = await client.query_async(base)
        assert_type(result, MetricsQueryResult)
        assert_type(await client.series_async(base), SeriesResult)
        return result


class CustomTransport:
    def get(self, url: str, params: Optional[HTTPParams] = None, *,
            headers: Optional[HTTPHeaders] = None,
            timeout: Optional[HTTPTimeout] = None) -> HTTPResponse:
        return {"status": "success", "data": {"resultType": "vector", "result": []}}

    def post(self, url: str, data: HTTPBody = None,
             params: Optional[HTTPParams] = None, *,
             headers: Optional[HTTPHeaders] = None,
             timeout: Optional[HTTPTimeout] = None,
             content_type: Optional[str] = None) -> HTTPResponse:
        return {}


class CustomAsyncTransport:
    async def get(self, url: str, params: Optional[HTTPParams] = None, *,
                  headers: Optional[HTTPHeaders] = None,
                  timeout: Optional[HTTPTimeout] = None) -> HTTPResponse:
        return {}

    async def post(self, url: str, data: HTTPBody = None,
                   params: Optional[HTTPParams] = None, *,
                   headers: Optional[HTTPHeaders] = None,
                   timeout: Optional[HTTPTimeout] = None,
                   content_type: Optional[str] = None) -> HTTPResponse:
        return {}


def sync_factory(*, http_options: Mapping[str, object],
                 connection_info: Mapping[str, object]) -> SyncHTTPTransport:
    return CustomTransport()


def async_factory(*, http_options: Mapping[str, object],
                  connection_info: Mapping[str, object],
                  sync_client: SyncHTTPTransport) -> AsyncHTTPTransport:
    return AsyncHTTPClient(sync_client=sync_client)


def consume_factories(sync: SyncHTTPTransportFactory, async_: AsyncHTTPTransportFactory) -> None:
    options = HttpClientOptions(client_factory=sync, async_client_factory=async_)
    assert_type(options.client_factory, Optional[SyncHTTPTransportFactory])
    assert_type(options.async_client_factory, Optional[AsyncHTTPTransportFactory])


consume_factories(sync_factory, async_factory)
custom_options = HttpClientOptions(client=CustomTransport(), async_client=CustomAsyncTransport())
assert_type(custom_options.client, Optional[SyncHTTPTransport])
assert_type(custom_options.async_client, Optional[AsyncHTTPTransport])
default_options = HttpClientOptions(client=SyncHTTPClient(), async_client=AsyncHTTPClient())
with DatabaseClient(PrometheusConfig("http://localhost:9090", http_options=custom_options)) as custom:
    assert_type(custom.client, SyncHTTPTransport)
    assert_type(custom.async_client, Optional[AsyncHTTPTransport])
    assert_type(custom.client.get("http://localhost:9090/api/v1/query"), HTTPResponse)
    custom.client = CustomTransport()
    custom.async_client = CustomAsyncTransport()


async def transport_mapping_inputs(sync: SyncHTTPTransport, async_: AsyncHTTPTransport) -> None:
    params = {"query": "up"}
    body = {"label": "value"}
    assert_type(sync.get("http://localhost:9090", params=params), HTTPResponse)
    assert_type(sync.post("http://localhost:9090", data=body, params=params), HTTPResponse)
    assert_type(await async_.get("http://localhost:9090", params=params), HTTPResponse)
    assert_type(await async_.post("http://localhost:9090", data=body, params=params), HTTPResponse)
