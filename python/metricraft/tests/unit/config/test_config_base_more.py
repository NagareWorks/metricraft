"""Additional coverage for Config registry edge cases."""

from typing import Any, Dict
import pytest

from metricraft.config.base import (
    Config,
    register_config,
    update_config,
    get_config,
    is_configured,
    reset_config,
    set_default_instance,
)
from metricraft.enums import DBType


class _Cfg(Config):
    def get_query_url_base(self) -> str:
        return "http://example.invalid"

    def get_connection_info(self) -> Dict[str, Any]:
        return {"url": "http://x"}

    def validate(self) -> None:
        return None

    @property
    def db_type(self) -> DBType:
        return DBType.VM


class FlaggedCfg(Config):
    def get_query_url_base(self) -> str:
        return "http://example.invalid"

    def __init__(self, marker: str) -> None:
        super().__init__()
        self.marker = marker
        self.validated = False

    def get_connection_info(self) -> Dict[str, Any]:
        return {"marker": self.marker}

    def validate(self) -> None:
        self.validated = True

    @property
    def db_type(self) -> DBType:
        return DBType.VM


def setup_function():
    reset_config()


def teardown_function():
    reset_config()


def test_register_config_invalid_type_raises_valueerror():
    with pytest.raises(ValueError):
        register_config(object())  # type: ignore[arg-type]


def test_set_default_instance_missing_raises():
    # No instances registered yet
    with pytest.raises(RuntimeError):
        set_default_instance(DBType.VM, "missing")


def test_get_config_specific_instance_missing_raises_and_is_configured_instance():
    register_config(_Cfg(), instance="a")
    # Instance flag
    assert is_configured(DBType.VM, "a") is True
    assert is_configured(DBType.VM, "b") is False
    # Missing instance fetch raises
    with pytest.raises(RuntimeError):
        get_config(DBType.VM, instance="b")


def test_update_config_replaces_existing_config_and_preserves_default():
    cfg1 = FlaggedCfg("one")
    register_config(cfg1, instance="primary", set_default=True)
    assert cfg1.validated is True

    cfg2 = FlaggedCfg("two")
    update_config(cfg2, instance="primary")
    assert cfg2.validated is True

    fetched = get_config(DBType.VM)
    assert fetched is cfg2
    assert fetched.get_connection_info()["marker"] == "two"


def test_update_config_can_switch_default_instance():
    register_config(FlaggedCfg("first"), instance="a")
    register_config(FlaggedCfg("second"), instance="b")

    new_cfg = FlaggedCfg("second_new")
    update_config(new_cfg, instance="b", set_default=True)
    assert new_cfg.validated is True

    fetched_default = get_config(DBType.VM)
    assert fetched_default is new_cfg
    assert fetched_default.get_connection_info()["marker"] == "second_new"


def test_update_config_without_existing_entry_raises():
    with pytest.raises(RuntimeError):
        update_config(FlaggedCfg("missing"))
