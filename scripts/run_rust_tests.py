#!/usr/bin/env python3
"""
Simple test runner wrapper for the Rust workspace.

Usage examples:
  python scripts/run_rust_tests.py                      # default toolchain/target
  python scripts/run_rust_tests.py --msvc               # use stable-x86_64-pc-windows-msvc
  python scripts/run_rust_tests.py --gnu                # use stable-x86_64-pc-windows-gnu
  python scripts/run_rust_tests.py --toolchain stable-x86_64-pc-windows-gnu-1.91
  python scripts/run_rust_tests.py --target x86_64-unknown-linux-musl
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Rust workspace test runner")
    parser.add_argument(
        "--msvc", action="store_true", help="use stable-x86_64-pc-windows-msvc toolchain"
    )
    parser.add_argument(
        "--gnu", action="store_true", help="use stable-x86_64-pc-windows-gnu toolchain"
    )
    parser.add_argument(
        "--toolchain", help="explicit rustup toolchain name (overrides --msvc/--gnu)"
    )
    parser.add_argument("--target", help="override target triple")
    parser.add_argument(
        "--mingw-lib",
        help="optional extra native lib search path (e.g. scoop mingw lib); if omitted will auto-detect scoop mingw when target is windows-gnu",
    )

    args = parser.parse_args()

    toolchain = args.toolchain
    if toolchain is None:
        if args.msvc:
            toolchain = "stable-x86_64-pc-windows-msvc"
        elif args.gnu:
            toolchain = "stable-x86_64-pc-windows-gnu"

    env = os.environ.copy()
    if args.gnu:
        target_for_linker = args.target or "x86_64-pc-windows-gnu"
        extra_paths = _detect_mingw_libs(args.mingw_lib, target_for_linker)
        if extra_paths:
            def _sanitize(p: str) -> str:
                return p.replace("\\", "/")
            extra_flags = " ".join(f'-Clink-arg=-L{_sanitize(p)}' for p in extra_paths)
            env["RUSTFLAGS"] = " ".join(
                flag for flag in [env.get("RUSTFLAGS", ""), extra_flags] if flag.strip()
            )

    cmd = ["cargo"]
    if toolchain:
        # Try existing toolchain first; install only if missing.
        probe = subprocess.run(
            ["rustup", "run", toolchain, "rustc", "-V"], capture_output=True
        )
        if probe.returncode != 0:
            subprocess.run(["rustup", "toolchain", "install", toolchain], check=False)
        cmd += ["+" + toolchain]
    cmd += ["test", "--workspace", "--locked", "--manifest-path", str(Path(__file__).resolve().parents[1] / "Cargo.toml")]
    if args.target:
        cmd += ["--target", args.target]

    return subprocess.call(cmd, env=env)


def _detect_mingw_libs(user_path: str, target: str) -> list[str]:
    """
    Try to discover mingw lib paths for windows-gnu targets.
    Priority:
      1) user provided --mingw-lib (single path, can be ; delimited)
      2) MINGW_LIB env (can be ; delimited)
      3) scoop prefix mingw (if scoop is installed)
    Returns list of paths (may be empty).
    """
    paths: list[str] = []
    def split_paths(val: str) -> list[str]:
        sep = ";" if os.name == "nt" else ":"
        return [p for p in val.split(sep) if p]

    if user_path:
        paths.extend(split_paths(user_path))
    elif "MINGW_LIB" in os.environ:
        paths.extend(split_paths(os.environ["MINGW_LIB"]))
    else:
        # Try scoop
        try:
            prefix = subprocess.check_output(
                ["scoop", "prefix", "mingw"], text=True, timeout=3
            ).strip()
            gcc_lib = os.path.join(prefix, "lib", "gcc", "x86_64-w64-mingw32")
            # Pick highest version dir if exists
            if os.path.isdir(gcc_lib):
                versions = sorted(
                    (d for d in os.listdir(gcc_lib) if os.path.isdir(os.path.join(gcc_lib, d))),
                    reverse=True,
                )
                if versions:
                    paths.append(os.path.join(gcc_lib, versions[0]))
            # root lib
            root_lib = os.path.join(prefix, "x86_64-w64-mingw32", "lib")
            if os.path.isdir(root_lib):
                paths.append(root_lib)
        except Exception:
            pass
    # Deduplicate preserving order
    seen = set()
    uniq = []
    for p in paths:
        if p not in seen:
            uniq.append(p)
            seen.add(p)
    return uniq


if __name__ == "__main__":
    sys.exit(main())
