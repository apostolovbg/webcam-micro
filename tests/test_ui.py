"""Stage 4 tests for the GUI shell description layer."""

from __future__ import annotations

import unittest

from webcam_micro.ui import (
    MissingGuiDependencyError,
    PreviewApplication,
    RuntimeStatus,
    ShellSpec,
    build_runtime_status,
    build_shell_spec,
    format_numeric_control_value,
    launch_main_window,
    parse_numeric_control_text,
)


class ShellSpecTest(unittest.TestCase):
    """Verify the headless-friendly main-window shell description."""

    def test_shell_spec_mentions_stage_four_baseline(self) -> None:
        """Assert the shell spec captures the Stage 4 shell contract."""

        spec = build_shell_spec()
        combined_body = " ".join(spec.hero_body)

        self.assertIsInstance(spec, ShellSpec)
        self.assertEqual("webcam-micro workspace", spec.title)
        self.assertEqual("litera", spec.theme_name)
        self.assertIn("ttkbootstrap", combined_body)
        self.assertIn("FFmpeg", combined_body)
        self.assertIn("separate window", combined_body)
        self.assertEqual(
            ("File", "Edit", "View", "Camera", "Capture", "Tools", "Help"),
            spec.menu_sections,
        )
        self.assertEqual(
            (
                "Controls",
                "Refresh",
                "Open",
                "Still",
                "Record",
                "Fullscreen",
                "Preferences",
            ),
            spec.toolbar_actions,
        )
        self.assertEqual("Camera Controls", spec.controls_window_title)
        self.assertEqual("© Apostol Apostolov", spec.copyright_notice)
        self.assertIn("{backend}", spec.status_template)
        self.assertIn("{controls}", spec.status_template)

    def test_ui_contract_symbols_stay_explicit(self) -> None:
        """Assert the GUI-shell public contract stays named and importable."""

        self.assertTrue(callable(build_shell_spec))
        self.assertTrue(callable(build_runtime_status))
        self.assertTrue(callable(format_numeric_control_value))
        self.assertTrue(callable(launch_main_window))
        self.assertTrue(callable(parse_numeric_control_text))
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

    def test_runtime_status_preserves_main_shell_fields(self) -> None:
        """Assert the visible runtime status keeps the key shell fields."""

        status = build_runtime_status(
            backend_name="ffmpeg",
            camera_name="Camera 0 (640x480)",
            preview_state="live",
            source_mode="640x480@30 preview",
            framing_mode="fit",
            controls_window_state="open",
            recording_state="not ready",
            notice="Live preview active.",
        )

        self.assertIsInstance(status, RuntimeStatus)
        self.assertEqual("ffmpeg", status.backend_name)
        self.assertEqual("Camera 0 (640x480)", status.camera_name)
        self.assertEqual("live", status.preview_state)
        self.assertEqual("640x480@30 preview", status.source_mode)
        self.assertEqual("fit", status.framing_mode)
        self.assertEqual("open", status.controls_window_state)
        self.assertEqual("not ready", status.recording_state)
        self.assertEqual("Live preview active.", status.notice)

    def test_numeric_control_helpers_format_and_reject_invalid_text(
        self,
    ) -> None:
        """Assert numeric helpers preserve valid values and blank bad ones."""

        self.assertEqual("1.5", format_numeric_control_value(1.5, 0.1))
        self.assertEqual(
            12.5,
            parse_numeric_control_text(
                "12.5",
                minimum=0.0,
                maximum=20.0,
            ),
        )
        self.assertIsNone(
            parse_numeric_control_text(
                "not-a-number",
                minimum=0.0,
                maximum=20.0,
            )
        )
        self.assertIsNone(
            parse_numeric_control_text(
                "32",
                minimum=0.0,
                maximum=20.0,
            )
        )
