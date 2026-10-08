"""Endpoint configurations and optional named-instance registry."""
from .base import Config, register_config, get_config, is_configured, reset_config, set_default_instance
from .single import VMSingleConfig
from .cluster import VMClusterConfig
from .prometheus import PrometheusConfig
from .http_options import HttpClientOptions

__all__ = [
    "Config", "VMSingleConfig", "VMClusterConfig", "PrometheusConfig", "HttpClientOptions",
    "register_config", "get_config", "is_configured", "reset_config", "set_default_instance",
]
