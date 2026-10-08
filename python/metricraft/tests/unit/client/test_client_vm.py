import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from metricraft import DatabaseClient
from metricraft import MetricsInsertData, register_config
from metricraft.config import reset_config
from metricraft.config.http_options import HttpClientOptions
from metricraft.config import VMSingleConfig


def test_query_and_query_range_params(monkeypatch):
    reset_config()
    register_config(VMSingleConfig('http://localhost:8428', http_options=HttpClientOptions(timeout=1.0)))
    client = DatabaseClient()

    # Mock http client get
    with patch.object(client, 'client') as mock_http:
        mock_http.get.return_value = {
            'status': 'success',
            'data': {'resultType': 'vector', 'result': []}
        }
        r = client.query('up')
        assert r.status == 'success'

        r2 = client.query_range('up', start=1640991600, end=1640995200, step='1m')
        assert r2.status == 'success'


def test_insert_sync_no_network(monkeypatch):
    reset_config()
    register_config(VMSingleConfig('http://localhost:8428', http_options=HttpClientOptions(timeout=1.0)))
    client = DatabaseClient()

    # Mock urlopen to avoid real network (patch where it's used)
    with patch('metricraft.client.http_client.urlopen') as mock_urlopen:
        mock_resp = MagicMock()
        # urlopen().__enter__().read().decode('utf-8') -> '{}'
        mock_resp.read.return_value = b'{}'
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        data = MetricsInsertData(
            query='test_metric{job="demo"}',
            times=[1640995200, 1640995260],
            values=[1.0, 2.0]
        )
        out = client.insert(data)
        assert isinstance(out, dict)

        # batch insert should also work
        batch = [
            MetricsInsertData(query='test_metric{job="demo"}', times=[1640995200], values=[1.0]),
            MetricsInsertData(query='test_metric{job="demo2"}', times=[1640995260], values=[2.0]),
        ]
        out2 = client.insert(batch)
        assert isinstance(out2, dict)


@pytest.mark.asyncio
async def test_async_endpoints():
    reset_config()
    register_config(VMSingleConfig('http://localhost:8428', http_options=HttpClientOptions(timeout=1.0)))
    client = DatabaseClient()

    with patch.object(client, 'async_client') as mock_async:
        mock_async.get = AsyncMock(return_value={
            'status': 'success',
            'data': {'resultType': 'matrix', 'result': []}
        })
        r = await client.query_async('up')
        assert r.status == 'success'

        mock_async.get = AsyncMock(return_value={
            'status': 'success',
            'data': {'resultType': 'matrix', 'result': []}
        })
        r2 = await client.query_range_async('up', start=1640991600, end=1640995200, step='1m')
        assert r2.status == 'success'

    with patch.object(client, 'async_client') as mock_async:
        mock_async.post = AsyncMock(return_value={})
        data = MetricsInsertData(query='m', times=[1640995200], values=[1.0])
        out = await client.insert_async(data)
        assert isinstance(out, dict)

        batch = [
            MetricsInsertData(query='m', times=[1640995200], values=[1.0]),
            MetricsInsertData(query='m', times=[1640995260], values=[2.0]),
        ]
        out2 = await client.insert_async(batch)
        assert isinstance(out2, dict)
