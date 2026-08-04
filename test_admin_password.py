import json
import os
import tempfile
import unittest
from unittest.mock import patch

import config


class AdminPasswordTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.admin_file = os.path.join(self.temp_dir.name, "admin.json")
        admin = {
            "username": "admin",
            "password_hash": config._hash_password("OldPass1!"),
            "must_change_password": False,
        }
        with open(self.admin_file, "w", encoding="utf-8") as handle:
            json.dump(admin, handle)
        self.admin_file_patch = patch.object(config, "ADMIN_FILE", self.admin_file)
        self.admin_file_patch.start()

    def tearDown(self):
        self.admin_file_patch.stop()
        self.temp_dir.cleanup()

    def test_rejects_incorrect_old_password_without_changing_password(self):
        result = config.change_admin_password("WrongPass1!", "NewPass2@")

        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "รหัสผ่านเดิมไม่ถูกต้อง")
        self.assertIsNotNone(config.authenticate_admin("admin", "OldPass1!"))
        self.assertIsNone(config.authenticate_admin("admin", "NewPass2@"))

    def test_changes_password_only_after_old_password_is_verified(self):
        result = config.change_admin_password("OldPass1!", "NewPass2@")

        self.assertTrue(result["success"])
        self.assertIsNone(config.authenticate_admin("admin", "OldPass1!"))
        self.assertIsNotNone(config.authenticate_admin("admin", "NewPass2@"))


if __name__ == "__main__":
    unittest.main()
