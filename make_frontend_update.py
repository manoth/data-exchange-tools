"""
Build a frontend-only update package for Data Exchange Tools.

The generated latest.json can be uploaded to GitHub Release assets, an
internal HTTPS web server, or object storage that client machines can access
without signing in.
"""

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT_DIR = Path(__file__).resolve().parent
STATIC_DIR = ROOT_DIR / "static"
DEFAULT_OUT_DIR = ROOT_DIR / "release"
INCLUDE_PATTERNS = (
    "index.html",
    "css/*",
    "js/*",
    "images/*",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_static_files() -> list[Path]:
    files: list[Path] = []
    for pattern in INCLUDE_PATTERNS:
        files.extend(path for path in STATIC_DIR.glob(pattern) if path.is_file())
    return sorted(set(files))


def build_package(version: str, base_url: str, notes: str, out_dir: Path) -> tuple[Path, Path, str]:
    if not STATIC_DIR.exists():
        raise FileNotFoundError(f"Static directory not found: {STATIC_DIR}")

    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / f"frontend-{version}.zip"
    manifest_path = out_dir / "latest.json"

    with ZipFile(zip_path, "w", ZIP_DEFLATED) as zip_file:
        for path in collect_static_files():
            zip_file.write(path, path.relative_to(STATIC_DIR).as_posix())

    zip_sha256 = sha256_file(zip_path)
    manifest = {
        "version": version,
        "notes": notes,
        "frontend_zip_url": f"{base_url.rstrip('/')}/{zip_path.name}",
        "frontend_zip_sha256": zip_sha256,
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return zip_path, manifest_path, zip_sha256


def main() -> None:
    parser = argparse.ArgumentParser(description="Create frontend update zip and latest.json")
    parser.add_argument("--version", required=True, help="New frontend version, for example 0.0.6")
    parser.add_argument(
        "--base-url",
        required=True,
        help="HTTPS URL where frontend zip and latest.json will be hosted",
    )
    parser.add_argument("--notes", default="Frontend update", help="Update notes")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Output directory")
    args = parser.parse_args()

    if not args.base_url.startswith("https://"):
        raise SystemExit("--base-url must start with https://")

    zip_path, manifest_path, zip_sha256 = build_package(
        version=args.version,
        base_url=args.base_url,
        notes=args.notes,
        out_dir=Path(args.out_dir).resolve(),
    )
    print(f"Created: {zip_path}")
    print(f"Created: {manifest_path}")
    print(f"SHA256:  {zip_sha256}")


if __name__ == "__main__":
    main()
