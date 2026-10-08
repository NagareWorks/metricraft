import pytest
from metricraft.config import VMSingleConfig, VMClusterConfig


def test_single_config_validate_errors():
    c = VMSingleConfig(url="http://host")
    c.url = ""  # force empty
    with pytest.raises(ValueError):
        c.validate()

    c.url = 123  # type: ignore[assignment]
    with pytest.raises(ValueError):
        c.validate()

    c.url = "http://host"
    c.timeout = 0
    with pytest.raises(ValueError):
        c.validate()


def test_cluster_config_validate_errors():
    c = VMClusterConfig(
        vminsert_url="http://ins", vmselect_url="http://sel", vmstorage_url="http://sto"
    )
    # Empty one by one
    c.vminsert_url = ""
    with pytest.raises(ValueError):
        c.validate()
    c.vminsert_url = "http://ins"

    c.vmselect_url = ""
    with pytest.raises(ValueError):
        c.validate()
    c.vmselect_url = "http://sel"

    c.vmstorage_url = ""
    with pytest.raises(ValueError):
        c.validate()
    c.vmstorage_url = "http://sto"

    # Non-string
    c.vmstorage_url = 1  # type: ignore[assignment]
    with pytest.raises(ValueError):
        c.validate()
    c.vmstorage_url = "http://sto"

    c.timeout = -1
    with pytest.raises(ValueError):
        c.validate()
