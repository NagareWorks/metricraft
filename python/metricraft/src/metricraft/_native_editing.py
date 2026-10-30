"""Optional traversal/editing exports. Native owners are never copied recursively."""
import ctypes

from . import _native


class BuildOptions(ctypes.Structure):
    _fields_ = [("max_output_bytes", ctypes.c_size_t),
                ("max_expanded_nodes", ctypes.c_size_t), ("flags", ctypes.c_uint32)]


def _bind(library):
    pointer, size = _native.pointer, ctypes.c_size_t
    path = ctypes.POINTER(size)
    signatures = {
        "node_info": ([pointer, ctypes.c_uint32], pointer),
        "children": ([pointer, ctypes.POINTER(pointer), size], ctypes.c_ssize_t),
        "at_path": ([pointer, path, size], pointer),
        "shares_node": ([pointer, pointer], ctypes.c_int32),
        "replace_at": ([pointer, path, size, pointer, ctypes.c_uint32,
                        ctypes.POINTER(BuildOptions)], pointer),
    }
    functions = {}
    for name, (arguments, result) in signatures.items():
        try:
            function = getattr(library, "mc_expr_" + name)
        except AttributeError as exc:
            raise RuntimeError(
                "Native library does not support AST editing; install a matching "
                "MetriCraft wheel or rebuild the Rust workspace"
            ) from exc
        function.argtypes, function.restype = arguments, result
        functions[name] = function
    return functions


_functions = _bind(_native.lib)


def _path(values):
    # Consume at most 1025 entries, including generators, before rejecting depth.
    indexes = []
    maximum = ctypes.c_size_t(-1).value
    for value in values:
        if len(indexes) == 1024:
            raise ValueError("AST path exceeds 1024 steps")
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError("AST child indexes must be integers, not booleans")
        if value < 0 or value > maximum:
            raise ValueError("AST child index is outside the native unsigned integer range")
        indexes.append(value)
    return (ctypes.c_size_t * len(indexes))(*indexes)


def _result(value, failed):
    if failed:
        _native.check()
        raise RuntimeError("native AST operation failed without an error")
    return value


def node_info(handle, kind):
    return _native._string(_functions["node_info"](handle, kind))


def at_path(handle, path):
    indexes = _path(path)
    result = _functions["at_path"](handle, indexes, len(indexes))
    return _result(result, not result)


def children(handle, wrap):
    function = _functions["children"]
    count = function(handle, None, 0)
    _result(count, count < 0)
    pointers = (_native.pointer * count)()
    owners = []
    result = function(handle, pointers, count)
    _result(result, result < 0)
    try:
        for i in range(count):
            pointer = pointers[i]
            pointers[i] = None  # Transfer this owner to the expression wrapper.
            owners.append(wrap(pointer))
        return tuple(owners)
    finally:
        for pointer in pointers:
            if pointer:
                _native.lib.mc_expr_free(pointer)


def shares_node(handle, other):
    result = _functions["shares_node"](handle, other)
    return bool(_result(result, result < 0))


def replace_at(handle, path, replacement, mode, max_output_bytes,
               max_expanded_nodes, experimental_functions, features):
    indexes = _path(path)
    if not isinstance(experimental_functions, bool):
        raise TypeError("experimental_functions must be a bool")
    options = BuildOptions(
        _native._budget(max_output_bytes, "max_output_bytes"),
        _native._budget(max_expanded_nodes, "max_expanded_nodes"),
        _native._feature_flags(experimental_functions, features),
    )
    result = _functions["replace_at"](handle, indexes, len(indexes), replacement,
                                      mode, ctypes.byref(options))
    return _result(result, not result)
