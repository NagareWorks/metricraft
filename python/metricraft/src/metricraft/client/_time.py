"""Timestamp units at the query and Prometheus exposition boundaries."""
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional
import time

from metricraft.models import TimeValue


def _numeric_seconds(value) -> Decimal:
    number = Decimal(str(value))
    if not number.is_finite():
        raise ValueError("Timestamp must be finite")
    return number / 1000 if abs(number) > Decimal("1e10") else number


def epoch_seconds(value: TimeValue) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, str):
        try:
            return float(_numeric_seconds(value))
        except InvalidOperation:
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
            except ValueError as exc:
                raise ValueError("Provide start explicitly when end is not an absolute timestamp") from exc
    if isinstance(value, datetime):
        return value.timestamp()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(_numeric_seconds(value))
    raise ValueError("Unsupported time format: " + str(type(value)))


def query_time(value: TimeValue) -> Optional[str]:
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, datetime):
        number = Decimal(str(value.timestamp()))
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        number = _numeric_seconds(value)
    else:
        raise ValueError("Unsupported time format: " + str(type(value)))
    return str(int(number)) if number == number.to_integral_value() else format(number, "f")


def ingestion_milliseconds(value: TimeValue) -> int:
    """Accept epoch seconds/milliseconds or absolute ISO timestamps; emit milliseconds."""
    if isinstance(value, str):
        try:
            seconds = _numeric_seconds(value)
        except InvalidOperation:
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError("Ingestion requires an absolute timestamp") from exc
            seconds = Decimal(str(parsed.timestamp()))
    elif isinstance(value, datetime):
        seconds = Decimal(str(value.timestamp()))
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        seconds = _numeric_seconds(value)
    else:
        raise ValueError("Ingestion requires an absolute timestamp")
    return int(seconds * 1000)


def range_bounds(start: TimeValue, end: TimeValue):
    """Default to the preceding hour without rewriting explicit backend time strings."""
    if end is None:
        end = int(time.time())
    if start is None:
        start = epoch_seconds(end) - 3600
    return start, end
