"""Headless tests for the application entrypoint and package contract."""

from __future__ import annotations

import tomllib
import unittest
from pathlib import Path

from webcam_micro.app import LaunchPlan, build_launch_plan, main


class ApplicationEntryPointTest(unittest.TestCase):
    """Verify the launcher wiring and package metadata."""

    def test_smoke_mode_returns_success(self) -> None:
        """Assert the headless smoke path exits successfully."""

        self.assertEqual(0, main(["--smoke-test"]))

    def test_launch_plan_describes_current_qt_baseline(self) -> None:
        """Assert the launch plan documents the Qt shell baseline."""

        plan = build_launch_plan()

        self.assertEqual("webcam-micro", plan.app_name)
        self.assertEqual("webcam_micro", plan.package_name)
        self.assertEqual("webcam-micro", plan.entrypoint_name)
        self.assertEqual("PySide6 Qt Widgets", plan.gui_baseline)
        self.assertIn("Qt Widgets owns", plan.backend_strategy)
        self.assertIn("Qt Multimedia now owns", plan.backend_strategy)
        self.assertIn("AVFoundation", plan.backend_strategy)
        self.assertIn("rubicon", plan.backend_strategy)
        self.assertIn("Qt Multimedia", plan.first_device_backend_target)
        self.assertIn("native desktop menu bar", plan.shell_contract)
        self.assertIn("toolbar", plan.shell_contract)
        self.assertIn("controls dock", plan.shell_contract)
        self.assertIn("dockable, detachable", plan.shell_contract)
        self.assertIn("hide, dock, float, and restore", plan.shell_contract)
        self.assertIn("fit/fill/crop", plan.shell_contract)
        self.assertIn("one-column default layout", plan.shell_contract)
        self.assertIn("two-column variant", plan.shell_contract)
        self.assertIn(
            "output folders that live in Preferences", plan.shell_contract
        )
        self.assertIn("compact structured status bar", plan.shell_contract)
        self.assertIn("still-save", plan.shell_contract)
        self.assertIn("recording", plan.shell_contract)
        self.assertIn("preferences", plan.shell_contract)
        self.assertIn("diagnostics", plan.shell_contract)
        self.assertIn("failure log", plan.shell_contract)
        self.assertIn("exit checks", plan.shell_contract)
        self.assertIn("fullscreen", plan.shell_contract)
        self.assertIn("per-user runtime interpreter", plan.shell_contract)
        self.assertIn("camera permission prompt", plan.shell_contract)

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

        self.assertEqual("0.1.0b1", payload["project"]["version"])
        self.assertEqual(
            {
                "file": "webcam_micro/README.md",
                "content-type": "text/markdown",
            },
            payload["project"]["readme"],
        )
        self.assertEqual(">=3.11", payload["project"]["requires-python"])
        self.assertIn(
            "PySide6>=6.11,<6.12", payload["project"]["dependencies"]
        )
        self.assertIn(
            "rubicon-objc>=0.5,<0.6; sys_platform == 'darwin'",
            payload["project"]["dependencies"],
        )
        self.assertEqual(
            "webcam_micro.launcher:main",
            payload["project"]["scripts"]["webcam-micro"],
        )

    def test_app_owned_artifacts_live_under_webcam_micro(self) -> None:
        """Assert import assets and package docs use distinct owned paths."""

        repo_root = Path(__file__).resolve().parents[1]

        self.assertTrue((repo_root / "webcam_micro" / "VERSION").exists())
        self.assertTrue(
            (repo_root / "webcam_micro" / "runtime-requirements.lock").exists()
        )
        self.assertTrue(
            (repo_root / "webcam_micro" / "licenses" / "README.md").exists()
        )
        self.assertTrue((repo_root / "webcam_micro" / "README.md").exists())
        self.assertFalse((repo_root / "webcam-micro").exists())

    def test_package_readme_stays_user_facing_only(self) -> None:
        """Assert the package README omits repo-only content."""

        repo_root = Path(__file__).resolve().parents[1]
        root_readme = (repo_root / "README.md").read_text(encoding="utf-8")
        package_readme = (repo_root / "webcam_micro" / "README.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("<!-- REPO-ONLY:BEGIN -->", root_readme)
        self.assertIn("per-user runtime interpreter", root_readme)
        self.assertIn("## What Works Today", package_readme)
        self.assertIn("Qt Widgets", package_readme)
        self.assertIn("webcam_micro.launcher", package_readme)
        self.assertIn("per-user runtime interpreter", package_readme)
        self.assertNotIn("Flet", package_readme)
        self.assertIn("## Alpha Status", package_readme)
        self.assertIn(
            "© 2026 Black Epsilon Ltd. and Apostol Apostolov",
            package_readme,
        )
        self.assertNotIn("## Development Quick Start", package_readme)
        self.assertNotIn("## Workflow", package_readme)
        self.assertNotIn("<!-- REPO-ONLY:BEGIN -->", package_readme)
