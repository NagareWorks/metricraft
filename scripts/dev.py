"""Run SDK checks from any working directory (Python 3.8+)."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def run(command, env):
    print("+ " + " ".join(map(str, command)), flush=True)
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build", "rust", "tests", "client", "query",
                                             "conformance", "smoke", "check"])
    command = parser.parse_args().command
    env = os.environ.copy()
    env.update(PYTHONUTF8="1", PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT / "python/metricraft/src"),
                                        env.get("PYTHONPATH", "")]).rstrip(os.pathsep)
    target = Path(env.get("CARGO_TARGET_DIR", str(ROOT / "target"))).resolve()
    env["CARGO_TARGET_DIR"] = str(target)
    native = ("metricraft_ffi.dll" if sys.platform == "win32" else
              "libmetricraft_ffi.dylib" if sys.platform == "darwin" else "libmetricraft_ffi.so")
    if command != "rust":
        run(["cargo", "build", "--workspace", "--locked"], env)
        env["METRICRAFT_NATIVE_LIB"] = str(target / "debug" / native)
    suites = ("rust", "tests", "smoke") if command == "check" else (command,)
    failures = []
    for suite in suites:
        try:
            if suite == "rust":
                run(["cargo", "test", "--workspace", "--locked"], env)
            if suite in ("tests", "query", "client"):
                paths = {
                    "tests": ["tests", "python/metricraft/tests"],
                    "query": ["tests"],
                    "client": ["python/metricraft/tests/unit/client", "tests/test_client_without_native.py"],
                }[suite]
                run([sys.executable, "-m", "pytest", "-o", "addopts=", "-o", "asyncio_mode=auto",
                     "--import-mode=importlib", "-p", "no:cacheprovider", "-q"] + paths, env)
            if suite == "smoke":
                for example in ("01_configurable_query", "02_saved_query", "03_language_extensions"):
                    run([sys.executable, "docs/examples/" + example + "/main.py"], env)
            if suite == "conformance":
                run([sys.executable, "scripts/check_query_parsers.py"], env)
        except subprocess.CalledProcessError:
            if command != "check":
                raise
            failures.append(suite)
    if command == "check":
        print("Failed suites: " + ", ".join(failures) if failures else "All workspace checks passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.CalledProcessError as exc:
        sys.exit(exc.returncode)
