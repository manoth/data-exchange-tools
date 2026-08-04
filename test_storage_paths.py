import os
import tempfile
import unittest
from pathlib import Path

from config import migrate_legacy_state, resolve_app_dir


class StoragePathTests(unittest.TestCase):
    def test_windows_frozen_app_uses_local_app_data(self):
        result = resolve_app_dir(
            data_dir="",
            frozen=True,
            executable=r"C:\Users\Demo\Desktop\DataExchangeTools.exe",
            platform_name="nt",
            environ={"LOCALAPPDATA": r"C:\Users\Demo\AppData\Local"},
            source_dir=r"C:\source",
        )

        self.assertEqual(
            result,
            os.path.join(r"C:\Users\Demo\AppData\Local", "DataExchangeTools"),
        )

    def test_data_dir_override_remains_supported(self):
        result = resolve_app_dir(
            data_dir="custom-data",
            frozen=True,
            executable="ignored.exe",
            platform_name="nt",
            environ={},
            source_dir="source",
        )

        self.assertTrue(result.endswith("custom-data"))

    def test_migration_copies_state_without_overwriting_destination(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            legacy = root / "legacy"
            target = root / "target"
            legacy.mkdir()
            target.mkdir()
            (legacy / ".key").write_text("legacy-key", encoding="utf-8")
            (legacy / "config.json").write_text("legacy-config", encoding="utf-8")
            (target / "config.json").write_text("current-config", encoding="utf-8")

            migrated = migrate_legacy_state(str(legacy), str(target))

            self.assertEqual(migrated, [".key"])
            self.assertEqual((target / ".key").read_text(encoding="utf-8"), "legacy-key")
            self.assertEqual((target / "config.json").read_text(encoding="utf-8"), "current-config")
            self.assertTrue((legacy / ".key").exists())


if __name__ == "__main__":
    unittest.main()
