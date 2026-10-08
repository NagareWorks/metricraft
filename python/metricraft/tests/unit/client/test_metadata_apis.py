"""Tests for metadata API methods (series, labels, label_values)."""

import pytest

try:
    from unittest.mock import patch
except ImportError:  # pragma: no cover - Python 2 fallback
    from mock import patch  # type: ignore

from metricraft import register_config, DatabaseClient, QueryBuilder
from metricraft.config import reset_config
from metricraft.config.http_options import HttpClientOptions
from metricraft.config import VMSingleConfig, VMClusterConfig


def test_series_with_single_match():
    """Test series() with single match selector."""
    reset_config()
    register_config(VMSingleConfig('http://localhost:8428', http_options=HttpClientOptions(timeout=1.0)))
    client = DatabaseClient()

    with patch.object(client, 'client') as mock_http:
        mock_http.get.return_value = {
            'status': 'success',
            'data': [
                {'__name__': 'up', 'job': 'prometheus', 'instance': 'localhost:9090'},
                {'__name__': 'up', 'job': 'node', 'instance': 'localhost:9091'}
            ]
        }

        result = client.series('up')

        assert result.is_success
        assert len(result.series) == 2
        assert result.series[0]['__name__'] == 'up'
        assert result.series[0]['job'] == 'prometheus'

        # Verify URL and params
        call_args = mock_http.get.call_args
        assert '/api/v1/series' in call_args[0][0]
        assert call_args[1]['params']['match[]'] == ['up']


def test_series_with_query_builder():
    """Test series() with QueryBuilder instance."""
    reset_config()
    register_config(VMSingleConfig('http://localhost:8428', http_options=HttpClientOptions(timeout=1.0)))
    client = DatabaseClient()

    with patch.object(client, 'client') as mock_http:
        mock_http.get.return_value = {
            'status': 'success',
            'data': [{'__name__': 'cpu_usage', 'job': 'api'}]
        }

        qb = QueryBuilder().from_metric('cpu_usage').where_eq('job', 'api')
        result = client.series(qb)

        assert result.is_success
        # QueryBuilder should be converted to string
        call_args = mock_http.get.call_args
        assert 'cpu_usage' in call_args[1]['params']['match[]'][0]


def test_series_with_list_of_matches():
    """Test series() with list of match selectors."""
    reset_config()
    register_config(VMSingleConfig('http://localhost:8428', http_options=HttpClientOptions(timeout=1.0)))
    client = DatabaseClient()

    with patch.object(client, 'client') as mock_http:
        mock_http.get.return_value = {
            'status': 'success',
            'data': [
                {'__name__': 'up'},
                {'__name__': 'process_cpu_seconds_total'}
            ]
        }

        result = client.series(['up', 'process_cpu_seconds_total'])

        assert result.is_success
        assert len(result.series) == 2

        call_args = mock_http.get.call_args
        assert call_args[1]['params']['match[]'] == ['up', 'process_cpu_seconds_total']


def test_series_with_time_range_and_limit():
    """Test series() with time range and limit parameters."""
    reset_config()
    register_config(VMSingleConfig('http://localhost:8428', http_options=HttpClientOptions(timeout=1.0)))
    client = DatabaseClient()

    with patch.object(client, 'client') as mock_http:
        mock_http.get.return_value = {'status': 'success', 'data': []}

        result = client.series('up', start=1640995200, end=1640998800, limit=100)

        assert result.is_success

        call_args = mock_http.get.call_args
        params = call_args[1]['params']
        assert params['start'] == '1640995200'
        assert params['end'] == '1640998800'
        assert params['limit'] == '100'


def test_series_with_account_id_cluster():
    """Test series() with account_id for cluster config."""
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
        mock_http.get.return_value = {'status': 'success', 'data': []}

        result = client.series('up', account_id=200)

        assert result.is_success

        call_args = mock_http.get.call_args
        assert '/select/200/prometheus/api/v1/series' in call_args[0][0]


def test_labels_without_filters():
    """Test labels() without any filters."""
    reset_config()
    register_config(VMSingleConfig('http://localhost:8428', http_options=HttpClientOptions(timeout=1.0)))
    client = DatabaseClient()

    with patch.object(client, 'client') as mock_http:
        mock_http.get.return_value = {
            'status': 'success',
            'data': ['__name__', 'job', 'instance', 'code']
        }

        result = client.labels()

        assert result.is_success
        assert len(result.labels) == 4
        assert '__name__' in result.labels
        assert 'job' in result.labels

        call_args = mock_http.get.call_args
        assert '/api/v1/labels' in call_args[0][0]


def test_labels_with_match_filter():
    """Test labels() with match filter."""
    reset_config()
    register_config(VMSingleConfig('http://localhost:8428', http_options=HttpClientOptions(timeout=1.0)))
    client = DatabaseClient()

    with patch.object(client, 'client') as mock_http:
        mock_http.get.return_value = {
            'status': 'success',
            'data': ['__name__', 'job', 'instance']
        }

        result = client.labels(match='up{job="api"}')

        assert result.is_success

        call_args = mock_http.get.call_args
        params = call_args[1]['params']
        assert params['match[]'] == ['up{job="api"}']


def test_labels_with_time_range_and_limit():
    """Test labels() with time range and limit."""
    reset_config()
    register_config(VMSingleConfig('http://localhost:8428', http_options=HttpClientOptions(timeout=1.0)))
    client = DatabaseClient()

    with patch.object(client, 'client') as mock_http:
        mock_http.get.return_value = {'status': 'success', 'data': ['__name__']}

        result = client.labels(start=1640995200, end=1640998800, limit=50)

        assert result.is_success

        call_args = mock_http.get.call_args
        params = call_args[1]['params']
        assert params['start'] == '1640995200'
        assert params['end'] == '1640998800'
        assert params['limit'] == '50'


def test_label_values_basic():
    """Test label_values() basic usage."""
    reset_config()
    register_config(VMSingleConfig('http://localhost:8428', http_options=HttpClientOptions(timeout=1.0)))
    client = DatabaseClient()

    with patch.object(client, 'client') as mock_http:
        mock_http.get.return_value = {
            'status': 'success',
            'data': ['200', '404', '500']
        }

        result = client.label_values('code')

        assert result.is_success
        assert len(result.values) == 3
        assert '200' in result.values
        assert '404' in result.values

        call_args = mock_http.get.call_args
        assert '/api/v1/label/code/values' in call_args[0][0]


def test_label_values_with_match_filter():
    """Test label_values() with match filter."""
    reset_config()
    register_config(VMSingleConfig('http://localhost:8428', http_options=HttpClientOptions(timeout=1.0)))
    client = DatabaseClient()

    with patch.object(client, 'client') as mock_http:
        mock_http.get.return_value = {
            'status': 'success',
            'data': ['prometheus', 'node']
        }

        qb = QueryBuilder().from_metric('up')
        result = client.label_values('job', match=qb)

        assert result.is_success
        assert result.values == ['prometheus', 'node']

        call_args = mock_http.get.call_args
        params = call_args[1]['params']
        assert 'match[]' in params


def test_label_values_with_time_range():
    """Test label_values() with time range."""
    reset_config()
    register_config(VMSingleConfig('http://localhost:8428', http_options=HttpClientOptions(timeout=1.0)))
    client = DatabaseClient()

    with patch.object(client, 'client') as mock_http:
        mock_http.get.return_value = {'status': 'success', 'data': ['api', 'web']}

        result = client.label_values('job', start=1640995200, end=1640998800, limit=10)

        assert result.is_success

        call_args = mock_http.get.call_args
        params = call_args[1]['params']
        assert params['start'] == '1640995200'
        assert params['end'] == '1640998800'
        assert params['limit'] == '10'


def test_metadata_error_response():
    """Test metadata queries with error response."""
    reset_config()
    register_config(VMSingleConfig('http://localhost:8428', http_options=HttpClientOptions(timeout=1.0)))
    client = DatabaseClient()

    with patch.object(client, 'client') as mock_http:
        mock_http.get.return_value = {
            'status': 'error',
            'errorType': 'bad_data',
            'error': 'invalid selector'
        }

        result = client.series('invalid{')

        assert result.is_error
        assert not result.is_success
        assert result.error == 'invalid selector'
        assert result.error_type == 'bad_data'


def test_series_with_custom_params():
    """Test series() with custom parameters."""
    reset_config()
    register_config(VMSingleConfig('http://localhost:8428', http_options=HttpClientOptions(timeout=1.0)))
    client = DatabaseClient()

    with patch.object(client, 'client') as mock_http:
        mock_http.get.return_value = {'status': 'success', 'data': []}

        result = client.series('up', custom_params={'extra': 'value'})

        assert result.is_success

        call_args = mock_http.get.call_args
        params = call_args[1]['params']
        assert params['extra'] == 'value'


def test_metadata_result_to_dict():
    """Test MetadataResult to_dict() method."""
    reset_config()
    register_config(VMSingleConfig('http://localhost:8428', http_options=HttpClientOptions(timeout=1.0)))
    client = DatabaseClient()

    with patch.object(client, 'client') as mock_http:
        mock_http.get.return_value = {
            'status': 'success',
            'data': ['label1', 'label2']
        }

        result = client.labels()
        result_dict = result.to_dict()

        assert result_dict['status'] == 'success'
        assert result_dict['data'] == ['label1', 'label2']


def test_metadata_result_repr():
    """Test MetadataResult __repr__() methods."""
    reset_config()
    register_config(VMSingleConfig('http://localhost:8428', http_options=HttpClientOptions(timeout=1.0)))
    client = DatabaseClient()

    with patch.object(client, 'client') as mock_http:
        # Test SeriesResult repr
        mock_http.get.return_value = {
            'status': 'success',
            'data': [{'__name__': 'up'}, {'__name__': 'down'}]
        }
        series_result = client.series('up')
        repr_str = repr(series_result)
        assert 'SeriesResult' in repr_str
        assert 'series_count=2' in repr_str

        # Test LabelsResult repr
        mock_http.get.return_value = {
            'status': 'success',
            'data': ['label1', 'label2', 'label3']
        }
        labels_result = client.labels()
        repr_str = repr(labels_result)
        assert 'LabelsResult' in repr_str
        assert 'label_count=3' in repr_str

        # Test LabelValuesResult repr
        mock_http.get.return_value = {
            'status': 'success',
            'data': ['val1', 'val2']
        }
        values_result = client.label_values('job')
        repr_str = repr(values_result)
        assert 'LabelValuesResult' in repr_str
        assert 'value_count=2' in repr_str

        # Test error result repr
        mock_http.get.return_value = {
            'status': 'error',
            'error': 'test error'
        }
        error_result = client.series('bad')
        repr_str = repr(error_result)
        assert 'error=' in repr_str
        assert 'test error' in repr_str


# Async tests
@pytest.mark.asyncio
async def test_series_async():
    """Test series_async() method."""
    reset_config()
    register_config(VMSingleConfig('http://localhost:8428', http_options=HttpClientOptions(timeout=1.0)))
    client = DatabaseClient()

    with patch.object(client, 'async_client') as mock_async:
        async def mock_get(url, params=None):
            return {
                'status': 'success',
                'data': [{'__name__': 'up', 'job': 'api'}]
            }

        mock_async.get = mock_get

        result = await client.series_async('up')

        assert result.is_success
        assert len(result.series) == 1


@pytest.mark.asyncio
async def test_labels_async():
    """Test labels_async() method."""
    reset_config()
    register_config(VMSingleConfig('http://localhost:8428', http_options=HttpClientOptions(timeout=1.0)))
    client = DatabaseClient()

    with patch.object(client, 'async_client') as mock_async:
        async def mock_get(url, params=None):
            return {
                'status': 'success',
                'data': ['__name__', 'job', 'instance']
            }

        mock_async.get = mock_get

        result = await client.labels_async()

        assert result.is_success
        assert len(result.labels) == 3
        assert 'job' in result.labels


@pytest.mark.asyncio
async def test_label_values_async():
    """Test label_values_async() method."""
    reset_config()
    register_config(VMSingleConfig('http://localhost:8428', http_options=HttpClientOptions(timeout=1.0)))
    client = DatabaseClient()

    with patch.object(client, 'async_client') as mock_async:
        async def mock_get(url, params=None):
            return {
                'status': 'success',
                'data': ['200', '404', '500']
            }

        mock_async.get = mock_get

        result = await client.label_values_async('code')

        assert result.is_success
        assert len(result.values) == 3
        assert '404' in result.values


@pytest.mark.asyncio
async def test_series_async_with_query_builder():
    """Test series_async() with QueryBuilder."""
    reset_config()
    register_config(VMClusterConfig(
        vminsert_url='http://vminsert:8480',
        vmselect_url='http://vmselect:8481',
        vmstorage_url='http://vmstorage:8482',
        http_options=HttpClientOptions(timeout=1.0)
    ))
    client = DatabaseClient()

    with patch.object(client, 'async_client') as mock_async:
        async def mock_get(url, params=None):
            return {'status': 'success', 'data': []}

        mock_async.get = mock_get

        qb = QueryBuilder().from_metric('cpu_usage')
        result = await client.series_async([qb, 'memory_usage'], account_id=100)

        assert result.is_success
