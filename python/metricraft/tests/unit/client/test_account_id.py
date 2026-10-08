"""Tests for account_id parameter support in VM client."""

import pytest
from unittest.mock import patch

from metricraft import register_config, DatabaseClient
from metricraft.config import reset_config
from metricraft.config.http_options import HttpClientOptions
from metricraft.config import VMSingleConfig, VMClusterConfig, PrometheusConfig
from metricraft.client.db_client import DatabaseClient
from metricraft import MetricsInsertData


def test_validate_account_id_with_non_cluster_config():
    """Test that account_id raises ValueError for non-cluster configs."""
    reset_config()
    register_config(VMSingleConfig('http://localhost:8428', http_options=HttpClientOptions(timeout=1.0)))
    client = DatabaseClient()

    # Test _validate_account_id directly
    with pytest.raises(ValueError, match="account_id parameter is only supported for VMClusterConfig"):
        client._validate_account_id(100)

    # account_id=None should be fine
    client._validate_account_id(None)


def test_validate_account_id_with_invalid_type():
    """Test that account_id must be an integer."""
    reset_config()
    register_config(VMClusterConfig(
        vminsert_url='http://vminsert:8480',
        vmselect_url='http://vmselect:8481',
        vmstorage_url='http://vmstorage:8482',
        http_options=HttpClientOptions(timeout=1.0)
    ))
    client = DatabaseClient()

    # Test non-integer account_id
    with pytest.raises(ValueError, match="account_id must be an integer"):
        client._validate_account_id("100")

    with pytest.raises(ValueError, match="account_id must be an integer"):
        client._validate_account_id(100.5)


def test_validate_account_id_with_negative_value():
    """Test that account_id must be non-negative."""
    reset_config()
    register_config(VMClusterConfig(
        vminsert_url='http://vminsert:8480',
        vmselect_url='http://vmselect:8481',
        vmstorage_url='http://vmstorage:8482',
        http_options=HttpClientOptions(timeout=1.0)
    ))
    client = DatabaseClient()

    # Test negative account_id
    with pytest.raises(ValueError, match="account_id must be non-negative"):
        client._validate_account_id(-1)


def test_get_effective_account_id_with_override():
    """Test that override account_id is used when provided."""
    reset_config()
    register_config(VMClusterConfig(
        vminsert_url='http://vminsert:8480',
        vmselect_url='http://vmselect:8481',
        vmstorage_url='http://vmstorage:8482',
        account_id=100,
        http_options=HttpClientOptions(timeout=1.0)
    ))
    client = DatabaseClient()

    # Test with override
    effective_id = client._get_effective_account_id(200)
    assert effective_id == 200

    # Test without override - should use config default
    effective_id = client._get_effective_account_id(None)
    assert effective_id == 100


def test_get_query_url_with_account_for_cluster():
    """Test query URL construction with account_id for cluster config."""
    reset_config()
    register_config(VMClusterConfig(
        vminsert_url='http://vminsert:8480',
        vmselect_url='http://vmselect:8481',
        vmstorage_url='http://vmstorage:8482',
        account_id=100,
        http_options=HttpClientOptions(timeout=1.0)
    ))
    client = DatabaseClient()

    # Test with override account_id
    url = client._get_query_url_with_account(account_id=200)
    assert url == 'http://vmselect:8481/select/200/prometheus'

    # Test without override - should use config default
    url = client._get_query_url_with_account(account_id=None)
    assert url == 'http://vmselect:8481/select/100/prometheus'


def test_get_query_url_with_account_for_single_raises_error():
    """Test that account_id raises error for single config in URL methods."""
    reset_config()
    register_config(VMSingleConfig('http://localhost:8428', http_options=HttpClientOptions(timeout=1.0)))
    client = DatabaseClient()

    # account_id should raise error for single config
    with pytest.raises(ValueError, match="account_id parameter is only supported for VMClusterConfig"):
        client._get_query_url_with_account(account_id=100)

    # Without account_id should work fine
    url = client._get_query_url_with_account(account_id=None)
    assert url == 'http://localhost:8428/prometheus'


def test_get_insert_url_with_account_for_cluster():
    """Test insert URL construction with account_id for cluster config."""
    reset_config()
    register_config(VMClusterConfig(
        vminsert_url='http://vminsert:8480',
        vmselect_url='http://vmselect:8481',
        vmstorage_url='http://vmstorage:8482',
        account_id=100,
        http_options=HttpClientOptions(timeout=1.0)
    ))
    client = DatabaseClient()

    # Test with override account_id
    url = client._get_insert_url_with_account(account_id=200)
    assert url == 'http://vminsert:8480/insert/200/prometheus'

    # Test without override - should use config default
    url = client._get_insert_url_with_account(account_id=None)
    assert url == 'http://vminsert:8480/insert/100/prometheus'


def test_get_insert_url_with_account_for_single_raises_error():
    """Test that account_id raises error for single config in insert URL."""
    reset_config()
    register_config(VMSingleConfig('http://localhost:8428', http_options=HttpClientOptions(timeout=1.0)))
    client = DatabaseClient()

    # account_id should raise error for single config
    with pytest.raises(ValueError, match="account_id parameter is only supported for VMClusterConfig"):
        client._get_insert_url_with_account(account_id=100)

    # Without account_id should work fine
    url = client._get_insert_url_with_account(account_id=None)
    assert url == 'http://localhost:8428/prometheus'


def test_query_with_account_id_override():
    """Test query() with account_id override for cluster config."""
    reset_config()
    register_config(VMClusterConfig(
        vminsert_url='http://vminsert:8480',
        vmselect_url='http://vmselect:8481',
        vmstorage_url='http://vmstorage:8482',
        account_id=100,
        http_options=HttpClientOptions(timeout=1.0)
    ))
    client = DatabaseClient()

    with patch.object(client, 'client') as mock_http:
        mock_http.get.return_value = {'status': 'success', 'data': {'resultType': 'vector', 'result': []}}

        # Query with account_id override
        result = client.query('up', account_id=200)

        # Verify the URL used
        call_args = mock_http.get.call_args
        assert '/select/200/prometheus/api/v1/query' in call_args[0][0]


def test_query_with_account_id_on_single_config_raises_error():
    """Test that query() with account_id raises error for single config."""
    reset_config()
    register_config(VMSingleConfig('http://localhost:8428', http_options=HttpClientOptions(timeout=1.0)))
    client = DatabaseClient()

    with patch.object(client, 'client') as mock_http:
        mock_http.get.return_value = {'status': 'success', 'data': {'resultType': 'vector', 'result': []}}

        # Query with account_id should raise ValueError
        with pytest.raises(ValueError, match="account_id parameter is only supported for VMClusterConfig"):
            client.query('up', account_id=100)


def test_query_range_with_account_id_override():
    """Test query_range() with account_id override for cluster config."""
    reset_config()
    register_config(VMClusterConfig(
        vminsert_url='http://vminsert:8480',
        vmselect_url='http://vmselect:8481',
        vmstorage_url='http://vmstorage:8482',
        account_id=100,
        http_options=HttpClientOptions(timeout=1.0)
    ))
    client = DatabaseClient()

    with patch.object(client, 'client') as mock_http:
        mock_http.get.return_value = {'status': 'success', 'data': {'resultType': 'matrix', 'result': []}}

        # Query range with account_id override
        result = client.query_range('up', start=1640995200, end=1640998800, account_id=200)

        # Verify the URL used
        call_args = mock_http.get.call_args
        assert '/select/200/prometheus/api/v1/query_range' in call_args[0][0]


def test_query_range_with_account_id_on_single_config_raises_error():
    """Test that query_range() with account_id raises error for single config."""
    reset_config()
    register_config(VMSingleConfig('http://localhost:8428', http_options=HttpClientOptions(timeout=1.0)))
    client = DatabaseClient()

    with patch.object(client, 'client') as mock_http:
        mock_http.get.return_value = {'status': 'success', 'data': {'resultType': 'matrix', 'result': []}}

        # Query range with account_id should raise ValueError
        with pytest.raises(ValueError, match="account_id parameter is only supported for VMClusterConfig"):
            client.query_range('up', start=1640995200, end=1640998800, account_id=100)


def test_insert_with_account_id_override():
    """Test insert() with account_id override for cluster config."""
    reset_config()
    register_config(VMClusterConfig(
        vminsert_url='http://vminsert:8480',
        vmselect_url='http://vmselect:8481',
        vmstorage_url='http://vmstorage:8482',
        account_id=100,
        http_options=HttpClientOptions(timeout=1.0)
    ))
    client = DatabaseClient()

    with patch.object(client, 'client') as mock_http:
        mock_http.post.return_value = {'status': 'ok'}

        # Insert with account_id override
        data = MetricsInsertData(query='metric_name{label="value"}', times=[1640995200], values=[42.0])
        result = client.insert(data, account_id=200)

        # Verify the URL used
        call_args = mock_http.post.call_args
        assert '/insert/200/prometheus/api/v1/import/prometheus' in call_args[0][0]


def test_insert_with_account_id_on_single_config_raises_error():
    """Test that insert() with account_id raises error for single config."""
    reset_config()
    register_config(VMSingleConfig('http://localhost:8428', http_options=HttpClientOptions(timeout=1.0)))
    client = DatabaseClient()

    with patch.object(client, 'client') as mock_http:
        mock_http.post.return_value = {'status': 'ok'}

        # Insert with account_id should raise ValueError
        data = MetricsInsertData(query='metric_name{label="value"}', times=[1640995200], values=[42.0])
        with pytest.raises(ValueError, match="account_id parameter is only supported for VMClusterConfig"):
            client.insert(data, account_id=100)


@pytest.mark.asyncio
async def test_query_async_with_account_id_override():
    """Test query_async() with account_id override for cluster config."""
    reset_config()
    register_config(VMClusterConfig(
        vminsert_url='http://vminsert:8480',
        vmselect_url='http://vmselect:8481',
        vmstorage_url='http://vmstorage:8482',
        account_id=100,
        http_options=HttpClientOptions(timeout=1.0)
    ))
    client = DatabaseClient()

    with patch.object(client, 'async_client') as mock_http:
        async def mock_get(url, params=None):
            return {'status': 'success', 'data': {'resultType': 'vector', 'result': []}}

        mock_http.get = mock_get

        # Query async with account_id override
        result = await client.query_async('up', account_id=200)
        assert result.is_success


@pytest.mark.asyncio
async def test_query_range_async_with_account_id_override():
    """Test query_range_async() with account_id override for cluster config."""
    reset_config()
    register_config(VMClusterConfig(
        vminsert_url='http://vminsert:8480',
        vmselect_url='http://vmselect:8481',
        vmstorage_url='http://vmstorage:8482',
        account_id=100,
        http_options=HttpClientOptions(timeout=1.0)
    ))
    client = DatabaseClient()

    with patch.object(client, 'async_client') as mock_http:
        async def mock_get(url, params=None):
            return {'status': 'success', 'data': {'resultType': 'matrix', 'result': []}}

        mock_http.get = mock_get

        # Query range async with account_id override
        result = await client.query_range_async('up', start=1640995200, end=1640998800, account_id=200)
        assert result.is_success


@pytest.mark.asyncio
async def test_insert_async_with_account_id_override():
    """Test insert_async() with account_id override for cluster config."""
    reset_config()
    register_config(VMClusterConfig(
        vminsert_url='http://vminsert:8480',
        vmselect_url='http://vmselect:8481',
        vmstorage_url='http://vmstorage:8482',
        account_id=100,
        http_options=HttpClientOptions(timeout=1.0)
    ))
    client = DatabaseClient()

    with patch.object(client, 'async_client') as mock_http:
        async def mock_post(url, data=None, params=None):
            return {'status': 'ok'}

        mock_http.post = mock_post

        # Insert async with account_id override
        data = MetricsInsertData(query='metric_name{label="value"}', times=[1640995200], values=[42.0])
        result = await client.insert_async(data, account_id=200)
        assert result['status'] == 'ok'


def test_prometheus_config_does_not_support_account_id():
    """Test that PrometheusConfig doesn't support account_id."""
    reset_config()
    register_config(PrometheusConfig('http://localhost:9090', http_options=HttpClientOptions(timeout=1.0)))
    client = DatabaseClient()

    with patch.object(client, 'client') as mock_http:
        mock_http.get.return_value = {'status': 'success', 'data': {'resultType': 'vector', 'result': []}}

        # PrometheusConfig is type 'prometheus', not 'cluster', so account_id should fail
        with pytest.raises(ValueError, match="account_id parameter is only supported for VMClusterConfig"):
            client.query('up', account_id=100)
