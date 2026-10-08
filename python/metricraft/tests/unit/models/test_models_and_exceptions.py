"""Tests for VictoriaMetrics-specific models and exceptions."""

import pytest

from metricraft import MetricsInsertData
from metricraft import QueryBuilder


def test_vm_insert_data_validation():
    """Test MetricsInsertData validation."""
    with pytest.raises(ValueError):
        MetricsInsertData(query="", times=[1], values=[1.0])
    with pytest.raises(ValueError):
        MetricsInsertData(query="m", times=[], values=[1.0])
    with pytest.raises(ValueError):
        MetricsInsertData(query="m", times=[1], values=[])
    with pytest.raises(ValueError):
        MetricsInsertData(query="m", times=[1, 2], values=[1.0])


def test_invalid_selector_reports_input_before_rendering():
    with pytest.raises(ValueError, match="invalid metric name") as error:
        QueryBuilder.from_metric("123\n")
    assert "123" in str(error.value)
