"""Direct client construction and named endpoint selection."""
import pytest
from metricraft import DatabaseClient, VMSingleConfig, VMClusterConfig, PrometheusConfig, DBType
from metricraft.config import register_config, reset_config, get_config


@pytest.fixture(autouse=True)
def registry():
    reset_config()
    yield
    reset_config()


@pytest.mark.parametrize("config", [
    VMSingleConfig("http://single.invalid"),
    VMClusterConfig(vmselect_url="http://select.invalid", vminsert_url="http://insert.invalid", vmstorage_url="http://storage.invalid"),
    PrometheusConfig("http://prometheus.invalid"),
])
def test_explicit_config_needs_no_registration(config):
    with DatabaseClient(config) as client:
        assert type(client) is DatabaseClient
        assert client.get_connection_info() == config.get_connection_info()


def test_named_instance_selects_registered_endpoint():
    register_config(VMSingleConfig("http://first.invalid"), instance="first")
    register_config(PrometheusConfig("http://second.invalid"), instance="second")
    with DatabaseClient(instance="second") as client:
        assert client.get_connection_info()["url"] == "http://second.invalid"


@pytest.mark.parametrize("config_class", [VMSingleConfig, PrometheusConfig])
def test_default_registry_remains_optional_convenience(config_class):
    config = config_class("http://default.invalid")
    register_config(config)
    with DatabaseClient() as client:
        assert client.get_connection_info() == config.get_connection_info()


def test_unconfigured_client_fails_with_configuration_error():
    with pytest.raises(RuntimeError, match="No configuration"):
        DatabaseClient()


def test_explicit_config_does_not_replace_registered_default():
    register_config(VMSingleConfig("http://default.invalid"))
    with DatabaseClient(PrometheusConfig("http://explicit.invalid")) as direct:
        assert direct.get_connection_info()["url"] == "http://explicit.invalid"
    with DatabaseClient() as default:
        assert default.get_connection_info()["url"] == "http://default.invalid"


def test_same_instance_name_is_isolated_by_backend():
    vm = VMSingleConfig("http://vm.invalid")
    prometheus = PrometheusConfig("http://prometheus.invalid")
    register_config(vm, instance="prod")
    register_config(prometheus, instance="prod")

    assert get_config(DBType.VM, "prod") is vm
    assert get_config(DBType.PROMETHEUS, "prod") is prometheus
    with DatabaseClient(get_config(DBType.PROMETHEUS, "prod")) as client:
        assert client.select_base_url == "http://prometheus.invalid"
    with DatabaseClient(get_config(DBType.VM, "prod")) as client:
        assert client.select_base_url == "http://vm.invalid/prometheus"


@pytest.mark.parametrize("instance", [None, "prod"])
def test_ambiguous_backend_selection_fails_before_transport_allocation(monkeypatch, instance):
    register_config(VMSingleConfig("http://vm.invalid"), instance="prod")
    register_config(PrometheusConfig("http://prometheus.invalid"), instance="prod")

    def unexpected(**options):
        pytest.fail("Transport allocated before endpoint resolution")

    monkeypatch.setattr("metricraft.client.db_client.SyncHTTPClient", unexpected)
    monkeypatch.setattr("metricraft.client.db_client.AsyncHTTPClient", unexpected)
    with pytest.raises(RuntimeError, match="Ambiguous configuration.*explicit config"):
        DatabaseClient(instance=instance)


def test_missing_instance_does_not_fall_back_to_default():
    register_config(VMSingleConfig("http://vm.invalid"), instance="vm")
    register_config(PrometheusConfig("http://prometheus.invalid"), instance="prometheus")
    with pytest.raises(RuntimeError, match="No configuration.*missing"):
        DatabaseClient(instance="missing")
