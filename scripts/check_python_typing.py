"""Check installed public types outside the checkout with mypy and optional Pyright."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import venv


ROOT = Path(__file__).resolve().parents[1]


def check(python, work, env, *, pyright=False):
    """Use the caller's mypy and the isolated interpreter's site-packages."""
    env = env.copy()
    for key in ("PYTHONPATH", "MYPYPATH", "METRICRAFT_NATIVE_LIB", "CARGO_TARGET_DIR"):
        env.pop(key, None)
    # An explicit config prevents a caller's suppressions from weakening the check.
    config = work / "mypy.ini"
    config.write_text("[mypy]\nstrict = True\npython_version = 3.11\n", encoding="utf-8")
    command = [sys.executable, "-I", "-m", "mypy", "--config-file", str(config),
               "--python-executable", str(python), "--no-incremental",
               "--cache-dir", str(work / "mypy-cache"), "--show-error-codes",
               "--no-error-summary", "--no-pretty", "--no-color-output"]
    for name in ("consumer.py", "invalid.py"):
        source = (ROOT / "tests/typing" / name).read_text(encoding="utf-8")
        (work / name).write_text(source, encoding="utf-8")
        result = subprocess.run(command + [name], cwd=work, env=env,
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if name == "consumer.py":
            if result.returncode:
                raise RuntimeError("Installed SDK typing failed:\n" + result.stdout)
        else:
            expected = {(line, code) for line, text in enumerate(source.splitlines(), 1)
                        for code in re.findall(r"# expect: ([a-z-]+)", text)}
            errors = re.findall(r"^invalid\.py:(\d+): error: .*\[([a-z-]+)\]$",
                                result.stdout, re.MULTILINE)
            actual = {(int(line), code) for line, code in errors}
            unexpected = [line for line in result.stdout.splitlines()
                          if ": error:" in line and not line.startswith("invalid.py:")]
            if result.returncode != 1 or actual != expected or unexpected:
                raise RuntimeError("Negative typing contract changed: expected " + str(sorted(expected))
                                   + ", got " + str(sorted(actual)) + "\n" + result.stdout)
    print("Installed SDK types: fluent inference, decorators, client and invalid calls passed.")
    if pyright:
        config = work / "pyrightconfig.json"
        config.write_text(json.dumps({
            "include": ["consumer.py", "invalid.py"],
            "typeCheckingMode": "strict", "pythonVersion": "3.11",
        }), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "-I", "-m", "pyright", "--project", str(config),
             "--pythonpath", str(python), "--outputjson"],
            cwd=work, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        if result.returncode != 1:
            raise RuntimeError("Expected Pyright to reject invalid.py:\n" + result.stdout + result.stderr)
        report = json.loads(result.stdout)
        diagnostics = report["generalDiagnostics"]
        expected = {line for line, text in enumerate(
            (work / "invalid.py").read_text(encoding="utf-8").splitlines(), 1) if "# expect:" in text}
        actual = {item["range"]["start"]["line"] + 1 for item in diagnostics
                  if Path(item["file"]).name == "invalid.py" and item["severity"] == "error"}
        unexpected = [item for item in diagnostics
                      if Path(item["file"]).name != "invalid.py" or item["severity"] != "error"]
        if actual != expected or unexpected:
            raise RuntimeError("Pyright consumer contract failed:\n" + result.stdout)
        print("Pyright: fluent/editor inference and every invalid call passed.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    parser.add_argument("--pyright", action="store_true",
                        help="Also run Pyright (install pyright and Node.js in the checker environment)")
    args = parser.parse_args()
    wheel = args.wheel.resolve()
    with tempfile.TemporaryDirectory(prefix="typing-check-", dir=wheel.parent.parent) as directory:
        work = Path(directory)
        venv.EnvBuilder(with_pip=True).create(work / "venv")
        python = work / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        subprocess.run([str(python), "-I", "-m", "pip", "install", "--no-deps", "--no-index", str(wheel)],
                       cwd=work, env=env, check=True)
        check(python, work, env, pyright=args.pyright)


if __name__ == "__main__":
    main()
