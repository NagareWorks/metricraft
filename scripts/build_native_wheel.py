"""Bundle a same-commit C ABI library into a platform-tagged Python wheel.

The packaging sequence follows the existing native artifact workflow: build a
staging wheel, add one platform's library, rewrite wheel metadata and RECORD,
then validate the installed result. Linux policy tags are assigned by auditwheel.
"""
import argparse
import base64
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile


TARGETS = {
    "x86_64-unknown-linux-gnu": ("linux_x86_64", "libmetricraft_ffi.so"),
    "x86_64-pc-windows-msvc": ("win_amd64", "metricraft_ffi.dll"),
    "x86_64-apple-darwin": ("macosx_11_0_x86_64", "libmetricraft_ffi.dylib"),
    "aarch64-apple-darwin": ("macosx_11_0_arm64", "libmetricraft_ffi.dylib"),
}


def bundle(staging, library, platform, target, source_commit, output):
    if TARGETS.get(target) != (platform, library.name):
        raise ValueError("Native target, library name and wheel platform must agree")
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise ValueError("source_commit must be a full Git SHA")
    wheels = list(staging.glob("metricraft-*-py3-none-any.whl"))
    if len(wheels) != 1:
        raise ValueError("Expected one source-only staging wheel")
    with zipfile.ZipFile(wheels[0]) as archive:
        if any(n.startswith("metricraft/native/") for n in archive.namelist()):
            raise ValueError("Staging wheel already contains native payloads")
        entries = {n: archive.read(n) for n in archive.namelist()}
    metadata = [n for n in entries if n.endswith(".dist-info/WHEEL")]
    if len(metadata) != 1:
        raise ValueError("Expected one wheel metadata directory")
    wheel_meta = metadata[0]
    record = wheel_meta.rsplit("/", 1)[0] + "/RECORD"
    entries.pop(record, None)
    entries["metricraft/native/" + library.name] = library.read_bytes()
    entries["metricraft/native/build.json"] = (json.dumps({
        "source_commit": source_commit, "target": target,
    }, sort_keys=True) + "\n").encode()
    headers = [line for line in entries[wheel_meta].decode().splitlines()
               if line and not line.startswith(("Tag:", "Root-Is-Purelib:"))]
    headers += ["Root-Is-Purelib: false", "Tag: py3-none-" + platform]
    entries[wheel_meta] = ("\n".join(headers) + "\n").encode()
    records = io.StringIO(newline="")
    writer = csv.writer(records, lineterminator="\n")
    for name, data in sorted(entries.items()):
        digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip("=")
        writer.writerow([name, "sha256=" + digest, str(len(data))])
    writer.writerow([record, "", ""])
    entries[record] = records.getvalue().encode()
    output.mkdir(parents=True, exist_ok=True)
    destination = output / wheels[0].name.replace("-any.whl", "-" + platform + ".whl")
    # A rerun must select a fresh artifact directory rather than overwrite a wheel.
    with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(entries.items()):
            archive.writestr(name, data)
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staging", type=Path, required=True)
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--platform", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(bundle(args.staging, args.library, args.platform, args.target, args.source_commit, args.output))
