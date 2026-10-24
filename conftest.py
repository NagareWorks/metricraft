"""Prevent a free-threaded CI job from silently testing with the GIL enabled."""
import os
import sys
import sysconfig

import pytest


def _check_free_threaded_runtime():
    if os.environ.get("METRICRAFT_REQUIRE_FREE_THREADED") != "1":
        return
    if sysconfig.get_config_var("Py_GIL_DISABLED") != 1:
        raise pytest.UsageError("This job requires a free-threaded CPython build")
    if getattr(sys, "_is_gil_enabled", lambda: True)():
        raise pytest.UsageError("The GIL must stay disabled for this test session")


def pytest_sessionstart(session):
    _check_free_threaded_runtime()


def pytest_sessionfinish(session, exitstatus):
    _check_free_threaded_runtime()
