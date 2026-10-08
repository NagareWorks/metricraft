"""Prometheus and VictoriaMetrics query responses."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

@dataclass(frozen=True)
class MetricsQueryResult:
    """
    Query response shared by Prometheus and VictoriaMetrics.
    
    Field Categories:
        Standard fields (common across Prometheus ecosystem):
            - status: Query execution status
            - data: Query result data (resultType and result)
            - error: Error message for failed queries
            - warnings: Optional warning messages
        
        Implementation-specific fields:
            - isPartial: [VM-specific] Partial response indicator (due to sample limit)
            - stats: [VM-specific] Detailed execution statistics
            - trace: [VM-specific] Debug tracing information
            - error_type: Specific error categorization
    
    Attributes:
        status: "success" or "error"
        data: Nested data object containing resultType and result
        error: Error message (if status is "error")
        error_type: Error classification (bad_data, timeout, execution, internal)
        is_partial: [VM-specific] Whether response is partial due to sample limit
        stats: [VM-specific] Query statistics (seriesFetched, executionTimeMsec)
        warnings: Optional warning messages
        trace: [VM-specific] Trace information (when trace=1 parameter is used)
    """

    _status: str
    _data: Optional[Dict[str, Any]] = None
    _error: Optional[str] = None
    _error_type: Optional[str] = None
    _is_partial: Optional[bool] = None
    _stats: Optional[Dict[str, Any]] = None
    _warnings: Optional[List[str]] = None
    _trace: Optional[Dict[str, Any]] = None

    # Response status
    @property
    def status(self) -> str:
        """Query status: 'success' or 'error'."""
        return self._status

    @property
    def error(self) -> Optional[str]:
        """Error message if query failed."""
        return self._error

    @property
    def error_type(self) -> Optional[str]:
        """Error type: 'bad_data', 'timeout', 'execution', or 'internal'."""
        return self._error_type

    @property
    def is_success(self) -> bool:
        """Check if query was successful."""
        return self._status == "success"

    @property
    def is_error(self) -> bool:
        """Check if query had an error."""
        return self._status == "error"

    # Data accessors
    @property
    def data(self) -> Optional[Dict[str, Any]]:
        """Data object containing resultType and result."""
        return self._data

    @property
    def result_type(self) -> Optional[str]:
        """Result type: 'vector', 'matrix', 'scalar', or 'string'."""
        if self._data:
            return self._data.get("resultType")
        return None

    @property
    def result(self) -> Union[List[Dict[str, Any]], List[Any], None]:
        """
        Query result data.
        
        Format depends on resultType:
        - vector: [{ "metric": {...}, "value": [timestamp, "value"] }]
        - matrix: [{ "metric": {...}, "values": [[timestamp, "value"], ...] }]
        - scalar: [timestamp, "value"]
        - string: [timestamp, "string value"]
        """
        if self._data:
            return self._data.get("result")
        return None

    @property
    def is_partial(self) -> bool:
        """
        [VM-specific] Check if response is partial.
        
        VictoriaMetrics may return partial results when number of samples
        exceeds configured limits (e.g., -search.maxSamplesPerQuery).
        
        Returns:
            True if response is partial, False otherwise.
        """
        return self._is_partial or False

    @property
    def stats(self) -> Optional[Dict[str, Any]]:
        """
        [VM-specific] Query execution statistics.
        
        Contains:
        - seriesFetched: Number of series fetched (string or int)
        - executionTimeMsec: Execution time in milliseconds
        
        Note: Returns None for Prometheus and other implementations.
        """
        return self._stats

    @property
    def warnings(self) -> Optional[List[str]]:
        """Optional warning messages from query execution."""
        return self._warnings

    @property
    def trace(self) -> Optional[Dict[str, Any]]:
        """
        [VM-specific] Query execution trace (available when trace=1 parameter is used).
        
        Contains:
        - duration_msec: Duration in milliseconds
        - message: Trace message
        - children: Nested trace steps
        
        Note: Returns None for Prometheus and other implementations.
        """
        return self._trace

    # Convenience accessors for stats
    @property
    def execution_time_ms(self) -> Optional[float]:
        """[VM-specific] Execution time in milliseconds (from stats.executionTimeMsec)."""
        if self._stats:
            return self._stats.get("executionTimeMsec")
        return None

    @property
    def series_fetched(self) -> Optional[Union[int, str]]:
        """[VM-specific] Number of series fetched (from stats.seriesFetched)."""
        if self._stats:
            return self._stats.get("seriesFetched")
        return None

    # Friendly representation with complete response
    def __repr__(self) -> str:
        if self.is_error:
            return (
                "MetricsQueryResult("
                f"status={self.status!r}, "
                f"errorType={self.error_type!r}, "
                f"error={self.error!r}"
                ")"
            )
        
        # Build complete representation for success responses
        parts = [f"status={self.status!r}"]
        
        if self._data is not None:
            parts.append(f"data={self._data!r}")
        
        if self._is_partial is not None:
            parts.append(f"isPartial={self._is_partial!r}")
        
        if self._stats is not None:
            parts.append(f"stats={self._stats!r}")
        
        if self._warnings is not None:
            parts.append(f"warnings={self._warnings!r}")
        
        if self._trace is not None:
            parts.append(f"trace={self._trace!r}")
        
        return f"MetricsQueryResult({', '.join(parts)})"

    def to_dict(self) -> Dict[str, Any]:
        """
        Return complete response as a dictionary matching Prometheus API format.
        
        Returns a dict that matches Prometheus/VictoriaMetrics API response,
        which can be serialized to JSON for API responses or testing.
        """
        result: Dict[str, Any] = {"status": self.status}
        
        if self.is_success:
            if self._data is not None:
                result["data"] = self._data
            if self._is_partial is not None:
                result["isPartial"] = self._is_partial
            if self._stats is not None:
                result["stats"] = self._stats
            if self._warnings is not None:
                result["warnings"] = self._warnings
            if self._trace is not None:
                result["trace"] = self._trace
        else:
            if self._error is not None:
                result["error"] = self._error
            if self._error_type is not None:
                result["errorType"] = self._error_type
        
        return result

    @classmethod
    def from_dict(cls, response_data: Dict[str, Any]) -> 'MetricsQueryResult':
        """
        Create MetricsQueryResult from API response dictionary.
        
        Parses standard Prometheus/VictoriaMetrics API response format
        and creates a structured result object.
        
        Args:
            response_data: Raw response from API in format:
                Success: {"status": "success", "data": {...}, "stats": {...}}
                Error: {"status": "error", "errorType": "...", "error": "..."}
            
        Returns:
            MetricsQueryResult instance with parsed data
            
        Examples:
            >>> response = {
            ...     "status": "success",
            ...     "data": {
            ...         "resultType": "vector",
            ...         "result": [{"metric": {...}, "value": [123, "1"]}]
            ...     },
            ...     "stats": {"executionTimeMsec": 15, "seriesFetched": "100"}
            ... }
            >>> result = MetricsQueryResult.from_dict(response)
            >>> result.is_success
            True
            >>> result.result_type
            'vector'
        """
        status = response_data.get("status", "unknown")
        
        # For success responses, extract data and stats
        if status == "success":
            return cls(
                _status=status,
                _data=response_data.get("data"),
                _is_partial=response_data.get("isPartial"),
                _stats=response_data.get("stats"),
                _warnings=response_data.get("warnings"),
                _trace=response_data.get("trace"),
            )
        
        # For error responses
        return cls(
            _status=status,
            _error=response_data.get("error"),
            _error_type=response_data.get("errorType"),
        )
