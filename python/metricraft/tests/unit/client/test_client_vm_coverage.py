import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime

from metricraft import DatabaseClient
from metricraft import register_config, MetricsInsertData
from metricraft.config import reset_config
from metricraft.config.http_options import HttpClientOptions
from metricraft.config import VMSingleConfig, VMClusterConfig


def test_properties_single_and_cluster_urls():
    # single
    reset_config()
    register_config(VMSingleConfig('http://localhost:8428', http_options=HttpClientOptions(timeout=1.0)))
    c1 = DatabaseClient()
    assert c1.select_base_url.endswith(':8428/prometheus')
    assert c1.insert_base_url.endswith(':8428/prometheus')
    assert c1.storage_base_url.endswith(':8428')

    # cluster
    reset_config()
    register_config(VMClusterConfig(
        vminsert_url='http://vminsert:8480',
        vmselect_url='http://vmselect:8481',
        vmstorage_url='http://vmstorage:8482',
        http_options=HttpClientOptions(timeout=1.0)
    ))
    c2 = DatabaseClient()
    assert c2.select_base_url.endswith('vmselect:8481/select/0/prometheus')
    assert c2.insert_base_url.endswith('vminsert:8480/insert/0/prometheus')
    assert c2.storage_base_url.endswith('vmstorage:8482')


def test_normalize_time_edges():
    c = DatabaseClient()
    # datetime
    assert c._normalize_time(datetime.fromtimestamp(1640995200)) == '1640995200'
    # milliseconds numeric
    assert c._normalize_time(1640995200000) == '1640995200'
    # invalid type
    with pytest.raises(ValueError):
        c._normalize_time(['bad'])


def test_insert_format_none_timestamp():
    c = DatabaseClient()
    d = MetricsInsertData(query='m', times=[None, 1640995200], values=[1.0, 2.0])
    text = c._convert_to_prometheus_format(d)
    # First line has no timestamp, second line has one
    lines = text.splitlines()
    assert lines[0].endswith(' 1.0 ')
    assert lines[1].endswith(' 2.0 1640995200000')


def test_query_range_time_types_and_default_step():
    c = DatabaseClient()
    with patch.object(c, 'client') as mock_http:
        mock_http.get.return_value = {'status': 'success', 'data': {'resultType': 'matrix', 'result': []}}
        r = c.query_range('up', start='2022-01-01T00:00:00Z', end=datetime.fromtimestamp(1640995200))
        assert r.is_success
    # Without explicit step, default_step should be used
        args, kwargs = mock_http.get.call_args
    # Params should be present in kwargs['params']
        assert kwargs['params']['step'] == c.default_step


def test_query_with_milliseconds_time():
    c = DatabaseClient()
    with patch.object(c, 'client') as mock_http:
        mock_http.get.return_value = {'status': 'success', 'data': {'resultType': 'vector', 'result': []}}
    # Millisecond timestamp input should be normalized to seconds internally
        assert c.query('up', time=1640995200000).is_success


def test_query_range_override_step():
    c = DatabaseClient()
    with patch.object(c, 'client') as mock_http:
        mock_http.get.return_value = {'status': 'success', 'data': {'resultType': 'matrix', 'result': []}}
        r = c.query_range('up', start=1640991600, end=1640995200, step='5m')
        assert r.is_success
        args, kwargs = mock_http.get.call_args
        assert kwargs['params']['step'] == '5m'


@pytest.mark.asyncio
async def test_query_range_async_end_str_start_none():
    c = DatabaseClient()
    with patch.object(c, 'async_client') as mock_async:
        mock_async.get = AsyncMock(return_value={'status': 'success', 'data': {'resultType': 'matrix', 'result': []}})
    # end provided as integer seconds and start=None should trigger start calculation branch
        r = await c.query_range_async('up', end=1640995200)
        assert r.is_success


def test_invalid_connection_type_properties():
    c = DatabaseClient()
    # Force invalid connection type to cover error branch
    c.connection_info['type'] = 'invalid'
    # select_base_url and insert_base_url now use config methods, so they won't raise ValueError
    # only storage_base_url has the type check
    with pytest.raises(ValueError):
        _ = c.storage_base_url


@pytest.mark.asyncio
async def test_query_async_with_time_and_range_variants():
    c = DatabaseClient()
    with patch.object(c, 'async_client') as mock_async:
        mock_async.get = AsyncMock(return_value={'status': 'success', 'data': {'resultType': 'vector', 'result': []}})
        assert (await c.query_async('up', time='2022-01-01T00:00:00Z')).is_success

    with patch.object(c, 'async_client') as mock_async:
        mock_async.get = AsyncMock(return_value={'status': 'success', 'data': {'resultType': 'matrix', 'result': []}})
        assert (await c.query_range_async('up', start=1640991600, end=1640995200)).is_success
