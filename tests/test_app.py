"""Stage 4 tests for the application entrypoint and package contract."""

from __future__ import annotations

import tomllib
import unittest
from pathlib import Path

from webcam_micro.app import LaunchPlan, build_launch_plan, main


class ApplicationEntryPointTest(unittest.TestCase):
    """Verify the Stage 4 launcher wiring and package metadata."""

    def test_smoke_mode_returns_success(self) -> None:
        """Assert the headless smoke path exits successfully."""

        self.assertEqual(0, main(["--smoke-test"]))

    def test_launch_plan_describes_stage_four_baseline(self) -> None:
        """Assert the launch plan documents the controls-aware baseline."""

        plan = build_launch_plan()

        self.assertEqual("webcam-micro", plan.app_name)
        self.assertEqual("webcam_micro", plan.package_name)
        self.assertEqual("webcam-micro", plan.entrypoint_name)
        self.assertEqual("ttkbootstrap", plan.gui_baseline)
        self.assertIn("newest-frame", plan.backend_strategy)
        self.assertIn("AVFoundation", plan.backend_strategy)
        self.assertIn("rubicon", plan.backend_strategy)
        self.assertIn("FFmpeg", plan.first_device_backend_target)
        self.assertIn("toolbar", plan.shell_contract)
        self.assertIn("separate controls window", plan.shell_contract)
        self.assertIn("typed camera controls", plan.shell_contract)

    def test_launch_plan_symbol_stays_explicit(self) -> None:
        """Assert the launch-plan dataclass stays public."""

        plan = build_launch_plan()

        self.assertIsInstance(plan, LaunchPlan)
        self.assertEqual("LaunchPlan", LaunchPlan.__name__)

    def test_pyproject_declares_console_script(self) -> None:
        """Assert package metadata exposes the governed launcher."""

        repo_root = Path(__file__).resolve().parents[1]
        payload = tomllib.loads(
            (repo_root / "pyproject.toml").read_text(encoding="utf-8")
        )

        self.assertEqual("0.0.1", payload["project"]["version"])
        self.assertEqual(">=3.11", payload["project"]["requires-python"])
        self.assertIn(
            "imageio-ffmpeg>=0.6,<0.7",
            payload["project"]["dependencies"],
        )
        self.assertIn("pillow>=10,<13", payload["project"]["dependencies"])
        self.assertIn(
            "ttkbootstrap>=1.20,<2",
            payload["project"]["dependencies"],
        )
        self.assertIn(
            "rubicon-objc>=0.5,<0.6; sys_platform == 'darwin'",
            payload["project"]["dependencies"],
        )
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
