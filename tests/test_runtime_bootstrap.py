"""Tests for the per-user runtime bootstrap module."""

from __future__ import annotations

import site
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from webcam_micro.runtime_bootstrap import (
    RuntimeBootstrapPlan,
    _bridge_import_roots,
    _runtime_root,
    _write_import_bridge,
    bootstrap_runtime,
    build_runtime_bootstrap_plan,
)


class RuntimeBootstrapModuleTest(unittest.TestCase):
    """Verify the runtime bootstrap contract and helper wiring."""

    def test_runtime_bootstrap_symbols_stay_explicit(self) -> None:
        """Assert the public bootstrap symbols keep their contract names."""

        self.assertEqual(
            "RuntimeBootstrapPlan",
            RuntimeBootstrapPlan.__name__,
        )
        self.assertTrue(callable(build_runtime_bootstrap_plan))
        self.assertTrue(callable(bootstrap_runtime))

    def test_bridge_import_roots_include_the_current_site_packages(
        self,
    ) -> None:
        """Assert the bridge keeps the active package site path visible."""

        site_packages = Path(site.getsitepackages()[0]).resolve()

        self.assertIn(
            site_packages,
            _bridge_import_roots(Path("/tmp/webcam-micro-runtime")),
        )

    def test_runtime_root_uses_the_expected_user_directory(self) -> None:
        """Assert the runtime root follows the supported OS layouts."""

        with self.subTest("macos"):
            with (
                mock.patch(
                    "webcam_micro.runtime_bootstrap.sys.platform",
                    "darwin",
                ),
                mock.patch(
                    "webcam_micro.runtime_bootstrap.Path.home",
                    return_value=Path("/Users/test"),
                ),
            ):
                self.assertEqual(
                    Path(
                        "/Users/test/Library/Application Support/"
                        "webcam-micro/python-runtime"
                    ),
                    _runtime_root(),
                )

        with self.subTest("windows"):
            with (
                mock.patch(
                    "webcam_micro.runtime_bootstrap.sys.platform",
                    "win32",
                ),
                mock.patch.dict(
                    "webcam_micro.runtime_bootstrap.os.environ",
                    {"LOCALAPPDATA": r"C:\Users\test\AppData\Local"},
                    clear=True,
                ),
            ):
                self.assertEqual(
                    Path(r"C:\Users\test\AppData\Local")
                    / "webcam-micro"
                    / "python-runtime",
                    _runtime_root(),
                )

        with self.subTest("linux"):
            with (
                mock.patch(
                    "webcam_micro.runtime_bootstrap.sys.platform",
                    "linux",
                ),
                mock.patch.dict(
                    "webcam_micro.runtime_bootstrap.os.environ",
                    {"XDG_DATA_HOME": "/home/test/.local/share"},
                    clear=True,
                ),
            ):
                self.assertEqual(
                    Path(
                        "/home/test/.local/share/webcam-micro/python-runtime"
                    ),
                    _runtime_root(),
                )

    def test_write_import_bridge_records_runtime_paths(self) -> None:
        """Assert the .pth bridge preserves the current import roots."""

        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_site_packages = Path(temp_dir) / "site-packages"
            import_roots = (
                Path("/opt/site-packages"),
                Path("/Users/test/project"),
            )

            _write_import_bridge(runtime_site_packages, import_roots)

            bridge_file = runtime_site_packages / "webcam_micro_runtime.pth"
            self.assertTrue(bridge_file.exists())
            self.assertEqual(
                "/opt/site-packages\n/Users/test/project\n",
                bridge_file.read_text(encoding="utf-8"),
            )

    def test_bootstrap_runtime_relaunches_through_the_private_python(
        self,
    ) -> None:
        """Assert the bootstrap path creates the bridge and re-execs."""

        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_root = Path(temp_dir) / "runtime"
            runtime_python = runtime_root / "bin" / "python"
            runtime_site_packages = (
                runtime_root / "lib" / "python3.14" / ("site-packages")
            )
            runtime_site_packages.mkdir(parents=True, exist_ok=True)

            plan = RuntimeBootstrapPlan(
                runtime_root=runtime_root,
                runtime_python=runtime_python,
                runtime_site_packages=runtime_site_packages,
                import_roots=(
                    Path("/opt/site-packages"),
                    Path("/Users/test/project"),
                ),
                needs_runtime_creation=True,
                needs_relaunch=True,
                macos_info_plist=None,
            )

            with (
                mock.patch(
                    "webcam_micro.runtime_bootstrap."
                    "build_runtime_bootstrap_plan",
                    return_value=plan,
                ),
                mock.patch(
                    "webcam_micro.runtime_bootstrap."
                    "_create_runtime_environment",
                ) as create_runtime_mock,
                mock.patch(
                    "webcam_micro.runtime_bootstrap.os.execv",
                ) as execv_mock,
            ):
                bootstrap_runtime(["--smoke-test"])

            create_runtime_mock.assert_called_once_with(runtime_root)
            self.assertTrue(
                (runtime_site_packages / "webcam_micro_runtime.pth").exists()
            )
            execv_mock.assert_called_once_with(
                str(runtime_python),
                [
                    str(runtime_python),
                    "-m",
                    "webcam_micro",
                    "--smoke-test",
                ],
            )

    def test_bootstrap_runtime_keeps_existing_bridge_when_reused(
        self,
    ) -> None:
        """Assert the runtime hop leaves the original bridge untouched."""

        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_root = Path(temp_dir) / "runtime"
            runtime_site_packages = (
                runtime_root / "lib" / "python3.14" / ("site-packages")
            )
            runtime_site_packages.mkdir(parents=True, exist_ok=True)
            bridge_file = runtime_site_packages / "webcam_micro_runtime.pth"
            bridge_file.write_text("/opt/site-packages\n", encoding="utf-8")

            plan = RuntimeBootstrapPlan(
                runtime_root=runtime_root,
                runtime_python=runtime_root / "bin" / "python",
                runtime_site_packages=runtime_site_packages,
                import_roots=(Path("/Users/test/project"),),
                needs_runtime_creation=False,
                needs_relaunch=False,
                macos_info_plist=None,
            )

            with (
                mock.patch(
                    "webcam_micro.runtime_bootstrap."
                    "build_runtime_bootstrap_plan",
                    return_value=plan,
                ),
                mock.patch(
                    "webcam_micro.runtime_bootstrap._write_import_bridge",
                ) as write_bridge_mock,
                mock.patch(
                    "webcam_micro.runtime_bootstrap._exec_runtime_python",
                ) as exec_runtime_mock,
            ):
                bootstrap_runtime(["--smoke-test"])

            write_bridge_mock.assert_not_called()
            exec_runtime_mock.assert_not_called()
            self.assertEqual(
                "/opt/site-packages\n",
                bridge_file.read_text(encoding="utf-8"),
            )
