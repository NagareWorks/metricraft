"""HTTP transport options for Prometheus and VictoriaMetrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Mapping, MutableMapping, Optional, Tuple, Union

HeadersMapping = Mapping[str, Union[str, int, float]]
TimeoutValue = Union[float, int]
TimeoutTuple = Tuple[TimeoutValue, TimeoutValue]
RawTimeout = Union[TimeoutValue, TimeoutTuple]


def _normalize_timeout(value: Optional[RawTimeout]) -> Optional[TimeoutTuple]:
    if value is None:
        return None
    if isinstance(value, (tuple, list)):
        if len(value) == 0:
            raise ValueError("Timeout tuple cannot be empty")
        if len(value) == 1:
            connect = read = float(value[0])
        else:
            connect = float(value[0])
            read = float(value[1])
    else:
        connect = read = float(value)

    if connect <= 0 or read <= 0:
        raise ValueError("Timeout values must be positive")
    return (connect, read)

_HEADER_CASE_OVERRIDES = {
    "Content-Type": "Content-type",
}


def _canonical_header_name(name: str) -> str:
    if not name:
        return name
    parts = str(name).split('-')
    canonical_parts = []
    for part in parts:
        if not part:
            canonical_parts.append(part)
            continue
        canonical_parts.append(part[0].upper() + part[1:])
    canonical = '-'.join(canonical_parts)
    return _HEADER_CASE_OVERRIDES.get(canonical, canonical)


def _normalize_headers(headers: Optional[HeadersMapping]) -> Dict[str, str]:
    if not headers:
        return {}
    materialized = dict(headers)
    normalized: Dict[str, str] = {}
    for key, value in materialized.items():
        canonical = _canonical_header_name(str(key))
        normalized[canonical] = str(value)
    return normalized


@dataclass(frozen=True)
class HttpClientOptions:
    """Typed container for HTTP client configuration."""

    timeout: Optional[TimeoutTuple] = None
    default_headers: Dict[str, str] = field(default_factory=dict)
    prepare_request: Optional[Callable[..., Any]] = None
    opener: Optional[Callable[..., Any]] = None
    client: Optional[Any] = None
    async_client: Optional[Any] = None
    client_factory: Optional[Callable[..., Any]] = None
    async_client_factory: Optional[Callable[..., Any]] = None
    max_workers: Optional[int] = None
    executor: Optional[Any] = None
    extras: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "timeout", _normalize_timeout(self.timeout))
        if self.max_workers is not None and self.max_workers <= 0:
            raise ValueError("max_workers must be positive when provided")
        object.__setattr__(self, "default_headers", _normalize_headers(self.default_headers))
        object.__setattr__(self, "extras", dict(self.extras))

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "HttpClientOptions":
        known_keys = {
            "timeout",
            "default_headers",
            "prepare_request",
            "opener",
            "client",
            "async_client",
            "client_factory",
            "async_client_factory",
            "max_workers",
            "executor",
        }

        materialized: MutableMapping[str, Any] = dict(data)

        # Alias support
        if "headers" in materialized and "default_headers" not in materialized:
            materialized["default_headers"] = materialized.pop("headers")

        extracted: Dict[str, Any] = {}
        for key in list(materialized.keys()):
            if key in known_keys:
                extracted[key] = materialized.pop(key)

        extras = dict(materialized)
        if 'extras' in extras:
            extras_value = extras.pop('extras')
            if isinstance(extras_value, Mapping):
                extras = {**extras, **dict(extras_value)}
            else:
                extras['extras'] = extras_value

        timeout = extracted.get("timeout")
        if isinstance(timeout, HttpClientOptions):
            timeout = timeout.timeout

        return cls(
            timeout=timeout,
            default_headers=_normalize_headers(extracted.get("default_headers")),
            prepare_request=extracted.get("prepare_request"),
            opener=extracted.get("opener"),
            client=extracted.get("client"),
            async_client=extracted.get("async_client"),
            client_factory=extracted.get("client_factory"),
            async_client_factory=extracted.get("async_client_factory"),
            max_workers=extracted.get("max_workers"),
            executor=extracted.get("executor"),
            extras=extras,
        )

    @classmethod
    def ensure(cls, value: Optional[Union["HttpClientOptions", Mapping[str, Any]]]) -> "HttpClientOptions":
        if value is None:
            return cls()
        if isinstance(value, HttpClientOptions):
            return value
        return cls.from_mapping(value)

    def merge(self, overrides: Optional[Union["HttpClientOptions", Mapping[str, Any]]]) -> "HttpClientOptions":
        if overrides is None:
            return self
        override_obj = HttpClientOptions.ensure(overrides)
        base_dict = self.to_dict()
        override_dict = override_obj.to_dict()

        merged_headers = {
            **base_dict.get("default_headers", {}),
            **override_dict.get("default_headers", {}),
        }

        merged = {**base_dict, **override_dict}
        if merged_headers:
            merged["default_headers"] = merged_headers

        # Merge extras explicitly
        merged_extras = {
            **base_dict.get("extras", {}),
            **override_dict.get("extras", {}),
        }
        if merged_extras:
            merged["extras"] = merged_extras

        return HttpClientOptions.from_mapping(merged)

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        if self.timeout is not None:
            data["timeout"] = self.timeout
        if self.default_headers:
            data["default_headers"] = dict(self.default_headers)
        if self.prepare_request is not None:
            data["prepare_request"] = self.prepare_request
        if self.opener is not None:
            data["opener"] = self.opener
        if self.client is not None:
            data["client"] = self.client
        if self.async_client is not None:
            data["async_client"] = self.async_client
        if self.client_factory is not None:
            data["client_factory"] = self.client_factory
        if self.async_client_factory is not None:
            data["async_client_factory"] = self.async_client_factory
        if self.max_workers is not None:
            data["max_workers"] = self.max_workers
        if self.executor is not None:
            data["executor"] = self.executor
        if self.extras:
            data["extras"] = dict(self.extras)
        return data
