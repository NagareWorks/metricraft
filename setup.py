"""Build the ctypes library with the same source as the Python distribution."""
from pathlib import Path
import sys

from setuptools import Extension, setup

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _build_native import NativeBuild, NativeWheel, SourceDistribution

setup(
    ext_modules=[Extension("metricraft.native.metricraft_ffi", sources=[])],
    cmdclass={"build_ext": NativeBuild, "bdist_wheel": NativeWheel,
              "sdist": SourceDistribution},
)
