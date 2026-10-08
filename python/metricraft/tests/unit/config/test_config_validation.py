"""Tests for config validation methods."""

import pytest

from metricraft.config.http_options import HttpClientOptions
from metricraft.config import VMSingleConfig, VMClusterConfig, PrometheusConfig


def test_vm_single_config_validation_success():
    """Test VMSingleConfig validation succeeds with valid parameters."""
    config = VMSingleConfig(
        'http://localhost:8428',
        default_step='1m',
        http_options=HttpClientOptions(timeout=30.0)
    )
    # validate() should not raise any exception
    config.validate()


def test_vm_single_config_validation_empty_url():
    """Test VMSingleConfig validation fails with empty URL."""
    config = VMSingleConfig('', http_options=HttpClientOptions(timeout=1.0))
    config.url = ''  # Force empty URL
    with pytest.raises(ValueError, match="VM URL cannot be empty"):
        config.validate()


def test_vm_single_config_validation_invalid_url_type():
    """Test VMSingleConfig validation fails with non-string URL."""
    config = VMSingleConfig('http://localhost:8428', http_options=HttpClientOptions(timeout=1.0))
    config.url = 12345  # Force invalid type
    with pytest.raises(ValueError, match="VM URL must be a string"):
        config.validate()


def test_vm_single_config_validation_invalid_timeout():
    """Test VMSingleConfig validation fails with invalid timeout."""
    config = VMSingleConfig('http://localhost:8428', http_options=HttpClientOptions(timeout=1.0))
    config.timeout = 0  # Force zero timeout
    with pytest.raises(ValueError, match="Timeout must be positive"):
        config.validate()

    config.timeout = -1  # Force negative timeout
    with pytest.raises(ValueError, match="Timeout must be positive"):
        config.validate()


def test_vm_single_config_rejects_timeout_kwarg():
    """Test VMSingleConfig rejects timeout as kwarg."""
    with pytest.raises(TypeError, match="timeout must be provided inside http_options"):
        VMSingleConfig('http://localhost:8428', timeout=30.0)


def test_vm_cluster_config_validation_success():
    """Test VMClusterConfig validation succeeds with valid parameters."""
    config = VMClusterConfig(
        vminsert_url='http://vminsert:8480',
        vmselect_url='http://vmselect:8481',
        vmstorage_url='http://vmstorage:8482',
        account_id=100,
        http_options=HttpClientOptions(timeout=30.0)
    )
    # validate() should not raise any exception
    config.validate()


def test_vm_cluster_config_validation_empty_urls():
    """Test VMClusterConfig validation fails with empty URLs."""
    config = VMClusterConfig(
        vminsert_url='http://vminsert:8480',
        vmselect_url='http://vmselect:8481',
        vmstorage_url='http://vmstorage:8482',
        http_options=HttpClientOptions(timeout=1.0)
    )

    # Test empty vminsert_url
    config.vminsert_url = ''
    with pytest.raises(ValueError, match="vminsert_url cannot be empty"):
        config.validate()

    # Reset and test empty vmselect_url
    config.vminsert_url = 'http://vminsert:8480'
    config.vmselect_url = ''
    with pytest.raises(ValueError, match="vmselect_url cannot be empty"):
        config.validate()

    # Reset and test empty vmstorage_url
    config.vmselect_url = 'http://vmselect:8481'
    config.vmstorage_url = ''
    with pytest.raises(ValueError, match="vmstorage_url cannot be empty"):
        config.validate()


def test_vm_cluster_config_validation_invalid_url_types():
    """Test VMClusterConfig validation fails with non-string URLs."""
    config = VMClusterConfig(
        vminsert_url='http://vminsert:8480',
        vmselect_url='http://vmselect:8481',
        vmstorage_url='http://vmstorage:8482',
        http_options=HttpClientOptions(timeout=1.0)
    )

    # Test non-string vminsert_url
    config.vminsert_url = 12345
    with pytest.raises(ValueError, match="vminsert_url must be a string"):
        config.validate()

    # Reset and test non-string vmselect_url
    config.vminsert_url = 'http://vminsert:8480'
    config.vmselect_url = 12345
    with pytest.raises(ValueError, match="vmselect_url must be a string"):
        config.validate()

    # Reset and test non-string vmstorage_url
    config.vmselect_url = 'http://vmselect:8481'
    config.vmstorage_url = 12345
    with pytest.raises(ValueError, match="vmstorage_url must be a string"):
        config.validate()


def test_vm_cluster_config_validation_invalid_account_id():
    """Test VMClusterConfig validation fails with invalid account_id."""
    config = VMClusterConfig(
        vminsert_url='http://vminsert:8480',
        vmselect_url='http://vmselect:8481',
        vmstorage_url='http://vmstorage:8482',
        http_options=HttpClientOptions(timeout=1.0)
    )

    # Test non-integer account_id
    config.account_id = "100"
    with pytest.raises(ValueError, match="account_id must be an integer"):
        config.validate()

    # Test negative account_id
    config.account_id = -1
    with pytest.raises(ValueError, match="account_id must be non-negative"):
        config.validate()


def test_vm_cluster_config_validation_invalid_timeout():
    """Test VMClusterConfig validation fails with invalid timeout."""
    config = VMClusterConfig(
        vminsert_url='http://vminsert:8480',
        vmselect_url='http://vmselect:8481',
        vmstorage_url='http://vmstorage:8482',
        http_options=HttpClientOptions(timeout=1.0)
    )

    config.timeout = 0
    with pytest.raises(ValueError, match="Timeout must be positive"):
        config.validate()


def test_vm_cluster_config_rejects_timeout_kwarg():
    """Test VMClusterConfig rejects timeout as kwarg."""
    with pytest.raises(TypeError, match="timeout must be provided inside http_options"):
        VMClusterConfig(
            vminsert_url='http://vminsert:8480',
            vmselect_url='http://vmselect:8481',
            vmstorage_url='http://vmstorage:8482',
            timeout=30.0
        )


def test_prometheus_config_validation_success():
    """Test PrometheusConfig validation succeeds with valid parameters."""
    config = PrometheusConfig(
        'http://localhost:9090',
        default_step='1m',
        http_options=HttpClientOptions(timeout=30.0)
    )
    # validate() should not raise any exception
    config.validate()


def test_prometheus_config_validation_empty_url():
    """Test PrometheusConfig validation fails with empty URL."""
    config = PrometheusConfig('', http_options=HttpClientOptions(timeout=1.0))
    config.url = ''
    with pytest.raises(ValueError, match="Prometheus URL cannot be empty"):
        config.validate()


def test_prometheus_config_validation_invalid_url_type():
    """Test PrometheusConfig validation fails with non-string URL."""
    config = PrometheusConfig('http://localhost:9090', http_options=HttpClientOptions(timeout=1.0))
    config.url = 12345
    with pytest.raises(ValueError, match="Prometheus URL must be a string"):
        config.validate()


def test_prometheus_config_validation_invalid_timeout():
    """Test PrometheusConfig validation fails with invalid timeout."""
    config = PrometheusConfig('http://localhost:9090', http_options=HttpClientOptions(timeout=1.0))
    config.timeout = 0
    with pytest.raises(ValueError, match="Timeout must be positive"):
        config.validate()


def test_prometheus_config_rejects_timeout_kwarg():
    """Test PrometheusConfig rejects timeout as kwarg."""
    with pytest.raises(TypeError, match="timeout must be provided inside http_options"):
        PrometheusConfig('http://localhost:9090', timeout=30.0)


def test_prometheus_config_get_insert_url_raises_error():
    """Test PrometheusConfig raises error when trying to get insert URL."""
    config = PrometheusConfig('http://localhost:9090', http_options=HttpClientOptions(timeout=1.0))

    with pytest.raises(NotImplementedError, match="Prometheus does not support insert operations"):
        config.get_insert_url_base()


def test_vm_single_config_url_methods():
    """Test VMSingleConfig URL construction methods."""
    config = VMSingleConfig('http://localhost:8428', http_options=HttpClientOptions(timeout=1.0))

    query_url = config.get_query_url_base()
    assert query_url == 'http://localhost:8428/prometheus'

    insert_url = config.get_insert_url_base()
    assert insert_url == 'http://localhost:8428/prometheus'


def test_vm_cluster_config_url_methods():
    """Test VMClusterConfig URL construction methods."""
    config = VMClusterConfig(
        vminsert_url='http://vminsert:8480',
        vmselect_url='http://vmselect:8481',
        vmstorage_url='http://vmstorage:8482',
        account_id=100,
        http_options=HttpClientOptions(timeout=1.0)
    )

    query_url = config.get_query_url_base()
    assert query_url == 'http://vmselect:8481/select/100/prometheus'

    insert_url = config.get_insert_url_base()
    assert insert_url == 'http://vminsert:8480/insert/100/prometheus'


def test_prometheus_config_url_methods():
    """Test PrometheusConfig URL construction methods."""
    config = PrometheusConfig('http://localhost:9090', http_options=HttpClientOptions(timeout=1.0))

    query_url = config.get_query_url_base()
    assert query_url == 'http://localhost:9090'
