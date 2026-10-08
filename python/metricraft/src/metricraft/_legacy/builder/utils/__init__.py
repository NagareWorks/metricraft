"""
VM builder utilities.

This package contains shared utilities used by the VM builder implementation.
"""

from .templates import *

__all__ = [
    # Templates - these are imported dynamically by mixins
    "create_binary_operation",
    "create_reverse_binary_operation", 
    "create_unary_function",
    "create_function_with_args",
    "create_transformation_function",
    "create_label_function",
    "create_aggregation_function",
    "create_range_vector_function",
    "create_simple_over_time_function",
    "maybe_parenthesize",
]
