#!/usr/bin/env python3
"""Fail fast when release-facing version strings or Python files disagree."""

import argparse
import py_compile
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def require_pattern(path: Path, pattern: str, description: str) -> None:
    content = path.read_text(encoding="utf-8")
    if not re.search(pattern, content):
        raise SystemExit(f"Release check failed: {description} in {path.relative_to(ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    version = args.version.strip()
    escaped = re.escape(version)

    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise SystemExit("Release version must use X.Y.Z format")

    require_pattern(ROOT / "main.py", rf'APP_VERSION\s*=\s*"{escaped}"', "main version mismatch")
    require_pattern(
        ROOT / "transform.py",
        rf'APP_VERSION\s*=\s*os\.environ\.get\("APP_VERSION",\s*"{escaped}"\)',
        "transform version mismatch",
    )
    require_pattern(ROOT / "static" / "index.html", rf">v{escaped}<", "footer version mismatch")
    require_pattern(ROOT / "static" / "index.html", rf"\?v={escaped}", "static cache version mismatch")

    notes = ROOT / f"RELEASE_NOTES_v{version}.md"
    checklist = ROOT / f"RELEASE_CHECKLIST_v{version}.md"
    build_script = ROOT / "scripts" / f"build_release_{version.replace('.', '_')}.ps1"
    if not notes.is_file():
        raise SystemExit(f"Release check failed: missing {notes.name}")
    if not checklist.is_file():
        raise SystemExit(f"Release check failed: missing {checklist.name}")
    if not build_script.is_file():
        raise SystemExit(f"Release check failed: missing {build_script.relative_to(ROOT)}")
    try:
        build_script.read_bytes().decode("ascii")
    except UnicodeDecodeError:
        raise SystemExit(
            "Release check failed: PowerShell build script must contain ASCII only "
            "for Windows PowerShell 5.1 compatibility"
        )

    for path in sorted(ROOT.glob("*.py")) + sorted((ROOT / "scripts").glob("*.py")):
        py_compile.compile(str(path), doraise=True)

    print(f"Release checks passed for v{version}")


if __name__ == "__main__":
    main()
