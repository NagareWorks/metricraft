import pytest

from metricraft import DatabaseClient, QueryBuilder
from metricraft.config import reset_config
from metricraft.config.single import VMSingleConfig


def test_direct_builder_and_client_construction():
    reset_config()
    # Register minimal config; defaults: instance="default"
    cfg = VMSingleConfig("http://localhost:8428")
    from metricraft import register_config  # late import to avoid cycles in some runners
    register_config(cfg)

    b = QueryBuilder()
    c = DatabaseClient()
    assert hasattr(b, 'build')
    assert hasattr(c, 'query')


def test_endpoint_config_base_init_via_subclass():
    from metricraft.config import Config
    from metricraft.enums import DBType

    class MyCfg(Config):
        @property
        def db_type(self):
            return DBType.VM

        def get_connection_info(self):
            return {"url": "http://localhost:8428"}

        def validate(self):
            return None

        def get_query_url_base(self) -> str:
            return "http://localhost:8428/prometheus"

        def get_insert_url_base(self) -> str:
            return "http://localhost:8428/prometheus"

    cfg = MyCfg()
    assert cfg.get_connection_info()["url"].startswith("http")


def test_metricsbuilder_create_new_builder_none_raises():
    from metricraft._legacy.builder.impl.base import MetricsBuilder

    mb = MetricsBuilder(ast_node=None)
    with pytest.raises(ValueError):
        mb._create_new_builder(None)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_vm_client_async_methods_require_async_client():
    reset_config()
    from metricraft import register_config
    register_config(VMSingleConfig("http://localhost:8428"))
    c = DatabaseClient()
    c.async_client = None
    with pytest.raises(RuntimeError):
        await c.query_async("up")
    with pytest.raises(RuntimeError):
        await c.query_range_async("up")
    with pytest.raises(RuntimeError):
        await c.insert_async(object())
