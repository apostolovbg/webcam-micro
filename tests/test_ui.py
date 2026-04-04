"""Headless tests for the GUI shell description layer."""

from __future__ import annotations

import inspect
import unittest

from webcam_micro.ui import (
    MissingGuiDependencyError,
    PreviewApplication,
    RenderedPreview,
    RuntimeStatus,
    ShellSpec,
    build_controls_surface_lines,
    build_diagnostics_lines,
    build_fullscreen_surface_actions,
    build_runtime_status,
    build_shell_spec,
    format_numeric_control_value,
    format_recording_duration,
    launch_main_window,
    parse_numeric_control_text,
    render_preview_image,
)


class ShellSpecTest(unittest.TestCase):
    """Verify the headless-friendly main-window shell description."""

    def test_shell_spec_mentions_current_qt_baseline(self) -> None:
        """Assert the shell spec captures the current Qt shell contract."""

        spec = build_shell_spec()
        combined_body = " ".join(spec.hero_body)

        self.assertIsInstance(spec, ShellSpec)
        self.assertEqual("webcam-micro workspace", spec.title)
        self.assertEqual("light", spec.theme_mode)
        self.assertIn("pyside6 qt widgets", combined_body.lower())
        self.assertIn("Qt Multimedia", combined_body)
        self.assertIn("native desktop menu bar", combined_body)
        self.assertIn("toggleable dock", combined_body)
        self.assertEqual(
            (
                "Menu Bar",
                "Toolbar",
                "Preview Workspace",
                "Controls Dock",
                "Status Bar",
            ),
            spec.command_sections,
        )
        self.assertEqual(
            (
                "Controls",
                "Refresh",
                "Open",
                "Fit",
                "Fill",
                "Crop",
                "Still",
                "Record",
                "Fullscreen",
                "Preferences",
            ),
            spec.toolbar_actions,
        )
        self.assertEqual("Camera Controls", spec.controls_surface_title)
        self.assertEqual("© Apostol Apostolov", spec.copyright_notice)
        self.assertIn("{backend}", spec.status_template)
        self.assertIn("{controls}", spec.status_template)
        self.assertIn("{capture_framing}", spec.status_template)

    def test_ui_contract_symbols_stay_explicit(self) -> None:
        """Assert the GUI-shell public contract stays named and importable."""

        self.assertTrue(callable(build_controls_surface_lines))
        self.assertTrue(callable(build_diagnostics_lines))
        self.assertTrue(callable(build_fullscreen_surface_actions))
        self.assertTrue(callable(build_shell_spec))
        self.assertTrue(callable(build_runtime_status))
        self.assertTrue(callable(format_recording_duration))
        self.assertTrue(callable(format_numeric_control_value))
        self.assertTrue(callable(launch_main_window))
        self.assertTrue(callable(parse_numeric_control_text))
        self.assertTrue(callable(render_preview_image))
        self.assertTrue(
            callable(PreviewApplication._set_fullscreen_surface_expanded)
        )
        self.assertTrue(callable(PreviewApplication._handle_escape_shortcut))
        self.assertTrue(callable(PreviewApplication.refresh_cameras))
        self.assertTrue(callable(PreviewApplication.open_selected_camera))
        self.assertTrue(callable(PreviewApplication.close_session))
        self.assertTrue(callable(PreviewApplication.run))
        self.assertTrue(issubclass(MissingGuiDependencyError, RuntimeError))
        self.assertEqual(
            "MissingGuiDependencyError", MissingGuiDependencyError.__name__
        )
        self.assertEqual("PreviewApplication", PreviewApplication.__name__)
        self.assertEqual("RenderedPreview", RenderedPreview.__name__)
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
            capture_framing_mode="crop",
            controls_surface_state="open",
            recording_state="not ready",
            notice="Live preview active.",
        )

        self.assertIsInstance(status, RuntimeStatus)
        self.assertEqual("ffmpeg", status.backend_name)
        self.assertEqual("Camera 0 (640x480)", status.camera_name)
        self.assertEqual("live", status.preview_state)
        self.assertEqual("640x480@30 preview", status.source_mode)
        self.assertEqual("fit", status.framing_mode)
        self.assertEqual("crop", status.capture_framing_mode)
        self.assertEqual("open", status.controls_surface_state)
        self.assertEqual("not ready", status.recording_state)
        self.assertEqual("Live preview active.", status.notice)

    def test_controls_surface_summary_mentions_live_state(self) -> None:
        """Assert the controls surface summary reflects current shell state."""

        self.assertEqual(
            (
                "Backend: ffmpeg",
                "Camera: Camera 0",
                "Preview: live",
                "Preview framing: fill",
                "Capture framing: crop",
                "Controls surfaced: 7",
            ),
            build_controls_surface_lines(
                backend_name="ffmpeg",
                camera_name="Camera 0",
                preview_state="live",
                preview_framing_mode="fill",
                capture_framing_mode="crop",
                control_count=7,
            ),
        )

    def test_preview_rendering_modes_keep_expected_geometry(self) -> None:
        """Assert fit, fill, and crop render distinct preview geometries."""

        fit = render_preview_image(
            source_width=1280,
            source_height=720,
            target_width=960,
            target_height=640,
            framing_mode="fit",
        )
        fill = render_preview_image(
            source_width=1280,
            source_height=720,
            target_width=960,
            target_height=640,
            framing_mode="fill",
        )
        crop = render_preview_image(
            source_width=1280,
            source_height=720,
            target_width=960,
            target_height=640,
            framing_mode="crop",
        )

        self.assertEqual((960, 540), fit.size)
        self.assertEqual((960, 640), fill.size)
        self.assertEqual((640, 640), crop.size)
        self.assertEqual(
            (0, 0, 1280, 720),
            (fit.source_x, fit.source_y, fit.source_width, fit.source_height),
        )
        self.assertEqual(
            (100, 0, 1080, 720),
            (
                fill.source_x,
                fill.source_y,
                fill.source_width,
                fill.source_height,
            ),
        )
        self.assertEqual(
            (280, 0, 720, 720),
            (
                crop.source_x,
                crop.source_y,
                crop.source_width,
                crop.source_height,
            ),
        )

    def test_fullscreen_surface_helpers_cover_both_states(self) -> None:
        """Assert the fullscreen command surface covers both states safely."""

        self.assertEqual(
            (
                "Controls",
                "Still",
                "Record",
                "Preferences",
                "Fit",
                "Fill",
                "Crop",
                "Windowed",
                "Collapse",
            ),
            build_fullscreen_surface_actions(expanded=True),
        )
        self.assertEqual(
            ("Expand", "Windowed"),
            build_fullscreen_surface_actions(expanded=False),
        )

    def test_diagnostics_helpers_report_shell_state(self) -> None:
        """Assert diagnostics lines cover the governed Qt shell state."""

        self.assertEqual(
            (
                "Backend: qt_multimedia",
                "Camera: Camera 0",
                "Preview: live",
                "Source mode: 1280x720 live preview",
                "Preview framing: fill",
                "Capture framing: crop",
                "Controls surfaced: 7",
                "Controls dock: open",
                "Fullscreen: windowed",
                "Recording: recording 00:05",
                "Image folder: /tmp/images",
                "Video folder: /tmp/videos",
                "Notice: Live preview active.",
            ),
            build_diagnostics_lines(
                backend_name="qt_multimedia",
                camera_name="Camera 0",
                preview_state="live",
                source_mode="1280x720 live preview",
                preview_framing_mode="fill",
                capture_framing_mode="crop",
                control_count=7,
                recording_state="recording 00:05",
                image_directory="/tmp/images",
                video_directory="/tmp/videos",
                controls_surface_state="open",
                fullscreen_state="windowed",
                notice="Live preview active.",
            ),
        )
        self.assertEqual("00:05", format_recording_duration(5_900))
        self.assertEqual("01:02:03", format_recording_duration(3_723_000))

    def test_nested_shell_callbacks_remain_covered_by_name(self) -> None:
        """Assert nested helper names stay visible to contract coverage."""

        numeric_builder_source = inspect.getsource(
            PreviewApplication._build_numeric_control
        )
        window_source = inspect.getsource(PreviewApplication._build_window)
        launch_source = inspect.getsource(launch_main_window)
        actions_source = inspect.getsource(PreviewApplication._build_actions)
        fullscreen_source = inspect.getsource(
            PreviewApplication._build_fullscreen_surface
        )
        preferences_source = inspect.getsource(
            PreviewApplication._open_preferences
        )

        self.assertIn("def sync_field", numeric_builder_source)
        self.assertIn("def sync_slider", numeric_builder_source)
        self.assertIn("def handle_slider_change", numeric_builder_source)
        self.assertIn("def handle_slider_commit", numeric_builder_source)
        self.assertIn("def handle_field_commit", numeric_builder_source)
        self.assertIn("def handle_step", numeric_builder_source)
        self.assertIn("def choose_directory", preferences_source)
        self.assertIn("class ResizeAwareLabel", window_source)
        self.assertIn("class ResizeAwareMainWindow", window_source)
        self.assertIn("def resizeEvent", window_source)
        self.assertIn("QApplication.instance", launch_source)
        self.assertIn("PreferencesRole", actions_source)
        self.assertIn("AboutRole", actions_source)
        self.assertIn("QuitRole", actions_source)
        self.assertIn("setShortcut", actions_source)
        self.assertIn("fullscreen-surface", fullscreen_source)

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
