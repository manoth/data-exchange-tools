#!/usr/bin/env python3
"""Verify that required frontend files are embedded in a PyInstaller EXE."""

import argparse
from pathlib import Path

from PyInstaller.archive.readers import CArchiveReader


REQUIRED_FILES = ("static/index.html",)


def normalized_archive_names(exe_path: Path) -> set[str]:
    archive = CArchiveReader(str(exe_path))
    return {name.replace("\\", "/").lstrip("./") for name in archive.toc}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("exe", type=Path)
    args = parser.parse_args()

    exe_path = args.exe.resolve()
    if not exe_path.is_file():
        raise SystemExit(f"Bundle check failed: executable not found: {exe_path}")

    try:
        names = normalized_archive_names(exe_path)
    except Exception as exc:
        raise SystemExit(f"Bundle check failed: cannot inspect executable: {exc}") from exc

    missing = [name for name in REQUIRED_FILES if name not in names]
    if missing:
        raise SystemExit(
            "Bundle check failed: required frontend file is missing: " + ", ".join(missing)
        )

    print("Bundle check passed: static/index.html is embedded in the executable")


if __name__ == "__main__":
    main()
