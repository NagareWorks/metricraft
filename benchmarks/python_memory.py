"""Measure Python-owned heap and process memory around real ctypes query lifetimes.

Native requested-allocation accounting lives in the Rust memory_profile probe.
Process memory includes allocator caches; it is not a native leak counter.
"""
import argparse
import ctypes
import gc
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import tracemalloc
import weakref

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python/metricraft/src"))
from metricraft import QueryBuilder as Q


@lru_cache(maxsize=1)
def _windows_reader():
    # Define ctypes types once: POINTER caches type objects globally. Defining a
    # new Counters class per sample would make the measurement itself retain memory.
    if sys.platform == "win32":
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in (
                    "PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                    "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage",
                    "PagefileUsage", "PeakPagefileUsage", "PrivateUsage",
                )
            ]

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        def read():
            data = Counters()
            data.cb = ctypes.sizeof(data)
            if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(data), data.cb):
                raise ctypes.WinError(ctypes.get_last_error())
            return {"private_bytes": data.PrivateUsage, "resident_bytes": data.WorkingSetSize}
        return read
    raise RuntimeError("Windows process memory is unavailable on this platform")


def process_memory():
    if sys.platform == "win32":
        return _windows_reader()()
    if sys.platform.startswith("linux"):
        fields = dict(line.split(":", 1) for line in Path("/proc/self/status").read_text().splitlines() if ":" in line)
        return {"resident_bytes": int(fields["VmRSS"].split()[0]) * 1024}
    return {}


def snapshot(phase):
    gc.collect()
    current, peak = tracemalloc.get_traced_memory()
    return dict(phase=phase, python_live_bytes=current, python_peak_bytes=peak, **process_memory())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--branches", type=int, default=2000)
    parser.add_argument("--batches", type=int, default=10)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.branches <= 0 or args.batches <= 0:
        parser.error("branches and batches must be positive")
    library = os.environ.get("METRICRAFT_NATIVE_LIB")
    if not library:
        parser.error("set METRICRAFT_NATIVE_LIB to the release-mode library")
    base = Q.from_metric("requests_total")
    for i in range(256):
        base = base.where_eq("label_" + str(i), "x" * 128)
    # Initialize ctypes and allocator paths before taking the baseline.
    for _ in range(200):
        base.where_eq("job", "warmup").build("promql")
        base.label_copy(("label_0", "copied")).build("metricsql")
    process_memory()
    gc.collect()
    tracemalloc.start()
    samples = [snapshot("baseline")]
    for prefix, mode, make in (
        ("", "promql", lambda i: base.where_eq("instance", str(i))),
        ("label_copy_", "metricsql", lambda i: base.label_copy(("label_0", "copied"))),
        ("template_", "metricsql", lambda i: Q.reference("x").with_(x=base)),
    ):
        for batch in range(args.batches):
            roots = [make(i) for i in range(args.branches)]
            refs = [weakref.ref(root) for root in roots]
            if batch == 0:
                samples.append(snapshot(prefix + "retained_branches"))
            for root in roots:
                root.build(mode)
            del root, roots
            gc.collect()
            assert all(ref() is None for ref in refs), "a Python query owner was retained"
            del refs
            samples.append(snapshot(prefix + "released_batch_" + str(batch + 1)))
    tracemalloc.stop()
    package = ROOT / "python/metricraft/src/metricraft"
    source_paths = list((ROOT / "crates").rglob("*.rs")) + list((package / "builder").glob("*.py")) + [package / "_native.py"]
    result = {
        "platform": platform.platform(), "python": sys.version,
        "branches": args.branches, "batches": args.batches, "labels_in_shared_base": 256,
        "workloads": ["selector branches", "label_copy branches with per-call string owners", "WITH branches sharing a binding"],
        "native_sha256": hashlib.sha256(Path(library).read_bytes()).hexdigest(),
        "source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(source_paths)},
        "note": "Python heap tracing and process memory include measurement overhead and allocator caches. This is not a native leak detector.",
        "samples": samples,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    for sample in samples:
        print(sample)


if __name__ == "__main__":
    main()
