# SPDX-License-Identifier: GPL-3.0-or-later
"""Local, value-suppressing audit of allowlisted files, ZIPs and Git metadata.

This is a practical check, not proof that every possible private value is absent.
Never print detected values; findings contain only relative file and category.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import zipfile

from build_release import ROOT, SOURCE_FILES

PATTERNS = {
    "personal_windows_location": re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+[^\\/\s]+", re.I),
    "personal_posix_location": re.compile(r"/(?:home|Users)/[^/\s]+"),
    "email": re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"),
    "private_key": re.compile(r"-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----"),
    "credential_token": re.compile(r"(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16})"),
    "bearer_secret": re.compile(r"Bearer\s+[A-Za-z0-9._-]{24,}"),
}


def scan(label, data, findings):
    try:
        content = data.decode("utf-8")
    except UnicodeDecodeError:
        findings.append({"file": label, "category": "unexpected_binary"})
        return
    for category, pattern in PATTERNS.items():
        if pattern.search(content):
            findings.append({"file": label, "category": category})
    username = os.environ.get("USERNAME", "")
    if username and len(username) >= 3 and re.search(r"(?<!\w)" + re.escape(username) + r"(?!\w)", content, re.I):
        findings.append({"file": label, "category": "local_user_identifier"})


def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True,
                          capture_output=True).stdout


def main():
    findings = []
    for name in SOURCE_FILES:
        scan(name, (ROOT / name).read_bytes(), findings)
    zip_count = 0
    for file in sorted((ROOT / "dist").glob("*.zip")):
        with zipfile.ZipFile(file) as archive:
            for info in archive.infolist():
                entry = Path(info.filename)
                if entry.is_absolute() or ".." in entry.parts or ".git" in entry.parts:
                    findings.append({"file": file.name, "category": "unsafe_archive_entry"})
                scan(file.name + ":" + info.filename, archive.read(info), findings)
        zip_count += 1
    metadata = {"repository": False}
    if (ROOT / ".git").is_dir():
        metadata = {"repository": True, "remote_count": len(git("remote").splitlines()),
                    "commits": len(git("rev-list", "--all").splitlines())}
        if metadata["remote_count"]:
            findings.append({"file": "git-metadata", "category": "remote_requires_review"})
        config = git("config", "--local", "--list").decode()
        config = re.sub(r"[\w.+-]+@users\.noreply\.github\.com", "PUBLIC_NOREPLY", config)
        scan("git:local-config", config.encode(), findings)
        for line in git("log", "--all", "--format=%an%x00%ae%x00%cn%x00%ce").decode().splitlines():
            fields = line.split("\x00")
            if len(fields) != 4 or any(not fields[i].endswith("@users.noreply.github.com") for i in (1, 3)):
                findings.append({"file": "git-metadata", "category": "non_noreply_identity"})
        for object_line in git("rev-list", "--objects", "--all").decode().splitlines():
            oid, _, name = object_line.partition(" ")
            kind = git("cat-file", "-t", oid).strip()
            if kind == b"blob":
                scan("git:" + name, git("cat-file", "-p", oid), findings)
            elif kind == b"commit":
                content = git("cat-file", "-p", oid).decode()
                # Identity is checked above; suppress only the verified noreply email.
                content = re.sub(r"[\w.+-]+@users\.noreply\.github\.com", "PUBLIC_NOREPLY", content)
                scan("git:commit", content.encode(), findings)
    output = {"audit_version": 1, "source_files": len(SOURCE_FILES), "zip_files": zip_count,
              "git": metadata, "findings": findings,
              "status": "PASS" if not findings else "REVIEW_REQUIRED",
              "limitations": "Pattern scan plus manual review; not a complete anonymity guarantee"}
    (ROOT / "dist" / "privacy-audit.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))
    raise SystemExit(bool(findings))


if __name__ == "__main__":
    main()
