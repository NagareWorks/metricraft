"""
HTTP client exceptions for time series databases.
"""

from typing import Dict, Optional
from .core import MetriCraftError


class MCHTTPError(MetriCraftError):
    """Base HTTP error for time series database APIs."""

    def __init__(self, status_code: int, message: str, response_data: Optional[Dict] = None):
        self.status_code = status_code
        self.message = message
        self.response_data = response_data or {}
        super().__init__(f"HTTP {status_code}: {message}")


class TimeoutError(MetriCraftError):
    """Timeout error for time series database requests."""
    pass


class ConnectionError(MetriCraftError):
    """Connection error for time series database requests."""
    pass
