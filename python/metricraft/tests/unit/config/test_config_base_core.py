"""Tests for Config base registry behaviors."""

from typing import Any, Dict
import pytest

from metricraft.config.base import (
    Config,
    register_config,
    get_config,
    reset_config,
    is_configured,
    update_config,
    set_default_instance,
)
from metricraft.config.http_options import HttpClientOptions
from metricraft.enums import DBType


class Cfg(Config):
    def get_query_url_base(self) -> str:
        return "http://example.invalid"

    def get_connection_info(self) -> Dict[str, Any]:
        return {"k": "v"}

    def validate(self) -> None:
        return None

    @property
    def db_type(self) -> DBType:
        return DBType.VM


def setup_function():
    reset_config()


def teardown_function():
    reset_config()


def test_register_and_get():
    cfg = Cfg()
    register_config(cfg)
    assert is_configured(DBType.VM) is True
    got = get_config(DBType.VM)
    assert got is cfg


def test_register_twice_raises():
    cfg = Cfg()
    register_config(cfg)
    with pytest.raises(RuntimeError):
        register_config(cfg)


def test_get_without_register_raises():
    reset_config()
    with pytest.raises(RuntimeError):
        get_config(DBType.VM)


def test_config_init_rejects_mapping_http_options():
    with pytest.raises(TypeError):
        Cfg(http_options={"timeout": 5})  # type: ignore[arg-type]


def test_set_and_update_http_options():
    cfg = Cfg()
    cfg.set_http_options(HttpClientOptions(timeout=5))
    assert cfg.http_options.timeout == (5.0, 5.0)

    cfg.update_http_options(HttpClientOptions(default_headers={"x": "y"}))
    assert cfg.http_options.default_headers == {"X": "y"}


def test_update_http_options_rejects_mapping():
    cfg = Cfg()
    with pytest.raises(TypeError):
        cfg.update_http_options({"timeout": 5})  # type: ignore[arg-type]


def test_update_config_replaces_and_sets_default():
    cfg1 = Cfg()
    cfg2 = Cfg()

    register_config(cfg1, instance="primary", set_default=False)
    register_config(cfg2, instance="secondary")
    assert get_config(DBType.VM, "secondary") is cfg2

    replacement = Cfg()
    update_config(replacement, instance="primary", set_default=True)
    assert get_config(DBType.VM, "primary") is replacement
    # default switched to primary via update_config
    assert get_config(DBType.VM) is replacement


def test_set_default_instance_switches_bucket():
    cfg1 = Cfg()
    cfg2 = Cfg()
    register_config(cfg1, instance="a", set_default=False)
    register_config(cfg2, instance="b", set_default=False)

    with pytest.raises(RuntimeError):
        get_config(DBType.VM)

    set_default_instance(DBType.VM, "b")
    assert get_config(DBType.VM) is cfg2

    assert is_configured(DBType.VM, "b") is True
