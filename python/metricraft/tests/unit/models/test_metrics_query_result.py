"""Tests for MetricsQueryResult (Prometheus/PromQL ecosystem query result)."""

import pytest
from metricraft.models import MetricsQueryResult


def test_metrics_query_result_from_dict_success():
    """Test creating MetricsQueryResult from successful API response."""
    resp = {
        'status': 'success',
        'data': {
            'resultType': 'vector',
            'result': [
                {'metric': {'__name__': 'up'}, 'value': [1640995200, '1']}
            ]
        },
        'stats': {
            'executionTimeMsec': 12.3,
            'seriesFetched': '100'
        },
        'warnings': ['warning message']
    }
    
    result = MetricsQueryResult.from_dict(resp)
    
    assert result.is_success
    assert not result.is_error
    assert result.status == 'success'
    assert result.result_type == 'vector'
    assert result.execution_time_ms == 12.3
    assert result.series_fetched == '100'
    assert len(result.result) == 1
    assert result.warnings == ['warning message']
    
    # Test to_dict() round-trip
    d = result.to_dict()
    assert d['status'] == 'success'
    assert d['data']['resultType'] == 'vector'
    assert isinstance(d['data']['result'], list)
    assert d['stats']['executionTimeMsec'] == 12.3
    assert d['warnings'] == ['warning message']


def test_metrics_query_result_from_dict_error():
    """Test creating MetricsQueryResult from error response."""
    error_resp = {
        'status': 'error',
        'errorType': 'bad_data',
        'error': 'parse error'
    }
    
    result = MetricsQueryResult.from_dict(error_resp)
    
    assert result.is_error
    assert not result.is_success
    assert result.status == 'error'
    assert result.error == 'parse error'
    assert result.error_type == 'bad_data'
    
    # Test to_dict() for error response
    d = result.to_dict()
    assert d['status'] == 'error'
    assert d['errorType'] == 'bad_data'
    assert d['error'] == 'parse error'


def test_metrics_query_result_is_partial_field():
    """Test isPartial field (VM-specific)."""
    # Test isPartial=True
    resp_partial = {
        'status': 'success',
        'data': {
            'resultType': 'vector',
            'result': [
                {'metric': {'__name__': 'up'}, 'value': [1640995200, '1']}
            ]
        },
        'isPartial': True,
        'stats': {'executionTimeMsec': 15.3}
    }
    
    result = MetricsQueryResult.from_dict(resp_partial)
    
    assert result.is_partial is True
    assert 'isPartial=True' in repr(result)
    
    d = result.to_dict()
    assert 'isPartial' in d
    assert d['isPartial'] is True
    
    # Test isPartial=False
    resp_complete = {
        'status': 'success',
        'data': {
            'resultType': 'vector',
            'result': []
        },
        'isPartial': False
    }
    
    result_complete = MetricsQueryResult.from_dict(resp_complete)
    assert result_complete.is_partial is False
    
    # Test isPartial not present (default to False)
    resp_no_partial = {
        'status': 'success',
        'data': {
            'resultType': 'vector',
            'result': []
        }
    }
    
    result_no_partial = MetricsQueryResult.from_dict(resp_no_partial)
    assert result_no_partial.is_partial is False
    
    # Verify to_dict() doesn't include isPartial when None
    d_no_partial = result_no_partial.to_dict()
    assert 'isPartial' not in d_no_partial


def test_metrics_query_result_trace_field():
    """Test trace field (VM-specific)."""
    resp_with_trace = {
        'status': 'success',
        'data': {
            'resultType': 'vector',
            'result': []
        },
        'trace': {
            'duration_msec': 10.5,
            'message': 'test trace',
            'children': []
        }
    }
    
    result = MetricsQueryResult.from_dict(resp_with_trace)
    
    assert result.trace is not None
    assert result.trace['duration_msec'] == 10.5
    assert result.trace['message'] == 'test trace'
    
    d = result.to_dict()
    assert 'trace' in d
    assert d['trace']['duration_msec'] == 10.5


def test_metrics_query_result_all_result_types():
    """Test different result types: vector, matrix, scalar, string."""
    # Vector
    vector_resp = {
        'status': 'success',
        'data': {
            'resultType': 'vector',
            'result': [
                {'metric': {'job': 'api'}, 'value': [1234567890, '42']}
            ]
        }
    }
    vector_result = MetricsQueryResult.from_dict(vector_resp)
    assert vector_result.result_type == 'vector'
    assert len(vector_result.result) == 1
    
    # Matrix
    matrix_resp = {
        'status': 'success',
        'data': {
            'resultType': 'matrix',
            'result': [
                {
                    'metric': {'job': 'api'},
                    'values': [[1234567890, '42'], [1234567900, '43']]
                }
            ]
        }
    }
    matrix_result = MetricsQueryResult.from_dict(matrix_resp)
    assert matrix_result.result_type == 'matrix'
    assert len(matrix_result.result[0]['values']) == 2
    
    # Scalar
    scalar_resp = {
        'status': 'success',
        'data': {
            'resultType': 'scalar',
            'result': [1234567890, '3.14']
        }
    }
    scalar_result = MetricsQueryResult.from_dict(scalar_resp)
    assert scalar_result.result_type == 'scalar'
    assert scalar_result.result[1] == '3.14'
    
    # String
    string_resp = {
        'status': 'success',
        'data': {
            'resultType': 'string',
            'result': [1234567890, 'test string']
        }
    }
    string_result = MetricsQueryResult.from_dict(string_resp)
    assert string_result.result_type == 'string'
    assert string_result.result[1] == 'test string'


def test_metrics_query_result_repr():
    """Test __repr__ method for both success and error cases."""
    # Success case
    success_resp = {
        'status': 'success',
        'data': {
            'resultType': 'vector',
            'result': []
        },
        'isPartial': True,
        'stats': {'executionTimeMsec': 10}
    }
    result = MetricsQueryResult.from_dict(success_resp)
    repr_str = repr(result)
    
    assert 'MetricsQueryResult(' in repr_str
    assert "status='success'" in repr_str
    assert 'isPartial=True' in repr_str
    assert 'stats=' in repr_str
    
    # Error case
    error_resp = {
        'status': 'error',
        'errorType': 'timeout',
        'error': 'query timeout'
    }
    error_result = MetricsQueryResult.from_dict(error_resp)
    error_repr = repr(error_result)
    
    assert 'MetricsQueryResult(' in error_repr
    assert "status='error'" in error_repr
    assert "errorType='timeout'" in error_repr
    assert "error='query timeout'" in error_repr


def test_metrics_query_result_optional_fields():
    """Test that optional fields return None when not present."""
    minimal_resp = {
        'status': 'success',
        'data': {
            'resultType': 'vector',
            'result': []
        }
    }
    
    result = MetricsQueryResult.from_dict(minimal_resp)
    
    assert result.stats is None
    assert result.warnings is None
    assert result.trace is None
    assert result.execution_time_ms is None
    assert result.series_fetched is None
    assert result.is_partial is False  # Default to False


def test_metrics_query_result_error_properties():
    """Test error-related properties."""
    error_resp = {
        'status': 'error',
        'errorType': 'execution',
        'error': 'out of memory'
    }
    
    result = MetricsQueryResult.from_dict(error_resp)
    
    assert result.error == 'out of memory'
    assert result.error_type == 'execution'
    assert result.data is None
    assert result.result is None
    assert result.result_type is None
