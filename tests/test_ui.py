"""Stage 2 tests for the GUI shell description layer."""

from __future__ import annotations

import unittest

from webcam_micro.ui import (
    MissingGuiDependencyError,
    PreviewApplication,
    RuntimeStatus,
    ShellSpec,
    build_runtime_status,
    build_shell_spec,
    launch_main_window,
)


class ShellSpecTest(unittest.TestCase):
    """Verify the headless-friendly preview-shell description."""

    def test_shell_spec_mentions_stage_two_baseline(self) -> None:
        """Assert the shell spec captures the GUI and preview choices."""

        spec = build_shell_spec()
        combined_body = " ".join(spec.hero_body)

        self.assertIsInstance(spec, ShellSpec)
        self.assertEqual("webcam-micro preview shell", spec.title)
        self.assertEqual("litera", spec.theme_name)
        self.assertIn("ttkbootstrap", combined_body)
        self.assertIn("FFmpeg", combined_body)
        self.assertIn("{backend}", spec.status_template)

    def test_ui_contract_symbols_stay_explicit(self) -> None:
        """Assert the GUI-shell public contract stays named and importable."""

        self.assertTrue(callable(build_shell_spec))
        self.assertTrue(callable(build_runtime_status))
        self.assertTrue(callable(launch_main_window))
        self.assertTrue(callable(PreviewApplication.refresh_cameras))
        self.assertTrue(callable(PreviewApplication.open_selected_camera))
        self.assertTrue(callable(PreviewApplication.close_session))
        self.assertTrue(callable(PreviewApplication.run))
        self.assertTrue(issubclass(MissingGuiDependencyError, RuntimeError))
        self.assertEqual(
            "MissingGuiDependencyError", MissingGuiDependencyError.__name__
        )
        self.assertEqual("PreviewApplication", PreviewApplication.__name__)
        self.assertEqual("RuntimeStatus", RuntimeStatus.__name__)
        self.assertEqual("ShellSpec", ShellSpec.__name__)

    def test_runtime_status_preserves_backend_camera_and_preview(self) -> None:
        """Assert the visible runtime status keeps the key preview fields."""

        status = build_runtime_status(
            backend_name="opencv",
            camera_name="Camera 0 (640x480)",
            preview_state="live",
        )

        self.assertIsInstance(status, RuntimeStatus)
        self.assertEqual("opencv", status.backend_name)
        self.assertEqual("Camera 0 (640x480)", status.camera_name)
        self.assertEqual("live", status.preview_state)
