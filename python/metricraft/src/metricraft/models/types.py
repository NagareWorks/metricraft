"""Time inputs accepted by HTTP queries and ingestion payloads."""
from datetime import datetime
from typing import Union


TimeValue = Union[int, float, str, datetime, None]
