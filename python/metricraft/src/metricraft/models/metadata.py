"""Series and label metadata returned by Prometheus-compatible HTTP endpoints."""
from __future__ import annotations

from typing import Any, Dict, List, Optional


class MetadataResult(object):
    """
    Base class for metadata query results.

    All metadata queries return responses in the format:
        {
            "status": "success" | "error",
            "data": [...] | {"error": "..."},
            "errorType": "..." (only on error),
            "error": "..." (only on error)
        }
    """

    def __init__(self, status, data=None, error=None, error_type=None):
        # type: (str, Optional[Any], Optional[str], Optional[str]) -> None
        """
        Initialize metadata result.

        Args:
            status: Query status ("success" or "error")
            data: Result data (format depends on query type)
            error: Error message (only if status is "error")
            error_type: Error type (only if status is "error")
        """
        self._status = status
        self._data = data
        self._error = error
        self._error_type = error_type

    @property
    def status(self):
        # type: () -> str
        """Get query status."""
        return self._status

    @property
    def is_success(self):
        # type: () -> bool
        """Check if query was successful."""
        return self._status == 'success'

    @property
    def is_error(self):
        # type: () -> bool
        """Check if query resulted in error."""
        return self._status == 'error'

    @property
    def data(self):
        # type: () -> Any
        """Get result data."""
        return self._data

    @property
    def error(self):
        # type: () -> Optional[str]
        """Get error message if query failed."""
        return self._error

    @property
    def error_type(self):
        # type: () -> Optional[str]
        """Get error type if query failed."""
        return self._error_type

    def to_dict(self):
        # type: () -> Dict[str, Any]
        """Convert result to dictionary."""
        result = {'status': self._status}
        if self.is_success:
            result['data'] = self._data
        else:
            result['error'] = self._error
            if self._error_type:
                result['errorType'] = self._error_type
        return result

    @classmethod
    def from_dict(cls, response):
        # type: (Dict[str, Any]) -> MetadataResult
        """
        Create MetadataResult from API response dictionary.

        Args:
            response: API response dictionary

        Returns:
            MetadataResult instance
        """
        status = response.get('status', 'error')
        data = response.get('data')
        error = response.get('error')
        error_type = response.get('errorType')

        return cls(
            status=status,
            data=data,
            error=error,
            error_type=error_type
        )

    def __repr__(self):
        # type: () -> str
        """String representation of result."""
        if self.is_success:
            return "MetadataResult(status='success', data_len={0})".format(
                len(self._data) if self._data else 0
            )
        else:
            return "MetadataResult(status='error', error='{0}')".format(self._error)


class SeriesResult(MetadataResult):
    """
    Result for /api/v1/series query.

    Returns list of series with their label sets.

    Example response:
        {
            "status": "success",
            "data": [
                {"__name__": "up", "job": "prometheus", "instance": "localhost:9090"},
                {"__name__": "up", "job": "node", "instance": "localhost:9091"}
            ]
        }
    """

    @property
    def series(self):
        # type: () -> List[Dict[str, str]]
        """
        Get list of series label sets.

        Returns:
            List of dictionaries, each containing label name-value pairs
        """
        if self.is_success and self._data:
            return self._data
        return []

    def __repr__(self):
        # type: () -> str
        """String representation."""
        if self.is_success:
            return "SeriesResult(status='success', series_count={0})".format(len(self.series))
        else:
            return "SeriesResult(status='error', error='{0}')".format(self._error)


class LabelsResult(MetadataResult):
    """
    Result for /api/v1/labels query.

    Returns list of label names.

    Example response:
        {
            "status": "success",
            "data": ["__name__", "job", "instance", "code"]
        }
    """

    @property
    def labels(self):
        # type: () -> List[str]
        """
        Get list of label names.

        Returns:
            List of label name strings
        """
        if self.is_success and self._data:
            return self._data
        return []

    def __repr__(self):
        # type: () -> str
        """String representation."""
        if self.is_success:
            return "LabelsResult(status='success', label_count={0})".format(len(self.labels))
        else:
            return "LabelsResult(status='error', error='{0}')".format(self._error)


class LabelValuesResult(MetadataResult):
    """
    Result for /api/v1/label/<label_name>/values query.

    Returns list of values for a specific label.

    Example response:
        {
            "status": "success",
            "data": ["200", "404", "500"]
        }
    """

    @property
    def values(self):
        # type: () -> List[str]
        """
        Get list of label values.

        Returns:
            List of label value strings
        """
        if self.is_success and self._data:
            return self._data
        return []

    def __repr__(self):
        # type: () -> str
        """String representation."""
        if self.is_success:
            return "LabelValuesResult(status='success', value_count={0})".format(len(self.values))
        else:
            return "LabelValuesResult(status='error', error='{0}')".format(self._error)
