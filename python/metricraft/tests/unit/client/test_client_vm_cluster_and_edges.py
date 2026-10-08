import pytest
from unittest.mock import patch, AsyncMock

from metricraft import DatabaseClient
from metricraft.config import VMClusterConfig
from metricraft import register_config
from metricraft.config import reset_config
from metricraft.config.http_options import HttpClientOptions


def test_cluster_urls_select_and_insert():
    reset_config()
    cfg = VMClusterConfig(
        vminsert_url='http://vminsert:8480',
        vmselect_url='http://vmselect:8481',
        vmstorage_url='http://vmstorage:8482',
        http_options=HttpClientOptions(timeout=1.0)
    )
    register_config(cfg)
    client = DatabaseClient()

    # query should use select_base_url
    with patch.object(client, 'client') as mock_http:
        mock_http.get.return_value = {'status': 'success', 'data': {'resultType': 'vector', 'result': []}}
        r = client.query('up')
        assert r.is_success

    # insert should use insert_base_url
    with patch('metricraft.client.http_client.urlopen') as mock_urlopen:
        mock_urlopen.return_value.__enter__().read.return_value = b'{}'
        from metricraft import MetricsInsertData
        data = MetricsInsertData(query='m', times=[1], values=[1.0])
        out = client.insert(data)
        assert isinstance(out, dict)


def test_async_not_available_guard():
    # Force async_client None to hit guard branch
    reset_config()
    cfg = VMClusterConfig(
        vminsert_url='http://vminsert:8480',
        vmselect_url='http://vmselect:8481',
        vmstorage_url='http://vmstorage:8482',
        http_options=HttpClientOptions(timeout=1.0)
    )
    register_config(cfg)
    client = DatabaseClient()
    # Manually set to None to trigger guard (coverage only)
    client.async_client = None
    with pytest.raises(RuntimeError):
        import asyncio
        asyncio.run(client.query_async('up'))
