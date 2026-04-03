"""Stage 1 tests for the application entrypoint and package contract."""

from __future__ import annotations

import unittest
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib

from webcam_micro.app import build_launch_plan, main


class ApplicationEntryPointTest(unittest.TestCase):
    """Verify the Stage 1 launcher wiring and package metadata."""

    def test_smoke_mode_returns_success(self) -> None:
        """Assert the headless smoke path exits successfully."""

        self.assertEqual(0, main(["--smoke-test"]))

    def test_launch_plan_describes_stage_one_baseline(self) -> None:
        """Assert the launch plan documents the chosen foundation."""

        plan = build_launch_plan()

        self.assertEqual("webcam-micro", plan.app_name)
        self.assertEqual("webcam_micro", plan.package_name)
        self.assertEqual("webcam-micro", plan.entrypoint_name)
        self.assertEqual("ttkbootstrap", plan.gui_baseline)
        self.assertIn("OpenCV", plan.first_device_backend_target)

    def test_pyproject_declares_console_script(self) -> None:
        """Assert package metadata exposes the governed launcher."""

        repo_root = Path(__file__).resolve().parents[1]
        payload = tomllib.loads(
            (repo_root / "pyproject.toml").read_text(encoding="utf-8")
        )

        self.assertEqual("0.0.1", payload["project"]["version"])
        self.assertEqual(
            "webcam_micro.app:main",
            payload["project"]["scripts"]["webcam-micro"],
        )

    def test_app_owned_artifacts_live_under_webcam_micro(self) -> None:
        """Assert Stage 1 uses one app-owned directory."""

        repo_root = Path(__file__).resolve().parents[1]

        self.assertTrue((repo_root / "webcam_micro" / "VERSION").exists())
        self.assertTrue(
            (repo_root / "webcam_micro" / "runtime-requirements.lock").exists()
        )
        self.assertTrue(
            (repo_root / "webcam_micro" / "licenses" / "README.md").exists()
        )
        self.assertFalse((repo_root / "webcam-micro").exists())
