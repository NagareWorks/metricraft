"""Lazy C ABI boundary for owned, immutable Rust expressions."""

import ctypes
import os
from pathlib import Path


def _check_abi(library):
    try:
        version = library.mc_abi_version
    except AttributeError as exc:
        raise RuntimeError(
            "Native query library predates the immutable ABI; rebuild the Rust workspace "
            "or reinstall a matching MetriCraft wheel"
        ) from exc
    version.argtypes = []
    version.restype = ctypes.c_uint
    actual = version()
    if actual != 4:
        raise RuntimeError(
            "Native query ABI mismatch (expected 4, got {}); rebuild the Rust workspace "
            "or reinstall a matching MetriCraft wheel".format(actual)
        )


def _load():
    names = ("metricraft_ffi.dll", "libmetricraft_ffi.so", "libmetricraft_ffi.dylib")
    explicit = os.environ.get("METRICRAFT_NATIVE_LIB")
    candidates = [Path(explicit)] if explicit else []
    if not explicit:
        candidates.extend(Path(__file__).parent / "native" / n for n in names)
        roots = []
        if os.environ.get("CARGO_TARGET_DIR"):
            roots.append(Path(os.environ["CARGO_TARGET_DIR"]))
        for parent in Path(__file__).resolve().parents:
            if (parent / "Cargo.toml").is_file() and (parent / "crates").is_dir():
                roots.append(parent / "target")
                break
        for root in roots:
            for profile in ("release", "debug"):
                candidates.extend(root / profile / n for n in names)
    for path in candidates:
        if path.is_file():
            library = ctypes.CDLL(str(path))
            _check_abi(library)
            return library
    raise RuntimeError(
        "Rust library not found; build the workspace and set METRICRAFT_NATIVE_LIB or CARGO_TARGET_DIR"
    )


lib = _load()
pointer = ctypes.c_void_p
lib.mc_expr_new.argtypes = [ctypes.c_char_p] * 3 + [
    ctypes.POINTER(pointer),
    ctypes.c_size_t,
]
lib.mc_expr_new.restype = pointer
lib.mc_expr_free.argtypes = [pointer]
lib.mc_expr_free.restype = None
lib.mc_expr_build.argtypes = [pointer, ctypes.c_uint]
lib.mc_expr_build.restype = pointer
lib.mc_expr_build_with_limits.argtypes = [pointer, ctypes.c_uint, ctypes.c_size_t, ctypes.c_size_t]
lib.mc_expr_build_with_limits.restype = pointer
lib.mc_expr_build_with_options.argtypes = [pointer, ctypes.c_uint, ctypes.c_size_t, ctypes.c_size_t, ctypes.c_uint]
lib.mc_expr_build_with_options.restype = pointer
lib.mc_expr_inspect.argtypes = [pointer, ctypes.c_uint, ctypes.c_uint, ctypes.c_size_t, ctypes.c_size_t, ctypes.c_uint]
lib.mc_expr_inspect.restype = pointer
lib.mc_string_free.argtypes = [pointer]
lib.mc_string_free.restype = None


class Error(ctypes.Structure):
    _fields_ = [("code", ctypes.c_uint), ("message", ctypes.c_char_p)]


lib.mc_last_error.argtypes = []
lib.mc_last_error.restype = ctypes.POINTER(Error)
lib.mc_error_free.argtypes = [ctypes.POINTER(Error)]
lib.mc_error_free.restype = None


def check():
    error = lib.mc_last_error()
    if error:
        try:
            raise ValueError(error.contents.message.decode("utf-8"))
        finally:
            lib.mc_error_free(error)


def encode(value):
    if not isinstance(value, str):
        raise TypeError("expected a string")
    if "\x00" in value:
        raise ValueError("NUL is not accepted at the C string boundary")
    return value.encode("utf-8")


def create(op, a, b, children):
    pointers = (pointer * len(children))(*(child._handle for child in children))
    handle = lib.mc_expr_new(encode(op), encode(a), encode(b), pointers, len(children))
    if not handle:
        check()
        raise RuntimeError("native constructor returned no expression")
    return handle


def _budget(value, name):
    if value is None:
        return 0
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(name + " must be a positive integer or None")
    if value <= 0 or value > ctypes.c_size_t(-1).value:
        raise ValueError(name + " is outside the native positive integer range")
    return value


def build(handle, mode, max_output_bytes=None, max_expanded_nodes=None, experimental_functions=False, features=()):
    if not isinstance(experimental_functions, bool):
        raise TypeError("experimental_functions must be a bool")
    result = lib.mc_expr_build_with_options(
        handle, mode, _budget(max_output_bytes, "max_output_bytes"),
        _budget(max_expanded_nodes, "max_expanded_nodes"), _feature_flags(experimental_functions, features),
    )
    return _string(result)


def inspect(handle, kind, mode, max_output_bytes, max_items, experimental_functions, features=()):
    if not isinstance(experimental_functions, bool):
        raise TypeError("experimental_functions must be a bool")
    return _string(lib.mc_expr_inspect(
        handle, kind, mode, _budget(max_output_bytes, "max_output_bytes"),
        _budget(max_items, "max_items"), _feature_flags(experimental_functions, features),
    ))


def _string(result):
    if not result:
        check()
        raise RuntimeError("native operation returned no string")
    try:
        return ctypes.string_at(result).decode("utf-8")
    finally:
        lib.mc_string_free(result)


def _feature_flags(experimental_functions, features):
    names = {"promql-experimental-functions": 1, "promql-duration-expr": 2,
             "promql-extended-range-selectors": 4, "promql-binop-fill-modifiers": 8}
    if isinstance(features, str):
        raise TypeError("features must be a collection of feature names")
    flags = int(experimental_functions)
    for feature in features:
        if feature not in names:
            raise ValueError("unknown Prometheus feature: " + str(feature))
        flags |= names[feature]
    return flags
