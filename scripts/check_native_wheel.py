"""Check platform wheel metadata, native payload identity and RECORD integrity."""
import argparse
import base64
import csv
from email.parser import BytesParser
import hashlib
import io
import json
from pathlib import Path
import zipfile

from build_native_wheel import TARGETS


def verify(wheel, source_commit=None):
    python_tag, abi, platform = wheel.stem.rsplit("-", 3)[1:]
    if python_tag != "py3" or abi != "none" or platform == "any":
        raise ValueError("Expected a py3-none platform wheel: " + wheel.name)
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        metadata_names = [n for n in names if n.endswith(".dist-info/WHEEL")]
        if len(metadata_names) != 1 or len(names) != len(set(names)):
            raise ValueError("Invalid or duplicate wheel entries")
        headers = BytesParser().parsebytes(archive.read(metadata_names[0]))
        expected_tags = {"py3-none-" + p for p in platform.split(".")}
        if headers["Root-Is-Purelib"] != "false" or set(headers.get_all("Tag", [])) != expected_tags:
            raise ValueError("Wheel filename and metadata tags disagree")
        manifest = json.loads(archive.read("metricraft/native/build.json"))
        target = manifest["target"]
        expected_platform, library = TARGETS[target]
        if source_commit and manifest["source_commit"] != source_commit:
            raise ValueError("Native artifact was built from a different source commit")
        platforms = platform.split(".")
        if target == "x86_64-unknown-linux-gnu":
            if not all(p.startswith("manylinux") and p.endswith("_x86_64") for p in platforms):
                raise ValueError("Linux distribution must pass auditwheel repair first")
        elif platform != expected_platform:
            raise ValueError("Native target and platform tag disagree")
        libraries = [n for n in names if n.startswith("metricraft/native/") and
                     n.endswith((".dll", ".so", ".dylib"))]
        if libraries != ["metricraft/native/" + library]:
            raise ValueError("Expected exactly one matching native library")
        record_name = metadata_names[0].rsplit("/", 1)[0] + "/RECORD"
        rows = list(csv.reader(io.StringIO(archive.read(record_name).decode())))
        # auditwheel may write explicit ZIP directory entries. RECORD describes
        # installed files, so directories must not participate in this check.
        files = {entry.filename for entry in archive.infolist() if not entry.is_dir()}
        if len(rows) != len(files) or {row[0] for row in rows} != files:
            raise ValueError("RECORD must list every wheel file exactly once")
        for name, digest, size in rows:
            if name == record_name:
                if digest or size:
                    raise ValueError("RECORD cannot hash itself")
                continue
            data = archive.read(name)
            actual = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip("=")
            if digest != "sha256=" + actual or size != str(len(data)):
                raise ValueError("RECORD integrity check failed: " + name)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dist", type=Path)
    parser.add_argument("--source-commit")
    args = parser.parse_args()
    wheels = list(args.dist.glob("*.whl"))
    if not wheels:
        raise SystemExit("No SDK wheel found; nothing is ready to publish.")
    for wheel in wheels:
        verify(wheel, args.source_commit)
        print("Verified " + wheel.name)


if __name__ == "__main__":
    main()
