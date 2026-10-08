import pytest
from unittest.mock import patch, AsyncMock

from metricraft import DatabaseClient, QueryBuilder
from metricraft import MetricsInsertData


def test_prepare_query_accept_builder():
    client = DatabaseClient()
    q = QueryBuilder.from_metric('up').where_eq('job', 'prometheus')
    with patch.object(client, 'client') as mock_http:
        mock_http.get.return_value = {'status': 'success', 'data': {'resultType': 'vector', 'result': []}}
        r = client.query(q)
        assert r.status == 'success'


def test_query_with_time_variants():
    client = DatabaseClient()
    with patch.object(client, 'client') as mock_http:
        mock_http.get.return_value = {'status': 'success', 'data': {'resultType': 'vector', 'result': []}}
        # int seconds
        assert client.query('up', time=1640995200).is_success
        # float seconds
        assert client.query('up', time=1640995200.0).is_success
        # iso string
        assert client.query('up', time='2022-01-01T00:00:00Z').is_success


def test_health_and_errors():
    client = DatabaseClient()
    with patch.object(client, 'client') as mock_http:
        mock_http.get_text.return_value = 'OK'
        assert client.health() is True
    with patch.object(client, 'client') as mock_http:
        mock_http.get_text.side_effect = Exception('boom')
        assert client.health() is False


@pytest.mark.asyncio
async def test_health_async_and_errors():
    client = DatabaseClient()
    with patch.object(client, 'async_client') as mock_async:
        mock_async.get_text = AsyncMock(return_value='OK')
        assert await client.health_async() is True
    with patch.object(client, 'async_client') as mock_async:
        mock_async.get_text = AsyncMock(side_effect=Exception('boom'))
        assert await client.health_async() is False


def test_convert_to_prometheus_format_mixed_times():
    client = DatabaseClient()
    data = MetricsInsertData(query='m{l="v"}', times=[1640995200, '1640995201000'], values=[1.0, 2.0])
    # Directly test the private conversion function output (inserting is too heavy)
    out = client._convert_to_prometheus_format(data)
    assert 'm{l="v"} 1.0 1640995200000' in out.splitlines()
    assert 'm{l="v"} 2.0 1640995201000' in out


def test_convert_to_prometheus_format_multiple_payloads():
    client = DatabaseClient()
    d1 = MetricsInsertData(query='m1', times=[1, 2], values=[1.1, 2.2])
    d2 = MetricsInsertData(query='m2{l="x"}', times=[3], values=[3.3])
    out = client._convert_to_prometheus_format([d1, d2])
    lines = out.splitlines()
    assert 'm1 1.1 1000' == lines[0]
    assert 'm1 2.2 2000' == lines[1]
    assert 'm2{l="x"} 3.3 3000' in lines
    assert len(lines) == 3


def test_convert_to_prometheus_format_empty_iterable_raises():
    client = DatabaseClient()
    with pytest.raises(ValueError, match="cannot be empty"):
        client._convert_to_prometheus_format([])
