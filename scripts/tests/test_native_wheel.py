"""Failure contracts for the wheel assembly and release validation boundary."""
import csv
import io
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_native_wheel import bundle
from check_native_wheel import verify


class NativeWheelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.staging = self.root / "staging"
        self.staging.mkdir()
        self.source = self.staging / "metricraft-0.3.0-py3-none-any.whl"
        with zipfile.ZipFile(self.source, "w") as wheel:
            wheel.writestr("metricraft/__init__.py", "")
            wheel.writestr("metricraft-0.3.0.dist-info/WHEEL",
                           "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n\n")
            wheel.writestr("metricraft-0.3.0.dist-info/RECORD", "")
        self.library = self.root / "metricraft_ffi.dll"
        self.library.write_bytes(b"native-test-payload")
        self.commit = "a" * 40

    def build(self, **changes):
        args = dict(staging=self.staging, library=self.library, platform="win_amd64",
                    target="x86_64-pc-windows-msvc", source_commit=self.commit,
                    output=self.root / "dist")
        args.update(changes)
        return bundle(**args)

    def rewrite(self, wheel, mutate):
        with zipfile.ZipFile(wheel) as archive:
            entries = {n: archive.read(n) for n in archive.namelist()}
        mutate(entries)
        with zipfile.ZipFile(wheel, "w") as archive:
            for name, data in entries.items():
                archive.writestr(name, data)

    def test_platform_metadata_and_record_are_consistent(self):
        wheel = self.build()
        self.assertEqual(verify(wheel, self.commit)["source_commit"], self.commit)

    def test_wrong_source_commit_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "source commit"):
            verify(self.build(), "b" * 40)

    def test_corrupted_library_is_rejected(self):
        wheel = self.build()
        self.rewrite(wheel, lambda entries: entries.update({"metricraft/native/metricraft_ffi.dll": b"changed"}))
        with self.assertRaisesRegex(ValueError, "integrity"):
            verify(wheel)

    def test_record_cannot_omit_a_file(self):
        wheel = self.build()
        def omit(entries):
            name = "metricraft-0.3.0.dist-info/RECORD"
            rows = list(csv.reader(io.StringIO(entries[name].decode())))
            output = io.StringIO()
            csv.writer(output).writerows(row for row in rows if row[0] != "metricraft/__init__.py")
            entries[name] = output.getvalue().encode()
        self.rewrite(wheel, omit)
        with self.assertRaisesRegex(ValueError, "every wheel entry"):
            verify(wheel)

    def test_wrong_platform_and_source_only_wheel_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "must agree"):
            self.build(platform="macosx_11_0_arm64")
        with self.assertRaisesRegex(ValueError, "platform wheel"):
            verify(self.source)

    def test_existing_artifact_is_not_overwritten(self):
        self.build()
        with self.assertRaises(FileExistsError):
            self.build()


if __name__ == "__main__":
    unittest.main()
