"""Tests for metadata result models."""

import pytest

from metricraft.models import MetadataResult, SeriesResult, LabelsResult, LabelValuesResult


def test_metadata_result_success():
    """Test MetadataResult with success status."""
    result = MetadataResult(
        status='success',
        data=[{'__name__': 'up', 'job': 'api'}]
    )

    assert result.status == 'success'
    assert result.is_success
    assert not result.is_error
    assert result.data == [{'__name__': 'up', 'job': 'api'}]
    assert result.error is None
    assert result.error_type is None


def test_metadata_result_error():
    """Test MetadataResult with error status."""
    result = MetadataResult(
        status='error',
        error='invalid query',
        error_type='bad_data'
    )

    assert result.status == 'error'
    assert not result.is_success
    assert result.is_error
    assert result.error == 'invalid query'
    assert result.error_type == 'bad_data'
    assert result.data is None


def test_metadata_result_to_dict_success():
    """Test MetadataResult.to_dict() for success."""
    result = MetadataResult(
        status='success',
        data=['label1', 'label2']
    )

    result_dict = result.to_dict()

    assert result_dict['status'] == 'success'
    assert result_dict['data'] == ['label1', 'label2']
    assert 'error' not in result_dict
    assert 'errorType' not in result_dict


def test_metadata_result_to_dict_error():
    """Test MetadataResult.to_dict() for error."""
    result = MetadataResult(
        status='error',
        error='timeout',
        error_type='timeout'
    )

    result_dict = result.to_dict()

    assert result_dict['status'] == 'error'
    assert result_dict['error'] == 'timeout'
    assert result_dict['errorType'] == 'timeout'
    assert 'data' not in result_dict


def test_metadata_result_from_dict_success():
    """Test MetadataResult.from_dict() for success."""
    response = {
        'status': 'success',
        'data': [{'metric': 'value'}]
    }

    result = MetadataResult.from_dict(response)

    assert result.status == 'success'
    assert result.is_success
    assert result.data == [{'metric': 'value'}]


def test_metadata_result_from_dict_error():
    """Test MetadataResult.from_dict() for error."""
    response = {
        'status': 'error',
        'error': 'parse error',
        'errorType': 'bad_data'
    }

    result = MetadataResult.from_dict(response)

    assert result.status == 'error'
    assert result.is_error
    assert result.error == 'parse error'
    assert result.error_type == 'bad_data'


def test_metadata_result_repr_success():
    """Test MetadataResult.__repr__() for success."""
    result = MetadataResult(
        status='success',
        data=['a', 'b', 'c']
    )

    repr_str = repr(result)

    assert 'MetadataResult' in repr_str
    assert "status='success'" in repr_str
    assert 'data_len=3' in repr_str


def test_metadata_result_repr_error():
    """Test MetadataResult.__repr__() for error."""
    result = MetadataResult(
        status='error',
        error='test error'
    )

    repr_str = repr(result)

    assert 'MetadataResult' in repr_str
    assert "status='error'" in repr_str
    assert 'test error' in repr_str


def test_metadata_result_repr_no_data():
    """Test MetadataResult.__repr__() with None data."""
    result = MetadataResult(status='success', data=None)

    repr_str = repr(result)

    assert 'data_len=0' in repr_str


def test_series_result_basic():
    """Test SeriesResult basic functionality."""
    result = SeriesResult(
        status='success',
        data=[
            {'__name__': 'up', 'job': 'prometheus', 'instance': 'localhost:9090'},
            {'__name__': 'up', 'job': 'node', 'instance': 'localhost:9091'}
        ]
    )

    assert result.is_success
    assert len(result.series) == 2
    assert result.series[0]['__name__'] == 'up'
    assert result.series[0]['job'] == 'prometheus'
    assert result.series[1]['job'] == 'node'


def test_series_result_empty():
    """Test SeriesResult with empty data."""
    result = SeriesResult(status='success', data=[])

    assert result.is_success
    assert result.series == []


def test_series_result_error():
    """Test SeriesResult with error."""
    result = SeriesResult(
        status='error',
        error='invalid selector'
    )

    assert result.is_error
    assert result.series == []


def test_series_result_repr_success():
    """Test SeriesResult.__repr__() for success."""
    result = SeriesResult(
        status='success',
        data=[{'__name__': 'up'}, {'__name__': 'down'}]
    )

    repr_str = repr(result)

    assert 'SeriesResult' in repr_str
    assert "status='success'" in repr_str
    assert 'series_count=2' in repr_str


def test_series_result_repr_error():
    """Test SeriesResult.__repr__() for error."""
    result = SeriesResult(
        status='error',
        error='bad selector'
    )

    repr_str = repr(result)

    assert 'SeriesResult' in repr_str
    assert "status='error'" in repr_str
    assert 'bad selector' in repr_str


def test_labels_result_basic():
    """Test LabelsResult basic functionality."""
    result = LabelsResult(
        status='success',
        data=['__name__', 'job', 'instance', 'code', 'handler']
    )

    assert result.is_success
    assert len(result.labels) == 5
    assert '__name__' in result.labels
    assert 'job' in result.labels
    assert 'instance' in result.labels


def test_labels_result_empty():
    """Test LabelsResult with empty data."""
    result = LabelsResult(status='success', data=[])

    assert result.is_success
    assert result.labels == []


def test_labels_result_error():
    """Test LabelsResult with error."""
    result = LabelsResult(
        status='error',
        error='query failed'
    )

    assert result.is_error
    assert result.labels == []


def test_labels_result_repr_success():
    """Test LabelsResult.__repr__() for success."""
    result = LabelsResult(
        status='success',
        data=['label1', 'label2', 'label3']
    )

    repr_str = repr(result)

    assert 'LabelsResult' in repr_str
    assert "status='success'" in repr_str
    assert 'label_count=3' in repr_str


def test_labels_result_repr_error():
    """Test LabelsResult.__repr__() for error."""
    result = LabelsResult(
        status='error',
        error='timeout'
    )

    repr_str = repr(result)

    assert 'LabelsResult' in repr_str
    assert "status='error'" in repr_str
    assert 'timeout' in repr_str


def test_label_values_result_basic():
    """Test LabelValuesResult basic functionality."""
    result = LabelValuesResult(
        status='success',
        data=['200', '404', '500', '502', '503']
    )

    assert result.is_success
    assert len(result.values) == 5
    assert '200' in result.values
    assert '404' in result.values
    assert '500' in result.values


def test_label_values_result_empty():
    """Test LabelValuesResult with empty data."""
    result = LabelValuesResult(status='success', data=[])

    assert result.is_success
    assert result.values == []


def test_label_values_result_error():
    """Test LabelValuesResult with error."""
    result = LabelValuesResult(
        status='error',
        error='label not found',
        error_type='not_found'
    )

    assert result.is_error
    assert result.values == []
    assert result.error == 'label not found'
    assert result.error_type == 'not_found'


def test_label_values_result_repr_success():
    """Test LabelValuesResult.__repr__() for success."""
    result = LabelValuesResult(
        status='success',
        data=['val1', 'val2']
    )

    repr_str = repr(result)

    assert 'LabelValuesResult' in repr_str
    assert "status='success'" in repr_str
    assert 'value_count=2' in repr_str


def test_label_values_result_repr_error():
    """Test LabelValuesResult.__repr__() for error."""
    result = LabelValuesResult(
        status='error',
        error='label error'
    )

    repr_str = repr(result)

    assert 'LabelValuesResult' in repr_str
    assert "status='error'" in repr_str
    assert 'label error' in repr_str


def test_series_result_from_dict():
    """Test SeriesResult.from_dict()."""
    response = {
        'status': 'success',
        'data': [
            {'__name__': 'cpu_usage', 'job': 'api'}
        ]
    }

    result = SeriesResult.from_dict(response)

    assert isinstance(result, SeriesResult)
    assert result.is_success
    assert len(result.series) == 1
    assert result.series[0]['__name__'] == 'cpu_usage'


def test_labels_result_from_dict():
    """Test LabelsResult.from_dict()."""
    response = {
        'status': 'success',
        'data': ['__name__', 'job']
    }

    result = LabelsResult.from_dict(response)

    assert isinstance(result, LabelsResult)
    assert result.is_success
    assert len(result.labels) == 2


def test_label_values_result_from_dict():
    """Test LabelValuesResult.from_dict()."""
    response = {
        'status': 'success',
        'data': ['prometheus', 'node', 'alertmanager']
    }

    result = LabelValuesResult.from_dict(response)

    assert isinstance(result, LabelValuesResult)
    assert result.is_success
    assert len(result.values) == 3
    assert 'prometheus' in result.values


def test_metadata_result_to_dict_without_error_type():
    """Test to_dict() when error_type is None."""
    result = MetadataResult(
        status='error',
        error='some error',
        error_type=None
    )

    result_dict = result.to_dict()

    assert result_dict['status'] == 'error'
    assert result_dict['error'] == 'some error'
    # errorType should not be in dict when None
    assert 'errorType' not in result_dict


def test_series_result_none_data():
    """Test SeriesResult with None data returns empty list."""
    result = SeriesResult(status='success', data=None)

    assert result.series == []


def test_labels_result_none_data():
    """Test LabelsResult with None data returns empty list."""
    result = LabelsResult(status='success', data=None)

    assert result.labels == []


def test_label_values_result_none_data():
    """Test LabelValuesResult with None data returns empty list."""
    result = LabelValuesResult(status='success', data=None)

    assert result.values == []
