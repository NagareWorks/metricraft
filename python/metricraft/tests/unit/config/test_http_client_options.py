"""Tests for HttpClientOptions container."""

from typing import Optional

import pytest

from metricraft.config.base import Config
from metricraft.config.http_options import HttpClientOptions
from metricraft.enums import DBType


def test_ensure_accepts_dict_and_normalizes_headers():
    options = HttpClientOptions.ensure({
        "timeout": 5,
        "default_headers": {"X": 1},
    })

    assert isinstance(options, HttpClientOptions)
    assert options.timeout == (5.0, 5.0)
    assert options.default_headers == {"X": "1"}


def test_ensure_accepts_instance():
    original = HttpClientOptions(timeout=(1, 2))
    ensured = HttpClientOptions.ensure(original)
    assert ensured is original


def test_merge_combines_values_and_headers():
    base = HttpClientOptions.ensure({
        "timeout": (1, 1),
        "default_headers": {"A": "1"},
        "extras": {"a": 1},
    })
    override = {
        "timeout": (3, 4),
        "default_headers": {"B": "2"},
        "extras": {"b": 2},
    }

    merged = base.merge(override)

    assert merged.timeout == (3.0, 4.0)
    assert merged.default_headers == {"A": "1", "B": "2"}
    assert merged.extras == {"a": 1, "b": 2}


def test_merge_with_none_returns_same_instance():
    base = HttpClientOptions.ensure({"timeout": 2})
    same = base.merge(None)
    assert same is base


def test_to_dict_skips_empty_values():
    options = HttpClientOptions()
    assert options.to_dict() == {}


@pytest.mark.parametrize(
    "value",
    [0, -1, (0, 1), (1, 0)],
)
def test_timeout_normalization_rejects_non_positive(value):
    with pytest.raises(ValueError):
        HttpClientOptions.ensure({"timeout": value})


def test_timeout_normalization_rejects_empty_iterable():
    with pytest.raises(ValueError):
        HttpClientOptions.ensure({"timeout": []})

    with pytest.raises(ValueError):
        HttpClientOptions.ensure({"timeout": ()})


def test_timeout_alias_list_single_value():
    options = HttpClientOptions.ensure({"timeout": [3]})
    assert options.timeout == (3.0, 3.0)


def test_headers_alias_is_supported():
    options = HttpClientOptions.ensure({"headers": {"Auth": "tok"}})
    assert options.default_headers == {"Auth": "tok"}


def test_header_canonicalization_preserves_content_type_override():
    options = HttpClientOptions.ensure({"default_headers": {"content-type": "value"}})
    assert options.default_headers == {"Content-type": "value"}


def test_from_mapping_accepts_existing_options_instance():
    original = HttpClientOptions(timeout=10)
    options = HttpClientOptions.from_mapping({"timeout": original})
    assert options.timeout == original.timeout


def test_extras_flattening_behaves_for_mapping_and_non_mapping():
    flattened = HttpClientOptions.from_mapping({
        "extras": {"nested": 1},
        "other": 2,
    })
    assert flattened.extras == {"nested": 1, "other": 2}

    preserved = HttpClientOptions.from_mapping({
        "extras": ["unsupported"],
    })
    assert preserved.extras == {"extras": ["unsupported"]}


def test_max_workers_must_be_positive():
    with pytest.raises(ValueError):
        HttpClientOptions(max_workers=0)


def test_to_dict_includes_all_configured_fields():
    def hook(request):
        return request

    def factory():
        return "client"

    sentinel_opener = object()
    sentinel_client = object()
    sentinel_async_client = object()
    sentinel_executor = object()

    options = HttpClientOptions(
        timeout=(1, 2),
        default_headers={"x-test": "1"},
        prepare_request=hook,
        opener=sentinel_opener,
        client=sentinel_client,
        async_client=sentinel_async_client,
        client_factory=factory,
        async_client_factory=factory,
        max_workers=4,
        executor=sentinel_executor,
        extras={"flag": True},
    )

    data = options.to_dict()
    assert data["timeout"] == (1.0, 2.0)
    assert data["default_headers"] == {"X-Test": "1"}
    assert data["prepare_request"] is hook
    assert data["opener"] is sentinel_opener
    assert data["client"] is sentinel_client
    assert data["async_client"] is sentinel_async_client
    assert data["client_factory"] is factory
    assert data["async_client_factory"] is factory
    assert data["max_workers"] == 4
    assert data["executor"] is sentinel_executor
    assert data["extras"] == {"flag": True}


class DummyConfig(Config):
    def get_query_url_base(self) -> str:
        return "http://example.invalid"

    def __init__(self, *, http_options: Optional[HttpClientOptions] = None):
        super().__init__(http_options=http_options)

    def get_connection_info(self):
        return {"url": "http://example"}

    def validate(self) -> None:  # pragma: no cover - not used in tests
        return None

    @property
    def db_type(self) -> DBType:  # pragma: no cover - not used in tests
        return DBType.VM


def test_inject_http_options_includes_serialized_dict():
    cfg = DummyConfig(http_options=HttpClientOptions(timeout=5))
    info = cfg.get_connection_info()
    merged = cfg._inject_http_options(info)

    assert merged["http_options"]["timeout"] == (5.0, 5.0)


def test_inject_http_options_skips_when_empty():
    cfg = DummyConfig()
    info = cfg.get_connection_info()
    merged = cfg._inject_http_options(info)

    assert "http_options" not in merged
