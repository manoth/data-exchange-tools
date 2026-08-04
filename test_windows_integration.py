import unittest

from main import _same_directory


class WindowsIntegrationTests(unittest.TestCase):
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
