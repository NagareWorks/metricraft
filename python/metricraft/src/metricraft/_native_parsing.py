"""Optional parsing symbols; importing or using the existing ABI never requires them."""
import ctypes

from . import _native
from .builder.parsing import ParseError


class Options(ctypes.Structure):
    _fields_ = [(name, ctypes.c_size_t) for name in (
        "max_input_bytes", "max_tokens", "max_depth", "max_work",
        "max_output_bytes", "max_expanded_nodes",
    )] + [("flags", ctypes.c_uint32)]


class ErrorInfo(ctypes.Structure):
    _fields_ = [("kind", ctypes.c_uint32), ("start", ctypes.c_size_t), ("end", ctypes.c_size_t)]


def _bind(library):
    try:
        function = library.mc_expr_parse
    except AttributeError as exc:
        raise RuntimeError(
            "Native library does not support query parsing; install a matching "
            "MetriCraft wheel or rebuild the Rust workspace"
        ) from exc
    function.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.c_uint32,
                         ctypes.POINTER(Options), ctypes.POINTER(ErrorInfo)]
    function.restype = _native.pointer
    return function


_parse = _bind(_native.lib)


def parse(source, mode, max_input_bytes, max_tokens, max_depth, max_work,
          max_output_bytes, max_expanded_nodes, experimental_functions, features):
    if not isinstance(source, str):
        raise TypeError("source must be a string")
    if not isinstance(experimental_functions, bool):
        raise TypeError("experimental_functions must be a bool")
    values = (max_input_bytes, max_tokens, max_depth, max_work, max_output_bytes, max_expanded_nodes)
    budgets = [_native._budget(value, name) for (name, _), value in zip(Options._fields_, values)]
    options = Options(*budgets, _native._feature_flags(experimental_functions, features))
    data = source.encode("utf-8")
    error = ErrorInfo()
    handle = _parse(data, len(data), mode, ctypes.byref(options), ctypes.byref(error))
    if not handle:
        try:
            _native.check()
        except ValueError as exc:
            if error.kind:
                kinds = {1: "syntax", 2: "validation", 3: "dialect", 4: "unsupported", 5: "limit"}
                raise ParseError(str(exc), kinds.get(error.kind, "other"), error.start, error.end) from None
            raise
        raise RuntimeError("native parser returned no expression")
    return handle
