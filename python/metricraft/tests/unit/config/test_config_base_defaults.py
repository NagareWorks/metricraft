"""Cover default selection and multiple-instance error branches in config registry."""

from typing import Any, Dict
import pytest

from metricraft.config.base import Config, register_config, get_config, reset_config
from metricraft.enums import DBType


class _Cfg(Config):
    def get_query_url_base(self) -> str:
        return "http://example.invalid"

    def __init__(self, name: str):
        super().__init__()
        self.name = name
    def get_connection_info(self) -> Dict[str, Any]:
        return {"name": self.name}
    def validate(self) -> None:
        return None
    @property
    def db_type(self) -> DBType:
        return DBType.VM


def setup_function():
    reset_config()


def teardown_function():
    reset_config()


def test_get_config_uses_default_when_multiple_instances():
    # First registration becomes default implicitly
    register_config(_Cfg("a"), instance="a", set_default=True)
    register_config(_Cfg("b"), instance="b", set_default=False)
    cfg = get_config(DBType.VM)
    assert cfg.get_connection_info()["name"] == "a"
    assert get_config() is cfg


def test_get_config_raises_when_multiple_no_default():
    register_config(_Cfg("a"), instance="a", set_default=False)
    register_config(_Cfg("b"), instance="b", set_default=False)
    with pytest.raises(RuntimeError):
        get_config(DBType.VM)
