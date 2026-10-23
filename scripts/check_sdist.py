"""Rebuild a complete sdist outside the checkout and test its installed native SDK."""
import argparse
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dist", type=Path)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()
    dist = args.dist.resolve()
    sources = list(dist.glob("metricraft-*.tar.gz"))
    if len(sources) != 1:
        raise SystemExit("Expected exactly one MetriCraft sdist")
    with tempfile.TemporaryDirectory(prefix="sdist-check-", dir=dist.parent) as work:
        work = Path(work)
        with tarfile.open(sources[0]) as archive:
            names = archive.getnames()
            root = names[0].split("/")[0]
            for required in ("Cargo.toml", "Cargo.lock", "setup.py", "_build_native.py",
                             "crates/metricraft-core/src/lib.rs",
                             "crates/metricraft-ffi/src/lib.rs", "metricraft-source.json",
                             "python/metricraft/src/metricraft/py.typed"):
                assert root + "/" + required in names, "sdist is missing " + required
            assert not any("/_legacy/" in name or "/target/" in name or "/.git/" in name
                           or name.endswith((".dll", ".so", ".dylib")) for name in names)
            for member in archive.getmembers():
                path = PurePosixPath(member.name)
                if (path.is_absolute() or ".." in path.parts or "\\" in member.name
                        or not (member.isfile() or member.isdir())):
                    raise ValueError("Unsafe sdist entry: " + member.name)
                destination = work.joinpath(*path.parts)
                if member.isdir():
                    destination.mkdir(parents=True, exist_ok=True)
                else:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(archive.extractfile(member).read())
        source = work / root
        identity = json.loads((source / "metricraft-source.json").read_text())
        assert identity == {"source_commit": args.source_commit, "source_dirty": False}
        env = os.environ.copy()
        for name in ("PYTHONPATH", "METRICRAFT_NATIVE_LIB", "SETUPTOOLS_SCM_PRETEND_VERSION"):
            env.pop(name, None)
        env["CARGO_TARGET_DIR"] = str(work / "cargo-target")
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        wheels = work / "wheels"
        subprocess.run([sys.executable, "-m", "build", "--wheel", str(source),
                        "--outdir", str(wheels)], cwd=work, env=env, check=True)
        wheel, = wheels.glob("*.whl")
        assert "-py3-none-" in wheel.name and not wheel.name.endswith("-any.whl")
        with zipfile.ZipFile(wheel) as archive:
            manifest = json.loads(archive.read("metricraft/native/build.json"))
            assert manifest["source_commit"] == args.source_commit
            assert manifest["source_dirty"] is False
        subprocess.run([sys.executable, str(ROOT / "scripts/check_python_package.py"),
                        str(wheels), "--require-bundled-native"],
                       cwd=work, env=env, check=True)
        print("Source archive rebuilt and installed successfully outside the checkout.")


if __name__ == "__main__":
    main()
