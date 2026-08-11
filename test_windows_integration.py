import unittest
from unittest.mock import patch

from main import _configure_standard_streams, _same_directory


class ReconfigurableStream:
    def __init__(self):
        self.options = None

    def reconfigure(self, **options):
        self.options = options


class WindowsIntegrationTests(unittest.TestCase):
    def test_startup_reconfigures_cp874_compatible_streams_before_printing(self):
        stdout = ReconfigurableStream()
        stderr = ReconfigurableStream()
        with patch("main.sys.stdout", stdout), patch("main.sys.stderr", stderr):
            _configure_standard_streams()

        self.assertEqual(stdout.options, {"encoding": "utf-8", "errors": "replace"})
        self.assertEqual(stderr.options, {"encoding": "utf-8", "errors": "replace"})

    def test_executable_on_desktop_is_detected(self):
        self.assertTrue(
            _same_directory(
                "/Users/demo/Desktop/DataExchangeTools.exe",
                "/Users/demo/Desktop",
            )
        )

    def test_executable_outside_desktop_keeps_shortcut(self):
        self.assertFalse(
            _same_directory(
                "/Users/demo/Downloads/DataExchangeTools.exe",
                "/Users/demo/Desktop",
            )
        )


if __name__ == "__main__":
    unittest.main()
