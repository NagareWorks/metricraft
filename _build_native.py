"""Setuptools commands for a Python-independent Rust C ABI library."""
import json
import os
from pathlib import Path
import platform
import re
import shutil
import struct
import subprocess
import sys
import sysconfig

from setuptools.command.build_ext import build_ext
from setuptools.command.sdist import sdist
from setuptools.errors import CompileError
from wheel.bdist_wheel import bdist_wheel


ROOT = Path(__file__).resolve().parent
IDENTITY = "metricraft-source.json"


def source_identity():
    """An sdist preserves provenance even when extracted outside a Git checkout."""
    saved = ROOT / IDENTITY
    if saved.is_file():
        return json.loads(saved.read_text(encoding="utf-8"))
    try:
        def git(*args):
            return subprocess.check_output(
                ["git", "-C", str(ROOT), *args], stderr=subprocess.DEVNULL,
                text=True).strip()
        if Path(git("rev-parse", "--show-toplevel")).resolve() != ROOT:
            raise ValueError("Not the project checkout")
        return {"source_commit": git("rev-parse", "HEAD"),
                "source_dirty": bool(git("status", "--porcelain"))}
    except (OSError, ValueError, subprocess.CalledProcessError):
        return {"source_commit": None, "source_dirty": True}


def library_name():
    if sys.platform == "win32":
        return "metricraft_ffi.dll"
    if sys.platform == "darwin":
        return "libmetricraft_ffi.dylib"
    return "libmetricraft_ffi.so"


def normalize_arch(arch):
    aliases = {"amd64": "x86_64", "arm64": "aarch64", "i386": "i686",
               "i486": "i686", "i586": "i686", "riscv64gc": "riscv64",
               "ppc": "powerpc", "ppc64": "powerpc64", "ppc64le": "powerpc64le"}
    if arch.startswith(("armv", "thumbv")):
        return "arm"
    return aliases.get(arch, arch)


def interpreter_arch():
    tag = sysconfig.get_platform().lower()
    arch = tag.rsplit("-", 1)[-1]
    if tag == "win32":
        arch = "i686"
    elif sys.platform == "darwin":
        # A universal Python executable is still running one architecture.
        arch = platform.machine().lower()
    arch = normalize_arch(arch)
    if arch == "x86_64" and struct.calcsize("P") == 4:
        arch = "i686"
    return arch


class NativeBuild(build_ext):
    def get_ext_filename(self, fullname):
        # A ctypes library has no CPython version suffix or initialization symbol.
        return os.path.join(*fullname.split(".")[:-1], library_name())

    def build_extension(self, ext):
        if not shutil.which("cargo") or not shutil.which("rustc"):
            raise CompileError(
                "Building MetriCraft from source requires Rust (cargo and rustc) "
                "and a platform C linker. Install Rust, or use a matching native wheel.")
        version = subprocess.check_output(["rustc", "-vV"], text=True)
        target = re.search(r"^host: (.+)$", version, re.MULTILINE).group(1)
        rust_arch = normalize_arch(target.split("-", 1)[0])
        if rust_arch != interpreter_arch():
            raise CompileError(
                "Rust toolchain target " + target + " does not match Python architecture "
                + interpreter_arch() + ". Use a Rust toolchain matching this Python interpreter.")
        # Each source install targets its current host. Release CI uses native runners.
        env = os.environ.copy()
        env.setdefault("CARGO_TARGET_DIR", str(Path(self.build_temp).resolve() / "cargo"))
        command = ["cargo", "build", "--manifest-path", str(ROOT / "Cargo.toml"),
                   "--locked", "--release", "--package", "metricraft-ffi",
                   "--target", target, "--message-format=json-render-diagnostics"]
        completed = subprocess.run(command, cwd=ROOT, env=env, text=True,
                                   stdout=subprocess.PIPE)
        artifacts = []
        for line in completed.stdout.splitlines():
            event = json.loads(line)
            if event.get("reason") == "compiler-message":
                print(event["message"].get("rendered", ""), file=sys.stderr)
            if (event.get("reason") == "compiler-artifact" and
                    event.get("target", {}).get("name") == "metricraft_ffi"):
                artifacts.extend(Path(p) for p in event.get("filenames", [])
                                 if Path(p).name == library_name())
        if completed.returncode or len(artifacts) != 1:
            raise CompileError("Cargo could not build the MetriCraft native library")
        destination = Path(self.get_ext_fullpath(ext.name))
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(artifacts[0], destination)
        identity = dict(source_identity(), target=target)
        (destination.parent / "build.json").write_text(
            json.dumps(identity, sort_keys=True) + "\n", encoding="utf-8")


class NativeWheel(bdist_wheel):
    def get_tag(self):
        # ctypes calls a C ABI; the payload is platform-specific, not CPython-specific.
        _, _, platform = super().get_tag()
        if sys.platform == "darwin" and platform.endswith("_universal2"):
            arch = "arm64" if interpreter_arch() == "aarch64" else interpreter_arch()
            platform = platform[:-len("universal2")] + arch
        return "py3", "none", platform


class SourceDistribution(sdist):
    def make_release_tree(self, base_dir, files):
        identity = source_identity()
        super().make_release_tree(base_dir, files)
        (Path(base_dir) / IDENTITY).write_text(
            json.dumps(identity, sort_keys=True) + "\n", encoding="utf-8")
