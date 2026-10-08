import pytest
from datetime import datetime

from metricraft._legacy.builder.impl.instant_vector import InstantVectorBuilder
from metricraft._legacy.builder.impl.processed_vector import ProcessedVectorBuilder
from metricraft._legacy.tree import MetricSelector, NumberLiteral
from metricraft._legacy.exceptions import VMInvalidExpressionError
from metricraft._legacy.exceptions import InvalidParameterError
from metricraft.models import MetricsQueryResult, MetricsInsertData

from metricraft.client.db_client import DatabaseClient


def _make_iv(metric: str = "cpu_usage") -> InstantVectorBuilder:
    return InstantVectorBuilder(MetricSelector(metric))


def test_comparison_and_logical_magic_ops():
    b = _make_iv()
    # comparison magic methods
    res_eq = (b == 1)
    res_ne = (b != 1)
    assert isinstance(res_eq, ProcessedVectorBuilder)
    assert isinstance(res_ne, ProcessedVectorBuilder)

    # logical magic methods
    res_and = (b & b)
    res_or = (b | b)
    assert isinstance(res_and, ProcessedVectorBuilder)
    assert isinstance(res_or, ProcessedVectorBuilder)


def test_mathematical_round_with_argument():
    b = _make_iv()
    out = b.round(2.0)
    assert isinstance(out, ProcessedVectorBuilder)

    # default branch
    out2 = b.round()
    assert isinstance(out2, ProcessedVectorBuilder)


def test_time_range_at_iso_and_ms_timestamp():
    b = _make_iv()
    # ISO 8601 string
    out_iso = b.at("2021-01-01T00:00:00Z")
    assert out_iso is not None

    # Milliseconds timestamp
    out_ms = b.at(1609459200000)
    assert out_ms is not None

    # unsupported type
    with pytest.raises(TypeError):
        b.at(object())


def test_time_range_offset_basic():
    b = _make_iv()
    out = b.offset("5m")
    assert out is not None


def test_instant_vector_metric_preserves_matchers_and_invalid_operator():
    b = _make_iv().where_eq("job", "api")
    b2 = b.metric("memory_usage")
    # ensure label matcher preserved (type-level check by building again)
    b3 = b2.where_ne("job", "db").metric("disk_io")
    assert isinstance(b3, InstantVectorBuilder)

    with pytest.raises(ValueError):
        _make_iv().where("job", "??", "x")

    # between() invalid range
    with pytest.raises(InvalidParameterError):
        _make_iv().between(5, 4)


def test_vm_invalid_expression_error_position_compat():
    # legacy position parameter path
    from metricraft._legacy.ast import Position

    # Use core Position factory; VM error supports legacy 'position' parameter by wrapping it
    pos = Position.for_text("x", offset=3)
    err = VMInvalidExpressionError("op", position=pos)
    # The error should attach a pseudo node with the same position
    assert getattr(err, "ast_node", None) is not None
    assert getattr(err.ast_node, "pos", None) == pos


def test_instant_vector_constructor_type_error():
    # Passing wrong AST node type should raise TypeError
    with pytest.raises(TypeError):
        InstantVectorBuilder(NumberLiteral(1.0))


def test_vm_client_helpers_and_health_fallback(monkeypatch):
    # Exercise the concrete client with its normal resource initialization
    c = DatabaseClient()
    # Shadow cached_property with direct value
    c.select_base_url = "http://example.com"

    class DummyClient:
        def get(self, url, params=None):
            raise RuntimeError("boom")

        def post(self, url, data=None, headers=None):
            return {"status": "ok"}

    c.client = DummyClient()

    # health should catch exception and return False
    assert c.health() is False

    # simulate string response containing 'victoria metrics'
    class OKClient:
        def get(self, url, params=None):
            return {"status": "ok", "message": "Victoria Metrics is OK"}

    c.client = OKClient()
    assert c.health() is True

    # _normalize_time branches
    assert c._normalize_time(None) is None
    assert c._normalize_time("2020-01-01T00:00:00Z") == "2020-01-01T00:00:00Z"
    assert c._normalize_time(1609459200) == "1609459200"  # seconds
    assert c._normalize_time(1609459200000) == "1609459200"  # ms -> seconds
    ts = int(datetime(2021, 1, 1).timestamp())
    assert c._normalize_time(datetime(2021, 1, 1)) == str(ts)

    with pytest.raises(ValueError):
        c._normalize_time(object())

    # _convert_to_prometheus_format basic path
    data = MetricsInsertData(query="foo", times=[1609459200000, None], values=[1.0, 2.0])
    text = c._convert_to_prometheus_format(data)
    # first line contains normalized timestamp, second has empty ts
    lines = text.splitlines()
    assert lines[0].startswith("foo 1.0 ")
    assert lines[1] == "foo 2.0 "


def test_vm_client_query_and_query_range_success():
    c = DatabaseClient()
    c.select_base_url = "http://example.com"
    # ensure default_step exists for query_range
    c.default_step = "1m"
    # Initialize connection_info to avoid AttributeError
    c.connection_info = {'type': 'single', 'url': 'http://example.com'}

    captured = {}

    class OKClient:
        def get(self, url, params=None):
            captured["url"] = url
            captured["params"] = dict(params or {})
            # minimal VM response
            return {
                "status": "success",
                "resultType": "matrix",
                "data": {"result": []},
            }

    c.client = OKClient()

    # query with raw string
    res = c.query("up")
    assert isinstance(res, MetricsQueryResult)
    assert res.is_success is True
    assert "/api/v1/query" in captured["url"]
    assert captured["params"]["query"] == "up"

    # query_range with inferred start and provided end
    captured.clear()
    res2 = c.query_range("up", end=1700000000)
    assert isinstance(res2, MetricsQueryResult)
    assert "/api/v1/query_range" in captured["url"]
    assert "start" in captured["params"] and "end" in captured["params"] and "step" in captured["params"]


def test_vm_query_result_repr_and_to_dict():
    # Test success result with complete repr
    vr = MetricsQueryResult(
        _status="success",
        _data={
            "resultType": "matrix",
            "result": [{"metric": {}, "values": []}]
        },
        _stats={
            "executionTimeMsec": 12.5,
            "seriesFetched": "150"
        },
        _warnings=["w1"],
    )
    s = repr(vr)
    assert "MetricsQueryResult(" in s and "status='success'" in s
    # Now repr shows complete data dict
    assert "data=" in s
    assert "'resultType': 'matrix'" in s
    assert "stats=" in s
    assert "warnings=" in s
    
    d = vr.to_dict()
    assert d["status"] == "success"
    assert d["data"]["resultType"] == "matrix"
    assert d["stats"]["executionTimeMsec"] == 12.5
    
    # Test error result
    vr_err = MetricsQueryResult(
        _status="error",
        _error="parse error",
        _error_type="bad_data"
    )
    s_err = repr(vr_err)
    assert "error='parse error'" in s_err
    assert "errorType='bad_data'" in s_err
    
    d_err = vr_err.to_dict()
    assert d_err["status"] == "error"
    assert d_err["error"] == "parse error"
    assert d_err["errorType"] == "bad_data"


def test_quantile_over_time_success():
    b = _make_iv()
    out = b.quantile_over_time(quantile=0.5, duration="5m")
    assert isinstance(out, ProcessedVectorBuilder)


def test_metricsbuilder_empty_build_and_query_string_error():
    # Accessing _query_string with no AST should raise ValueError
    from metricraft._legacy.builder.impl.base import MetricsBuilder

    m = MetricsBuilder(ast_node=None)
    with pytest.raises(ValueError):
        _ = m._query_string

    # build(validate=False) should also surface ValueError via cached property
    with pytest.raises(ValueError):
        m.build(validate=False)


def test_validation_mixin_invalid_standard_and_quantile_bounds():
    b = _make_iv()
    with pytest.raises(InvalidParameterError):
        # invalid standard name
        b.validate(standard="Foo")

    # invalid quantile range
    with pytest.raises(InvalidParameterError):
        b.quantile_over_time(quantile=1.1, duration="5m")

    # zscore_over_time path (smoke)
    out = b.zscore_over_time("5m")
    assert isinstance(out, ProcessedVectorBuilder)


def test_vm_client_prepare_query_with_builder_stub():
    class Stub:
        def build(self):
            return "stubbed"

    c = DatabaseClient()
    assert c._prepare_query(Stub()) == "stubbed"


@pytest.mark.asyncio
async def test_vm_client_async_methods():
    c = DatabaseClient()
    c.select_base_url = "http://example.com"
    c.insert_base_url = "http://example.com"
    # Initialize connection_info to avoid AttributeError
    c.connection_info = {'type': 'single', 'url': 'http://example.com'}

    class AsyncOK:
        async def get(self, url, params=None):
            return {"status": "ok"}

        async def post(self, url, data=None, headers=None, params=None):
            return {"ok": 1}

    class AsyncFail:
        async def get(self, url, params=None):
            raise RuntimeError("boom")

    c.async_client = AsyncOK()
    assert await c.health_async() is True
    resp = await c.insert_async(MetricsInsertData(query="m", times=[None], values=[1.0]))
    assert resp["ok"] == 1

    c.async_client = AsyncFail()
    assert await c.health_async() is False


def test_between_without_base_expression():
    from metricraft._legacy.builder.impl.base import MetricsBuilder
    m = MetricsBuilder(ast_node=None)
    with pytest.raises(VMInvalidExpressionError):
        m.between(1, 2)
