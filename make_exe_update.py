"""
Create Windows .exe update assets for GitHub Release.

Example:
    python make_exe_update.py --version 0.0.9 --exe dist/DataExchangeTools.exe
"""

import argparse
import hashlib
import json
import shutil
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_EXE = ROOT_DIR / "dist" / "DataExchangeTools.exe"
DEFAULT_OUT_DIR = ROOT_DIR / "release"
DEFAULT_BASE_URL = "https://github.com/manoth/data-exchange-tools/releases/latest/download"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_package(version: str, exe_path: Path, base_url: str, notes: str, out_dir: Path) -> tuple[Path, Path, str]:
    if not exe_path.exists():
        raise FileNotFoundError(f"ไม่พบไฟล์ exe: {exe_path}")
    if not base_url.startswith("https://"):
        raise ValueError("--base-url ต้องขึ้นต้นด้วย https://")

    out_dir.mkdir(parents=True, exist_ok=True)
    asset_name = "DataExchangeTools.exe"
    asset_path = out_dir / asset_name
    versioned_asset_path = out_dir / f"DataExchangeTools-v{version}.exe"
    manifest_path = out_dir / "latest.json"

    shutil.copy2(exe_path, asset_path)
    shutil.copy2(exe_path, versioned_asset_path)
    exe_sha256 = sha256_file(asset_path)

    manifest = {
        "version": version,
        "notes": notes,
        "windows_exe_url": f"{base_url.rstrip('/')}/{asset_name}",
        "windows_exe_sha256": exe_sha256,
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return asset_path, manifest_path, exe_sha256


def main() -> None:
    parser = argparse.ArgumentParser(description="Create Windows exe update assets and latest.json")
    parser.add_argument("--version", required=True, help="Version in latest.json, for example 0.0.9")
    parser.add_argument("--exe", default=str(DEFAULT_EXE), help="Path to built DataExchangeTools.exe")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="GitHub Release/latest download base URL")
    parser.add_argument(
        "--notes",
        default="Windows exe update",
        help="Release notes shown in update status",
    )
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Output directory")
    args = parser.parse_args()

    asset_path, manifest_path, exe_sha256 = build_package(
        version=args.version,
        exe_path=Path(args.exe).resolve(),
        base_url=args.base_url,
        notes=args.notes,
        out_dir=Path(args.out_dir).resolve(),
    )
    print(f"Created: {asset_path}")
    print(f"Created: {manifest_path}")
    print(f"SHA256:  {exe_sha256}")


if __name__ == "__main__":
    main()
