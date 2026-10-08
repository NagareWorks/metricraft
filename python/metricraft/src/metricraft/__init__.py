# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025-present NagareWorks
"""Immutable PromQL/MetricsQL construction and independent HTTP client contracts."""

from metricraft.builder import QueryBuilder, QueryMode, vm_only, prom_only

from metricraft.client import DatabaseClient
from metricraft.models import (
    TimeValue,
    MetricsQueryResult,
    MetricsInsertData,
)

# TSDB Configuration
from metricraft.config import (
    Config, register_config, get_config, set_default_instance,
    VMSingleConfig, VMClusterConfig, PrometheusConfig, HttpClientOptions,
)
from metricraft.enums import DBType

from metricraft.exceptions import MetriCraftError, MCHTTPError, TimeoutError, ConnectionError


# Version information
__version__ = "0.3.0"
__author__ = "NagareWorks"
__license__ = "Apache-2.0 © 2025-present NagareWorks"
__description__ = "PromQL/MetricsQL query builder and HTTP client"

# Public API exports
__all__ = [
    # === Core Query Building ===
    'QueryBuilder', 'QueryMode', 'vm_only', 'prom_only',

    # === TSDB Client ===
    'DatabaseClient',
    'TimeValue',
    'MetricsQueryResult',
    'MetricsInsertData',

    # === TSDB Configuration ===
    'Config',
    'register_config',
    'get_config',
    'set_default_instance',
    'VMSingleConfig', 'VMClusterConfig', 'PrometheusConfig', 'HttpClientOptions',
    'DBType',

    # === Exception Handling ===
    # General Exceptions
    'MetriCraftError',

    # Client Exceptions
    'MCHTTPError',
    'TimeoutError',
    'ConnectionError',

    # === Metadata ===
    '__version__',
    '__author__',
    '__license__',
    '__description__',
]
