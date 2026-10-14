# SPDX-License-Identifier: GPL-3.0-or-later
"""Build deterministic allowlisted ZIPs. No .git, logs, caches or blend files."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILES = (
    ".gitignore", "LICENSE", "README.md", "README.ja.md",
    "blender_parts_check/__init__.py", "blender_parts_check/adapter.py",
    "blender_parts_check/blender_manifest.toml", "blender_parts_check/core.py",
    "blender_parts_check/ui.py", "docs/DESIGN.md", "docs/VALIDATION.md",
    "examples/README.md", "examples/run_synthetic.py", "examples/sample-report.json",
    "tests/test_core.py", "tests/blender_integration.py",
    "tools/build_release.py", "tools/audit_public.py",
)


def build_zip(path, entries):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source, target in sorted(entries):
            file = ROOT / source
            if file.is_symlink() or not file.is_file():
                raise ValueError("Release allowlist contains a missing or linked file")
            info = zipfile.ZipInfo(target, date_time=(2026, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, file.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def main():
    output = ROOT / "dist"
    output.mkdir(exist_ok=True)
    source = output / "blender-parts-check-source-0.1.0.zip"
    extension = output / "blender_parts_check-0.1.0.zip"
    build_zip(source, [(s, "blender-parts-check/" + s) for s in SOURCE_FILES])
    addon_entries = [(s, s.split("/", 1)[1]) for s in SOURCE_FILES if s.startswith("blender_parts_check/")]
    addon_entries += [(s, s) for s in ("LICENSE", "README.md", "README.ja.md", "docs/DESIGN.md",
                                     "examples/README.md", "examples/sample-report.json")]
    build_zip(extension, addon_entries)
    inventory = {s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for s in sorted(SOURCE_FILES)}
    (output / "SOURCE-MANIFEST.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    hashes = {f.name: hashlib.sha256(f.read_bytes()).hexdigest()
              for f in (source, extension, output / "SOURCE-MANIFEST.json")}
    (output / "SHA256SUMS.txt").write_text("".join(f"{digest}  {name}\n" for name, digest in hashes.items()), encoding="utf-8")
    print(json.dumps({"source_files": len(SOURCE_FILES), "sha256": hashes}, indent=2))


if __name__ == "__main__":
    main()
