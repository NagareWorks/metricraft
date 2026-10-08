"""Benchmark failures must leave useful reports and never turn the job green."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_benchmarks as runner


class BenchmarkRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / "report"
        self.target = self.root / "target"
        (self.target / "release").mkdir(parents=True)
        for filename in ("metricraft_ffi.dll", "libmetricraft_ffi.so", "libmetricraft_ffi.dylib"):
            (self.target / "release" / filename).write_bytes(b"test payload")

    def test_reports_survive_downstream_failure_with_partial_json(self):
        calls = []

        def fail_timing(command, **kwargs):
            calls.append(command)
            if "benchmark_shapes" in command:
                kwargs["stdout"].write('{"unfinished":')
                kwargs["stderr"].write("native timing process failed\n")
                raise subprocess.CalledProcessError(42, command)
            return subprocess.CompletedProcess(command, 0)

        with patch.object(runner, "provenance", return_value={"revision": "test"}), \
                patch.dict(runner.os.environ, {"CARGO_TARGET_DIR": str(self.target)}), \
                patch.object(runner.subprocess, "run", side_effect=fail_timing), \
                contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(subprocess.CalledProcessError) as error:
                runner.main(["--output", str(self.output)])
        self.assertEqual(error.exception.returncode, 42)
        report = json.loads((self.output / "report.json").read_text())
        self.assertEqual(report["status"], "failed")
        self.assertEqual([s["status"] for s in report["steps"]], ["passed", "passed", "failed"])
        self.assertEqual(len(calls), 3)
        self.assertIn("rust-timings | failed", (self.output / "summary.md").read_text(encoding="utf-8"))
        self.assertIn("native timing process failed", (self.output / "rust-timings.log").read_text())

    def test_setup_failure_is_recorded_before_any_benchmark(self):
        with patch.object(runner, "provenance", side_effect=OSError("git unavailable")), \
                contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(OSError, "git unavailable"):
                runner.main(["--output", str(self.output)])
        report = json.loads((self.output / "report.json").read_text())
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["steps"], [])
        self.assertIn("git unavailable", (self.output / "summary.md").read_text(encoding="utf-8"))

    def test_rejects_mixed_reports_checkout_outputs_and_unbounded_durations(self):
        self.output.mkdir()
        previous = self.output / "previous.json"
        previous.write_text("keep this run")
        cases = [
            ["--output", str(self.output)],
            ["--output", str(runner.ROOT / "benchmark-output")],
            ["--output", str(self.root / "fresh"), "--memory-seconds", "nan"],
            ["--output", str(self.root / "fresh"), "--memory-seconds", "inf"],
        ]
        with patch.object(runner.subprocess, "run") as execute, contextlib.redirect_stderr(io.StringIO()):
            for args in cases:
                with self.subTest(args=args), self.assertRaises(SystemExit) as error:
                    runner.main(args)
                self.assertEqual(error.exception.code, 2)
        execute.assert_not_called()
        self.assertEqual(previous.read_text(), "keep this run")
        self.assertFalse((self.root / "fresh").exists())


if __name__ == "__main__":
    unittest.main()
