import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import windows_launcher


class WindowsLauncherTests(unittest.TestCase):
    def test_install_executable_uses_stable_per_user_program_directory(self):
        executable = windows_launcher.get_install_executable({
            "LOCALAPPDATA": r"C:\Users\Demo\AppData\Local",
        })

        self.assertEqual(
            executable,
            Path(r"C:\Users\Demo\AppData\Local") / "Programs" / "DataExchangeTools" / "DataExchangeTools.exe",
        )

    def test_parses_legacy_frontend_version_only_for_our_product(self):
        self.assertEqual(
            windows_launcher.parse_legacy_frontend_version(
                '<title>Data Exchange Tools</title><span class="version-text">v0.1.8</span>'
            ),
            "0.1.8",
        )
        self.assertEqual(windows_launcher.parse_legacy_frontend_version("<title>Other App</title>v9.9.9"), "")

    def test_parses_windows_netstat_listener_pid(self):
        output = "  TCP    0.0.0.0:8899    0.0.0.0:0    LISTENING    4321\n"
        self.assertEqual(windows_launcher.parse_netstat_listener_pid(output, 8899), 4321)

    def test_removes_only_generated_shortcut_beside_desktop_launcher(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            profile = Path(temp_dir)
            desktop = profile / "Desktop"
            desktop.mkdir()
            launcher = desktop / "DataExchangeTools.exe"
            launcher.write_bytes(b"launcher")
            shortcut = desktop / "Data Exchange Tools.url"
            shortcut.write_text(
                "[InternetShortcut]\nURL=http://localhost:8899\n",
                encoding="utf-8",
            )

            windows_launcher.cleanup_duplicate_desktop_shortcut(
                str(launcher),
                "http://localhost:8899",
                {"USERPROFILE": str(profile)},
            )

            self.assertFalse(shortcut.exists())

    def test_running_same_version_only_opens_browser(self):
        with patch.object(
            windows_launcher,
            "probe_service",
            return_value={"running": True, "recognized": True, "version": "0.1.9", "pid": 100},
        ), patch.object(windows_launcher.webbrowser, "open") as open_browser, patch.object(
            windows_launcher, "stop_service"
        ) as stop_service, patch.object(windows_launcher, "register_launcher_path") as register:
            result = windows_launcher.run_windows_launcher(
                "0.1.9", "http://localhost:8899", 8899, "data", "launcher.exe"
            )

        self.assertEqual(result, 0)
        open_browser.assert_called_once_with("http://localhost:8899")
        stop_service.assert_not_called()
        register.assert_called_once_with("data", "launcher.exe")

    def test_newer_launcher_replaces_old_service_then_opens_browser(self):
        service_exe = Path("installed/DataExchangeTools.exe")
        with patch.object(
            windows_launcher,
            "probe_service",
            return_value={"running": True, "recognized": True, "version": "0.1.8", "pid": 100},
        ), patch.object(windows_launcher, "stop_service", return_value=True) as stop_service, patch.object(
            windows_launcher, "prepare_service_executable", return_value=(service_exe, "0.1.9")
        ) as prepare, patch.object(windows_launcher, "start_service") as start, patch.object(
            windows_launcher, "wait_for_service", return_value=True
        ), patch.object(windows_launcher.webbrowser, "open") as open_browser:
            result = windows_launcher.run_windows_launcher(
                "0.1.9", "http://localhost:8899", 8899, "data", "launcher.exe"
            )

        self.assertEqual(result, 0)
        stop_service.assert_called_once_with("http://localhost:8899", 8899, "data", 100)
        prepare.assert_called_once_with("launcher.exe", "0.1.9", "data")
        start.assert_called_once_with(service_exe)
        open_browser.assert_called_once_with("http://localhost:8899")

    def test_installed_newer_version_is_not_downgraded(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "launcher.exe"
            target = root / "installed" / "DataExchangeTools.exe"
            data_dir = root / "data"
            target.parent.mkdir()
            data_dir.mkdir()
            source.write_bytes(b"old-launcher")
            target.write_bytes(b"new-installed")
            (data_dir / windows_launcher.INSTALL_STATE_FILENAME).write_text(
                '{"version":"0.2.0"}', encoding="utf-8"
            )

            with patch.object(windows_launcher, "get_install_executable", return_value=target):
                selected, version = windows_launcher.prepare_service_executable(
                    str(source), "0.1.9", str(data_dir)
                )

            self.assertEqual(selected, target.resolve())
            self.assertEqual(version, "0.2.0")
            self.assertEqual(target.read_bytes(), b"new-installed")

    def test_portable_launcher_is_copied_to_stable_location(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "download" / "DataExchangeTools.exe"
            target = root / "local-app-data" / "Programs" / "DataExchangeTools" / "DataExchangeTools.exe"
            data_dir = root / "local-app-data" / "DataExchangeTools"
            source.parent.mkdir()
            source.write_bytes(b"portable-one-file-executable")

            with patch.object(windows_launcher, "get_install_executable", return_value=target):
                selected, version = windows_launcher.prepare_service_executable(
                    str(source), "0.1.10", str(data_dir)
                )

            source.unlink()
            self.assertEqual(selected, target.resolve())
            self.assertEqual(version, "0.1.10")
            self.assertEqual(target.read_bytes(), b"portable-one-file-executable")
            self.assertTrue((data_dir / windows_launcher.INSTALL_STATE_FILENAME).is_file())


if __name__ == "__main__":
    unittest.main()
