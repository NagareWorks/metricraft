"""Download the released wheel from PyPI and verify the exact tested artifact."""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import time

from check_native_wheel import verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--expected", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    for name in ("PYTHONPATH", "METRICRAFT_NATIVE_LIB", "CARGO_TARGET_DIR"):
        env.pop(name, None)
    # Index propagation can lag behind a successful upload for a short time.
    for attempt in range(4):
        result = subprocess.run([
            sys.executable, "-m", "pip", "--isolated", "download", "--no-deps",
            "--no-cache-dir", "--only-binary=:all:", "--index-url", "https://pypi.org/simple",
            "--dest", str(args.output), "metricraft==" + args.version], env=env)
        if result.returncode == 0:
            break
        if attempt == 3:
            raise SystemExit(result.returncode)
        time.sleep(15)
    wheel, = args.output.glob("metricraft-*.whl")
    expected = args.expected / wheel.name
    if hashlib.sha256(wheel.read_bytes()).digest() != hashlib.sha256(expected.read_bytes()).digest():
        raise SystemExit("PyPI wheel differs from the validated release artifact")
    verify(wheel, args.source_commit)
    subprocess.run([sys.executable, str(Path(__file__).with_name("check_python_package.py")),
                    str(args.output), "--require-bundled-native"], env=env, check=True)
    print("Verified exact PyPI artifact and isolated installed SDK: " + wheel.name)


if __name__ == "__main__":
    main()
