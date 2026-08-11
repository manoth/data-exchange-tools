import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from build_exe import configure_standard_streams, create_pyinstaller_command


class ReconfigurableStream:
    def __init__(self):
        self.options = None

    def reconfigure(self, **options):
        self.options = options


class BuildExeCommandTests(unittest.TestCase):
    def test_build_output_uses_utf8_on_windows_code_pages(self):
        stdout = ReconfigurableStream()
        stderr = ReconfigurableStream()
        with patch("build_exe.sys.stdout", stdout), patch("build_exe.sys.stderr", stderr):
            configure_standard_streams()

        self.assertEqual(stdout.options, {"encoding": "utf-8", "errors": "replace"})
        self.assertEqual(stderr.options, {"encoding": "utf-8", "errors": "replace"})

    def test_static_frontend_uses_pyinstaller_source_dest_separator(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "main.py").write_text("", encoding="utf-8")
            (root / "static").mkdir()
            (root / "static" / "index.html").write_text("<!doctype html>", encoding="utf-8")

            command = create_pyinstaller_command(str(root))
            add_data_args = [item for item in command if item.startswith("--add-data=")]

            self.assertEqual(add_data_args, [f"--add-data={root / 'static'}:static"])
            self.assertNotIn(f"--add-data={root / 'static'};static", command)

    def test_missing_static_index_stops_build(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "main.py").write_text("", encoding="utf-8")
            (root / "static").mkdir()

            with self.assertRaises(FileNotFoundError):
                create_pyinstaller_command(str(root))


if __name__ == "__main__":
    unittest.main()
