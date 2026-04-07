"""Headless tests for the GUI shell description layer."""

from __future__ import annotations

import inspect
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from webcam_micro.camera import (
    CameraControl,
    CameraControlChoice,
    CameraDescriptor,
    PreviewFrame,
    RecordingCropPlan,
)
from webcam_micro.error_reporting import WebcamMicroError
from webcam_micro.ui import (
    MissingGuiDependencyError,
    PreviewApplication,
    RenderedPreview,
    RuntimeStatus,
    ShellSpec,
    _camera_control_setting_key,
    _control_default_setting_key,
    _controls_surface_column_count,
    _directory_setting_path,
    _group_controls_for_surface,
    _named_presets_from_value,
    _named_presets_to_value,
    _recording_crop_plan_from_frame,
    _settings_bool,
    _settings_text,
    _shortcut_conflict_label,
    _shortcut_setting_key,
    build_controls_surface_lines,
    build_diagnostics_lines,
    build_fullscreen_surface_actions,
    build_prototype_exit_check_lines,
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
        self.assertIn("toggleable, detachable dock", combined_body)
        self.assertIn("detachable dock", combined_body)
        self.assertIn("dock, float, hide, and restore", combined_body)
        self.assertIn("visible restore action", combined_body)
        self.assertIn("slider-plus-spinbox", combined_body)
        self.assertIn("one column", combined_body)
        self.assertIn("two columns", combined_body)
        self.assertIn("compact structured status bar", combined_body)
        self.assertIn(
            "camera controls and user controls", combined_body.lower()
        )
        for phrase in (
            "Camera Controls",
            "User Controls",
            "Resolution",
            "Exposure",
            "Focus",
            "Light",
            "Zoom",
            "Backlight compensation",
            "Brightness",
            "Contrast",
            "Hue",
            "Saturation",
            "Sharpness",
            "Gamma",
            "Gain",
            "Power Line Frequency",
            "White balance",
            "Reset to Defaults",
        ):
            self.assertIn(phrase, combined_body)
        self.assertIn("still capture saves quietly", combined_body)
        self.assertIn("tighter preview cadence", combined_body.lower())
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
                "Restore Dock",
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
        self.assertEqual(
            "© 2026 Black Epsilon Ltd. and Apostol Apostolov",
            spec.copyright_notice,
        )
        self.assertIn("{backend}", spec.status_template)
        self.assertIn("{controls}", spec.status_template)
        self.assertIn("{capture_framing}", spec.status_template)

    def test_ui_contract_symbols_stay_explicit(self) -> None:
        """Assert the GUI-shell public contract stays named and importable."""

        preferences_source = inspect.getsource(
            PreviewApplication._open_preferences
        )
        diagnostics_source = inspect.getsource(
            PreviewApplication._open_diagnostics
        )
        fullscreen_toggle_source = inspect.getsource(
            PreviewApplication._set_fullscreen
        )
        actions_source = inspect.getsource(PreviewApplication._build_actions)
        dock_source = inspect.getsource(
            PreviewApplication._build_controls_dock
        )
        dock_button_source = inspect.getsource(
            PreviewApplication._make_controls_dock_action_button
        )
        controls_source = inspect.getsource(
            PreviewApplication._rebuild_controls_widgets
        )
        run_source = inspect.getsource(PreviewApplication.run)
        open_source = inspect.getsource(
            PreviewApplication.open_selected_camera
        )
        self.assertTrue(callable(build_controls_surface_lines))
        self.assertTrue(callable(build_diagnostics_lines))
        self.assertTrue(callable(build_fullscreen_surface_actions))
        self.assertTrue(callable(build_prototype_exit_check_lines))
        self.assertTrue(callable(build_shell_spec))
        self.assertTrue(callable(build_runtime_status))
        self.assertTrue(callable(format_recording_duration))
        self.assertTrue(callable(format_numeric_control_value))
        self.assertTrue(callable(launch_main_window))
        self.assertTrue(callable(parse_numeric_control_text))
        self.assertTrue(callable(render_preview_image))
        self.assertTrue(callable(_group_controls_for_surface))
        self.assertTrue(callable(_named_presets_from_value))
        self.assertTrue(callable(_named_presets_to_value))
        self.assertTrue(
            callable(PreviewApplication._set_fullscreen_surface_expanded)
        )
        self.assertTrue(callable(PreviewApplication._handle_escape_shortcut))
        self.assertTrue(callable(PreviewApplication._restore_controls_dock))
        self.assertTrue(
            callable(PreviewApplication._sync_controls_surface_layout)
        )
        self.assertTrue(callable(PreviewApplication._persist_workspace_state))
        self.assertTrue(
            callable(PreviewApplication._apply_persisted_control_state)
        )
        self.assertTrue(
            callable(PreviewApplication._apply_persisted_shortcuts)
        )
        self.assertTrue(callable(PreviewApplication.refresh_cameras))
        self.assertTrue(callable(PreviewApplication.open_selected_camera))
        self.assertTrue(callable(PreviewApplication.close_session))
        self.assertTrue(callable(PreviewApplication.run))
        self.assertEqual(16, PreviewApplication.refresh_interval_milliseconds)
        self.assertIn("accept_dialog", preferences_source)
        self.assertIn("apply_named_preset", preferences_source)
        self.assertIn("save_named_preset", preferences_source)
        self.assertIn("add_text_tab", diagnostics_source)
        self.assertNotIn("_workspace_notes", fullscreen_toggle_source)
        self.assertIn("ResizeAwareControlsWidget", dock_source)
        self.assertIn("_controls_dock_actions_row", dock_source)
        self.assertIn("QToolButton", dock_button_source)
        self.assertIn("_make_controls_dock_action_button", actions_source)
        self.assertIn("_build_camera_controls_section_widget", controls_source)
        self.assertIn("_build_user_controls_section_widget", controls_source)
        self.assertIn("_controls_surface_column_count", controls_source)
        self.assertIn("_build_controls_section_widget", controls_source)
        self.assertIn("_build_controls_column_widget", controls_source)
        self.assertIn("_build_controls_empty_state_widget", controls_source)
        self.assertIn("PreciseTimer", run_source)
        self.assertIn("self._poll_preview_frame()", open_source)
        self.assertIn("_prime_source_format_for_descriptor", open_source)
        self.assertTrue(
            issubclass(MissingGuiDependencyError, WebcamMicroError)
        )
        self.assertEqual(
            "MissingGuiDependencyError", MissingGuiDependencyError.__name__
        )
        self.assertEqual("PreviewApplication", PreviewApplication.__name__)
        self.assertEqual("RenderedPreview", RenderedPreview.__name__)
        self.assertEqual("RuntimeStatus", RuntimeStatus.__name__)
        self.assertEqual("ShellSpec", ShellSpec.__name__)

    def test_menu_bar_keeps_camera_actions_out_of_file(self) -> None:
        """Assert the File menu stays exit-only while Camera owns sessions."""

        menu_bar_source = inspect.getsource(PreviewApplication._build_menu_bar)

        self.assertIn('file_menu = menu_bar.addMenu("File")', menu_bar_source)
        self.assertIn(
            "file_menu.addAction(self._exit_action)",
            menu_bar_source,
        )
        self.assertNotIn(
            "file_menu.addAction(self._open_action)",
            menu_bar_source,
        )
        self.assertNotIn(
            "file_menu.addAction(self._close_camera_action)",
            menu_bar_source,
        )
        self.assertIn(
            "camera_menu.addAction(self._refresh_action)",
            menu_bar_source,
        )
        self.assertIn(
            "camera_menu.addAction(self._open_action)",
            menu_bar_source,
        )
        self.assertIn(
            "camera_menu.addAction(self._close_camera_action)",
            menu_bar_source,
        )

    def test_capture_still_saves_quietly_to_the_image_folder(self) -> None:
        """Assert still capture saves directly to the configured folder."""

        class FakeImage:
            """Record the still-save path and format."""

            def __init__(self) -> None:
                """Initialize the captured save calls list."""

                self.calls: list[tuple[str, str]] = []

            def save(self, path: str, format_name: str) -> bool:
                """Record one still-save request."""

                self.calls.append((path, format_name))
                return True

        class FakeShell:
            """Provide the minimum still-capture surface."""

            def __init__(self, image_directory: Path) -> None:
                """Initialize the shell state used by still capture."""

                self._latest_frame = object()
                self._image_directory = image_directory
                self._capture_framing_mode = "fit"
                self._preview_state = "live"
                self._qt_gui = object()
                self.status_calls: list[tuple[str, str]] = []
                self.diagnostic_calls: list[str] = []
                self.persisted = False

            def _preview_target_size(self) -> tuple[int, int]:
                """Return the active preview size used for still capture."""

                return (960, 640)

            def _set_status(self, preview_state: str, notice: str) -> None:
                """Record the visible status update."""

                self.status_calls.append((preview_state, notice))

            def _record_diagnostic_event(self, message: str) -> None:
                """Record the diagnostic event emitted by still capture."""

                self.diagnostic_calls.append(message)

            def _persist_output_directories(self) -> None:
                """Record that the output folder was persisted."""

                self.persisted = True

        with TemporaryDirectory() as temp_dir:
            image_directory = Path(temp_dir)
            existing_path = image_directory / "microscope-20260405-010203.png"
            existing_path.write_text("existing still")
            fake_image = FakeImage()
            shell = FakeShell(image_directory)

            with (
                mock.patch(
                    "webcam_micro.ui._timestamp_slug",
                    return_value="20260405-010203",
                ),
                mock.patch(
                    "webcam_micro.ui._capture_image_from_frame",
                    return_value=fake_image,
                ),
                mock.patch.object(
                    PreviewApplication,
                    "_select_output_path",
                    side_effect=AssertionError("save dialog should not run"),
                ),
            ):
                PreviewApplication._capture_still_action(shell)

        self.assertEqual(
            [
                (
                    str(image_directory / "microscope-20260405-010203-1.png"),
                    "PNG",
                )
            ],
            fake_image.calls,
        )
        self.assertTrue(shell.persisted)
        self.assertEqual(
            [
                (
                    "live",
                    "Saved still to microscope-20260405-010203-1.png.",
                )
            ],
            shell.status_calls,
        )
        self.assertEqual([], shell.diagnostic_calls)

    def test_open_selected_camera_checks_permission_before_opening(
        self,
    ) -> None:
        """Assert the camera-open path requests permission first."""

        class FakeBackend:
            """Record whether the backend was asked to open a session."""

            backend_name = "qt_multimedia"

            def __init__(self) -> None:
                """Initialize the list of opened descriptors."""

                self.opened_descriptors: list[CameraDescriptor] = []

            def open_session(self, descriptor: CameraDescriptor) -> object:
                """Record the open request and return a placeholder session."""

                self.opened_descriptors.append(descriptor)
                return object()

        class FakeShell:
            """Provide the minimum surface needed by the open path."""

            def __init__(self) -> None:
                """Initialize the shell state used by the permission guard."""

                self._backend = fake_backend
                self._cameras = [descriptor]
                self._selected_camera_id = descriptor.stable_id
                self._qt_core = object()
                self._session = None
                self._preview_state = "live"
                self._current_preset_name = None
                self.calls: list[object] = []

            def _selected_descriptor(self) -> CameraDescriptor | None:
                """Return the selected descriptor used for the open path."""

                return descriptor

            def close_session(self) -> None:
                """Record that the shell tried to close an existing session."""

                self.calls.append("close_session")

            def _set_preview_message(self, message: str) -> None:
                """Record the preview message shown to the user."""

                self.calls.append(("preview", message))

            def _refresh_control_surface(self, notice: str) -> None:
                """Record the controls-surface notice."""

                self.calls.append(("controls", notice))

            def _set_status(self, state: str, notice: str) -> None:
                """Record the visible status update."""

                self.calls.append(("status", state, notice))

            def _record_diagnostic_event(self, message: str) -> None:
                """Record the diagnostic event emitted by the shell."""

                self.calls.append(("diagnostic", message))

            def _refresh_recording_state(self) -> None:
                """Record the recording-state refresh call."""

                self.calls.append("recording_state")

            def _apply_persisted_control_state(self) -> None:
                """Record the control-state restore call."""

                self.calls.append("apply_controls")

            def _persist_workspace_state(self) -> None:
                """Record the workspace-persistence call."""

                self.calls.append("persist")

        descriptor = CameraDescriptor(
            stable_id="camera-1",
            display_name="Camera 1",
            backend_name="qt_multimedia",
            device_selector="camera-1",
        )
        fake_backend = FakeBackend()
        shell = FakeShell()

        with mock.patch(
            "webcam_micro.ui.request_camera_permission",
            return_value=(False, "Camera permission denied."),
        ):
            PreviewApplication.open_selected_camera(shell)

        self.assertEqual([], fake_backend.opened_descriptors)
        self.assertNotIn("close_session", shell.calls)
        self.assertIn(
            ("preview", "Camera permission denied."),
            shell.calls,
        )
        self.assertIn(
            ("status", "permission denied", "Camera permission denied."),
            shell.calls,
        )

    def test_runtime_status_preserves_main_shell_fields(self) -> None:
        """Assert the visible runtime status keeps the key shell fields."""

        status = build_runtime_status(
            backend_name="ffmpeg",
            camera_name="Camera 0 (640x480)",
            preview_state="live",
            source_mode="640x480@30 preview",
            framing_mode="fit",
            capture_framing_mode="crop",
            controls_surface_state="docked",
            current_preset_name="none",
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
        self.assertEqual("docked", status.controls_surface_state)
        self.assertEqual("none", status.current_preset_name)
        self.assertEqual("not ready", status.recording_state)
        self.assertEqual("Live preview active.", status.notice)

    def test_controls_surface_state_tracks_dock_modes(self) -> None:
        """Assert the dock state helper reports hidden, docked, and
        floating."""

        class FakeDock:
            """Expose the minimal dock API used by the state helper."""

            def __init__(self) -> None:
                """Initialize the fake dock state."""

                self.visible = False
                self.floating = True

            def isVisible(self) -> bool:
                """Return whether the dock is currently visible."""

                return self.visible

            def isFloating(self) -> bool:
                """Return whether the dock is currently floating."""

                return self.floating

        class FakeShell:
            """Provide only the dock attribute used by the helper."""

            def __init__(self) -> None:
                """Initialize the fake shell wrapper."""

                self._controls_dock = FakeDock()

        shell = FakeShell()

        self.assertEqual(
            "hidden",
            PreviewApplication._controls_surface_state(shell),
        )
        shell._controls_dock.visible = True
        shell._controls_dock.floating = False
        self.assertEqual(
            "docked",
            PreviewApplication._controls_surface_state(shell),
        )
        shell._controls_dock.floating = True
        self.assertEqual(
            "floating",
            PreviewApplication._controls_surface_state(shell),
        )
        shell._controls_dock.visible = False
        self.assertEqual(
            "hidden",
            PreviewApplication._controls_surface_state(shell),
        )

    def test_controls_surface_column_count_prefers_two_columns(
        self,
    ) -> None:
        """Assert the dock layout stays single-column until it has room."""

        self.assertEqual(1, _controls_surface_column_count(799, 2))
        self.assertEqual(2, _controls_surface_column_count(800, 2))
        self.assertEqual(1, _controls_surface_column_count(1200, 1))

    def test_controls_surface_summary_mentions_live_state(self) -> None:
        """Assert the controls surface summary reflects current shell state."""

        self.assertEqual(
            (
                "Backend: ffmpeg",
                "Camera: Camera 0",
                "Preview: live",
                "Preview framing: fill",
                "Capture framing: crop",
                "Controls dock: docked",
                "Controls surfaced: 7",
            ),
            build_controls_surface_lines(
                backend_name="ffmpeg",
                camera_name="Camera 0",
                preview_state="live",
                preview_framing_mode="fill",
                capture_framing_mode="crop",
                controls_surface_state="docked",
                control_count=7,
            ),
        )

    def test_restore_controls_dock_reanchors_the_controls_pane(self) -> None:
        """Assert the restore action docks the pane back to the right edge."""

        class FakeDock:
            """Expose the dock API exercised by the restore action."""

            def __init__(self) -> None:
                """Initialize the fake dock state."""

                self.calls: list[tuple[str, object]] = []
                self.visible = False
                self.floating = True

            def setFloating(self, floating: bool) -> None:
                """Record the floating-state change."""

                self.calls.append(("setFloating", floating))
                self.floating = floating

            def setVisible(self, visible: bool) -> None:
                """Record the visible-state change."""

                self.calls.append(("setVisible", visible))
                self.visible = visible

            def isVisible(self) -> bool:
                """Return whether the dock is currently visible."""

                return self.visible

            def isFloating(self) -> bool:
                """Return whether the dock is currently floating."""

                return self.floating

        class FakeWindow:
            """Record the dock reattachment request."""

            def __init__(self) -> None:
                """Initialize the recorded dock calls."""

                self.calls: list[tuple[object, object]] = []

            def addDockWidget(self, area: object, dock: object) -> None:
                """Record the requested dock area."""

                self.calls.append((area, dock))

        class FakeToggleAction:
            """Record the action state mirrored from the dock."""

            def __init__(self) -> None:
                """Initialize the recorded toggle state."""

                self.checked: bool | None = None
                self.signals_blocked = False

            def blockSignals(self, blocked: bool) -> bool:
                """Record the signal-blocking state and return the old one."""

                previous = self.signals_blocked
                self.signals_blocked = blocked
                return previous

            def setChecked(self, checked: bool) -> None:
                """Record the dock toggle state."""

                self.checked = checked

        class FakeQtNamespace:
            """Expose only the dock area enum needed here."""

            class DockWidgetArea:
                """Provide the right-dock area constant."""

                RightDockWidgetArea = "right"

        class FakeQtCore:
            """Provide the Qt namespace used by the restore action."""

            def __init__(self) -> None:
                """Expose the dock area namespace under the Qt attribute."""

                setattr(self, "Qt", FakeQtNamespace)

        class FakeShell:
            """Provide only the shell methods used during restore."""

            def __init__(self) -> None:
                """Initialize the recorded restore state."""

                self._qt_core = FakeQtCore()
                self._window = FakeWindow()
                self._controls_dock = FakeDock()
                self._controls_dock_requested = False
                self._suspend_dock_sync = False
                self._toggle_controls_action = FakeToggleAction()
                self._status_label = object()
                self._preview_state = "live"
                self.sync_calls: list[str] = []
                self.status_calls: list[tuple[str, str | None]] = []
                self.render_calls = 0
                self.layout_calls = 0
                self.persist_calls = 0

            def _sync_controls_surface_layout(self) -> None:
                """Record the dock-layout refresh."""

                self.sync_calls.append("sync")

            def _controls_surface_state(self) -> str:
                """Return the current dock state through the real helper."""

                return PreviewApplication._controls_surface_state(self)

            def _sync_controls_dock_state(
                self,
                *,
                notice: str | None = None,
            ) -> None:
                """Run the real dock-state sync through the fake shell."""

                PreviewApplication._sync_controls_dock_state(
                    self,
                    notice=notice,
                )

            def _set_status(
                self,
                preview_state: str,
                notice: str | None = None,
            ) -> None:
                """Record the visible status update."""

                self.status_calls.append((preview_state, notice))

            def _render_latest_preview(self) -> None:
                """Record the preview refresh."""

                self.render_calls += 1

            def _layout_fullscreen_surface(self) -> None:
                """Record the fullscreen overlay refresh."""

                self.layout_calls += 1

            def _persist_workspace_state(self) -> None:
                """Record the workspace persistence request."""

                self.persist_calls += 1

        shell = FakeShell()

        PreviewApplication._restore_controls_dock(shell)

        self.assertEqual(
            [("right", shell._controls_dock)], shell._window.calls
        )
        self.assertEqual(
            [("setFloating", False), ("setVisible", True)],
            shell._controls_dock.calls,
        )
        self.assertTrue(shell._controls_dock_requested)
        self.assertTrue(shell._toggle_controls_action.checked)
        self.assertEqual(["sync"], shell.sync_calls)
        self.assertEqual(
            [("live", "Controls dock restored.")], shell.status_calls
        )
        self.assertEqual(1, shell.render_calls)
        self.assertEqual(1, shell.layout_calls)
        self.assertEqual(1, shell.persist_calls)

    def test_controls_surface_groups_related_controls_and_hides_backend_info(
        self,
    ) -> None:
        """Assert related controls stay grouped into stable families."""

        controls = (
            CameraControl(
                control_id="source_format",
                label="Resolution",
                kind="enum",
                value="1920x1080|Format_NV12|30-60fps",
            ),
            CameraControl(
                control_id="manual_exposure_time",
                label="Manual Exposure Time",
                kind="numeric",
                value=0.02,
            ),
            CameraControl(
                control_id="exposure_locked",
                label="Exposure Locked",
                kind="boolean",
                value=False,
            ),
            CameraControl(
                control_id="exposure_priority",
                label="Exposure Priority",
                kind="boolean",
                value=True,
            ),
            CameraControl(
                control_id="focus_distance",
                label="Focus Distance",
                kind="numeric",
                value=0.5,
            ),
            CameraControl(
                control_id="focus_auto",
                label="Focus Automatic",
                kind="boolean",
                value=False,
            ),
            CameraControl(
                control_id="activity_led",
                label="Activity LED",
                kind="boolean",
                value=True,
            ),
            CameraControl(
                control_id="light_enabled",
                label="Light Enabled",
                kind="boolean",
                value=True,
            ),
            CameraControl(
                control_id="light_level",
                label="Light Level",
                kind="numeric",
                value=50,
            ),
            CameraControl(
                control_id="backlight_compensation",
                label="Backlight Compensation",
                kind="numeric",
                value=0.0,
            ),
            CameraControl(
                control_id="brightness",
                label="Brightness",
                kind="numeric",
                value=10,
            ),
            CameraControl(
                control_id="contrast",
                label="Contrast",
                kind="numeric",
                value=50,
            ),
            CameraControl(
                control_id="contrast_auto",
                label="Contrast Automatic",
                kind="boolean",
                value=False,
            ),
            CameraControl(
                control_id="hue",
                label="Hue",
                kind="numeric",
                value=0,
            ),
            CameraControl(
                control_id="hue_auto",
                label="Hue Automatic",
                kind="boolean",
                value=False,
            ),
            CameraControl(
                control_id="saturation",
                label="Saturation",
                kind="numeric",
                value=128,
            ),
            CameraControl(
                control_id="sharpness",
                label="Sharpness",
                kind="numeric",
                value=50,
            ),
            CameraControl(
                control_id="gamma",
                label="Gamma",
                kind="numeric",
                value=72,
            ),
            CameraControl(
                control_id="gain",
                label="Gain",
                kind="numeric",
                value=20,
            ),
            CameraControl(
                control_id="power_line_frequency",
                label="Power Line Frequency",
                kind="enum",
                value="50",
                choices=(
                    CameraControlChoice(value="50", label="50 Hz"),
                    CameraControlChoice(value="60", label="60 Hz"),
                ),
            ),
            CameraControl(
                control_id="white_balance_temperature",
                label="White Balance Temperature",
                kind="numeric",
                value=2800,
            ),
            CameraControl(
                control_id="white_balance_automatic",
                label="White Balance Automatic",
                kind="boolean",
                value=True,
            ),
            CameraControl(
                control_id="manual_iso_sensitivity",
                label="Manual ISO Sensitivity",
                kind="numeric",
                value=100,
            ),
            CameraControl(
                control_id="exposure_mode",
                label="Exposure Mode",
                kind="enum",
                value="continuous_auto",
            ),
            CameraControl(
                control_id="smooth_auto_focus",
                label="Smooth Auto Focus",
                kind="boolean",
                value=False,
            ),
            CameraControl(
                control_id="focus_mode",
                label="Focus Mode",
                kind="enum",
                value="auto",
            ),
            CameraControl(
                control_id="flash_mode",
                label="Flash Mode",
                kind="enum",
                value="off",
            ),
            CameraControl(
                control_id="torch_mode",
                label="Torch Mode",
                kind="enum",
                value="off",
            ),
            CameraControl(
                control_id="video_hdr_automatic",
                label="Automatic Video HDR",
                kind="boolean",
                value=True,
            ),
            CameraControl(
                control_id="zoom_factor",
                label="Zoom Factor",
                kind="numeric",
                value=2.0,
            ),
            CameraControl(
                control_id="active_format",
                label="Active Format",
                kind="read_only",
                value="1920x1080",
            ),
            CameraControl(
                control_id="restore_auto_exposure",
                label="Restore Auto Exposure",
                kind="action",
                value=None,
            ),
            CameraControl(
                control_id="vendor_extension",
                label="Vendor Extension",
                kind="read_only",
                value="Enabled",
            ),
            CameraControl(
                control_id="control_backend",
                label="Control Backend",
                kind="read_only",
                value="AVFoundation",
            ),
        )

        grouped = tuple(
            (
                section_name,
                tuple(control.control_id for control in section_controls),
            )
            for section_name, section_controls in _group_controls_for_surface(
                controls
            )
        )

        self.assertEqual(
            (
                (
                    "Camera Controls",
                    (
                        "source_format",
                        "manual_exposure_time",
                        "exposure_locked",
                        "exposure_priority",
                        "focus_distance",
                        "focus_auto",
                        "activity_led",
                        "light_enabled",
                        "light_level",
                        "zoom_factor",
                    ),
                ),
                (
                    "User Controls",
                    (
                        "backlight_compensation",
                        "brightness",
                        "contrast",
                        "contrast_auto",
                        "hue",
                        "hue_auto",
                        "saturation",
                        "sharpness",
                        "gamma",
                        "gain",
                        "power_line_frequency",
                        "white_balance_temperature",
                        "white_balance_automatic",
                    ),
                ),
                (
                    "Other Controls",
                    (
                        "focus_mode",
                        "flash_mode",
                        "torch_mode",
                        "video_hdr_automatic",
                        "active_format",
                        "restore_auto_exposure",
                        "vendor_extension",
                    ),
                ),
            ),
            grouped,
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
                "Restore Dock",
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
                "Preset: daylight",
                "Controls dock: docked",
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
                current_preset_name="daylight",
                recording_state="recording 00:05",
                image_directory="/tmp/images",
                video_directory="/tmp/videos",
                controls_surface_state="docked",
                fullscreen_state="windowed",
                notice="Live preview active.",
            ),
        )
        self.assertEqual(
            (
                "Release readiness",
                "Package: webcam_micro",
                "Entry point: webcam-micro",
                "Python floor: 3.11+",
                "GUI baseline: PySide6 Qt Widgets",
                "Build artifacts: governance-gated CI distributions",
                "Publish path: trusted publishing from validated CI "
                "artifacts",
                "",
                "Prototype exit checks",
                "Backend: qt_multimedia",
                "Camera: Camera 0",
                "Preview state: live",
                "Source mode: 1280x720 live preview",
                "Preview framing: fill",
                "Capture framing: crop",
                "Controls dock: docked",
                "Fullscreen: windowed",
                "Preset: daylight",
                "Recording: recording 00:05",
                "Image folder: /tmp/images",
                "Video folder: /tmp/videos",
                "Recent diagnostic events: 3",
                "Recording containers are validated on this runtime.",
            ),
            build_prototype_exit_check_lines(
                app_name="webcam-micro",
                package_name="webcam_micro",
                gui_baseline="PySide6 Qt Widgets",
                backend_name="qt_multimedia",
                camera_name="Camera 0",
                preview_state="live",
                source_mode="1280x720 live preview",
                preview_framing_mode="fill",
                capture_framing_mode="crop",
                controls_surface_state="docked",
                fullscreen_state="windowed",
                current_preset_name="daylight",
                recording_state="recording 00:05",
                image_directory="/tmp/images",
                video_directory="/tmp/videos",
                diagnostic_event_count=3,
            ),
        )
        self.assertEqual("00:05", format_recording_duration(5_900))

    def test_recording_action_uses_runtime_supported_formats(self) -> None:
        """Assert recording opens with runtime-supported containers."""

        class FakeSession:
            """Record the selected recording output path."""

            def __init__(self) -> None:
                """Initialize the recording state used by the shell."""

                self.recording_state = "stopped"
                self.recording_output_path = None
                self.recording_error = None
                self.recording_duration_milliseconds = 0
                self.start_calls: list[tuple[Path, object]] = []

            def start_recording(
                self,
                output_path: Path,
                *,
                crop_plan: object,
            ) -> Path:
                """Record the requested path and return the normalized path."""

                self.start_calls.append((output_path, crop_plan))
                return output_path.with_suffix(".mov")

        class FakeShell:
            """Provide the minimum surface needed by the record action."""

            def __init__(self, video_directory: Path) -> None:
                """Initialize the shell state used by recording."""

                self._session = fake_session
                self._preview_state = "live"
                self._latest_frame = object()
                self._capture_framing_mode = "fit"
                self._video_directory = video_directory
                self._qt_multimedia = object()
                self.status_calls: list[tuple[str, str]] = []
                self.diagnostic_calls: list[str] = []
                self.persisted = False
                self.select_calls: list[tuple[str, Path, str]] = []

            def _preview_target_size(self) -> tuple[int, int]:
                """Return the active preview size used for recording."""

                return (960, 640)

            def _set_status(self, preview_state: str, notice: str) -> None:
                """Record the visible status update."""

                self.status_calls.append((preview_state, notice))

            def _record_diagnostic_event(self, message: str) -> None:
                """Record the diagnostic event emitted by recording."""

                self.diagnostic_calls.append(message)

            def _persist_output_directories(self) -> None:
                """Record that the output folder was persisted."""

                self.persisted = True

            def _select_output_path(
                self,
                *,
                title: str,
                initial_path: Path,
                filter_text: str,
            ) -> Path:
                """Record the save-dialog request and return one path."""

                self.select_calls.append((title, initial_path, filter_text))
                return initial_path.with_name(initial_path.stem)

        with TemporaryDirectory() as temp_dir:
            video_directory = Path(temp_dir)
            fake_session = FakeSession()
            shell = FakeShell(video_directory)

            with (
                mock.patch(
                    "webcam_micro.ui._timestamp_slug",
                    return_value="20260405-010203",
                ),
                mock.patch(
                    "webcam_micro.ui.build_recording_file_filter",
                    return_value="supported-formats",
                ) as build_filter,
                mock.patch(
                    "webcam_micro.ui._preferred_recording_output_suffix",
                    return_value=".mov",
                ) as preferred_suffix,
                mock.patch(
                    "webcam_micro.ui._recording_crop_plan_from_frame",
                    return_value=RecordingCropPlan(
                        source_x=0,
                        source_y=0,
                        source_width=960,
                        source_height=640,
                    ),
                ),
            ):
                PreviewApplication._toggle_recording_action(shell)

        self.assertEqual(
            [
                (
                    "Start Recording",
                    Path(temp_dir) / "microscope-20260405-010203.mov",
                    "supported-formats",
                )
            ],
            shell.select_calls,
        )
        self.assertEqual(1, build_filter.call_count)
        self.assertEqual(1, preferred_suffix.call_count)
        self.assertEqual(
            [
                (
                    Path(temp_dir) / "microscope-20260405-010203",
                    RecordingCropPlan(
                        source_x=0,
                        source_y=0,
                        source_width=960,
                        source_height=640,
                    ),
                )
            ],
            fake_session.start_calls,
        )
        self.assertTrue(shell.persisted)
        self.assertEqual(Path(temp_dir), shell._video_directory)
        self.assertEqual(
            [
                (
                    "live",
                    "Recording to microscope-20260405-010203.mov.",
                )
            ],
            shell.status_calls,
        )
        self.assertEqual([], shell.diagnostic_calls)

    def test_output_helpers_freeze_capture_crop_and_setting_paths(
        self,
    ) -> None:
        """Assert output helpers keep framing and persisted paths stable."""

        frame = PreviewFrame(
            width=1280,
            height=720,
            rgb_bytes=b"",
            frame_number=1,
        )

        fill_plan = _recording_crop_plan_from_frame(
            frame,
            framing_mode="fill",
            target_width=960,
            target_height=640,
        )
        crop_plan = _recording_crop_plan_from_frame(
            frame,
            framing_mode="crop",
            target_width=960,
            target_height=640,
        )

        self.assertEqual(
            (100, 0, 1080, 720),
            (
                fill_plan.source_x,
                fill_plan.source_y,
                fill_plan.source_width,
                fill_plan.source_height,
            ),
        )
        self.assertEqual(
            (280, 0, 720, 720),
            (
                crop_plan.source_x,
                crop_plan.source_y,
                crop_plan.source_width,
                crop_plan.source_height,
            ),
        )
        self.assertEqual(
            Path("/tmp/images"),
            _directory_setting_path(
                None,
                default=Path("/tmp/images"),
            ),
        )
        self.assertEqual(
            Path("/tmp/videos"),
            _directory_setting_path(
                "  ",
                default=Path("/tmp/videos"),
            ),
        )
        self.assertEqual("01:02:03", format_recording_duration(3_723_000))

    def test_settings_helpers_keep_text_and_shortcuts_stable(self) -> None:
        """Assert the small settings helpers stay predictable."""

        self.assertEqual("abc", _settings_text("  abc  ", default=""))
        self.assertEqual("fallback", _settings_text(None, default="fallback"))
        self.assertTrue(_settings_bool("yes", default=False))
        self.assertFalse(_settings_bool("no", default=True))
        self.assertEqual(
            "defaults/zoom_factor",
            _control_default_setting_key("zoom_factor"),
        )
        self.assertEqual("shortcuts/record", _shortcut_setting_key("record"))
        self.assertIsNone(
            _shortcut_conflict_label({"controls": "Ctrl+1", "fit": "Ctrl+2"})
        )
        self.assertEqual(
            "controls and fit share Ctrl+1.",
            _shortcut_conflict_label({"controls": "Ctrl+1", "fit": "Ctrl+1"}),
        )

    def test_named_preset_helpers_round_trip_json(self) -> None:
        """Assert named-preset storage stays deterministic and parseable."""

        payload = {
            "daylight": {
                "preview_framing_mode": "fit",
                "capture_framing_mode": "crop",
                "controls": {"brightness": 10},
            }
        }
        text = _named_presets_to_value(payload)

        self.assertEqual(payload, _named_presets_from_value(text))
        self.assertEqual({}, _named_presets_from_value("not json"))
        self.assertEqual({}, _named_presets_from_value(""))

    def test_apply_control_value_routes_backend_controls_and_persists_them(
        self,
    ) -> None:
        """Assert backend-owned controls apply through the active backend."""

        class FakeSettings:
            """Store settings values for the control-application path."""

            def __init__(self) -> None:
                """Initialize the settings value cache."""

                self.values: dict[str, object] = {}

            def value(self, key: str) -> object | None:
                """Return one stored settings value."""

                return self.values.get(key)

            def setValue(self, key: str, value: object) -> None:
                """Store one settings value."""

                self.values[key] = value

        class FakeBackend:
            """Record backend writes for the control-application path."""

            def __init__(self, shell: object) -> None:
                """Store the shell that records backend writes."""

                self._shell = shell

            def set_control_value(
                self,
                descriptor: CameraDescriptor,
                control_id: str,
                value: object,
            ) -> None:
                """Record the backend routing for a control write."""

                self._shell.backend_calls.append((control_id, value))

        class FakeShell:
            """Expose the minimum shell surface used by the control setter."""

            def __init__(self) -> None:
                """Initialize the fake shell state."""

                self._settings = FakeSettings()
                self.backend_calls: list[tuple[str, object]] = []
                self._backend = FakeBackend(self)
                self._preview_state = "live"
                self._controls_by_id = {
                    "brightness": CameraControl(
                        control_id="brightness",
                        label="Brightness",
                        kind="numeric",
                        value=0.0,
                        min_value=-100.0,
                        max_value=100.0,
                        step=1.0,
                    )
                }
                self.notice_calls: list[str] = []
                self.status_calls: list[tuple[str, str | None]] = []
                self.refresh_calls: list[str | None] = []
                self.diagnostic_calls: list[str] = []

            def _selected_descriptor(self) -> CameraDescriptor:
                """Return the fake selected descriptor."""

                return descriptor

            def _set_controls_notice(self, notice: str) -> None:
                """Record the visible controls notice."""

                self.notice_calls.append(notice)

            def _set_status(
                self,
                preview_state: str,
                notice: str | None = None,
            ) -> None:
                """Record the visible status update."""

                self.status_calls.append((preview_state, notice))

            def _refresh_control_surface(
                self,
                *,
                notice: str | None = None,
            ) -> None:
                """Record the requested surface refresh."""

                self.refresh_calls.append(notice)

            def _record_diagnostic_event(self, message: str) -> None:
                """Record the diagnostic event emitted by the shell."""

                self.diagnostic_calls.append(message)

        descriptor = CameraDescriptor(
            stable_id="camera-1",
            display_name="Camera 1",
            backend_name="qt_multimedia",
            device_selector="camera-1",
        )
        shell = FakeShell()

        PreviewApplication._apply_control_value(
            shell,
            "brightness",
            12.0,
            refresh_surface=True,
            status_notice=True,
        )

        self.assertEqual(
            12.0,
            shell._settings.values[
                _camera_control_setting_key(descriptor.stable_id, "brightness")
            ],
        )
        self.assertEqual([("brightness", 12.0)], shell.backend_calls)
        self.assertEqual([], shell.diagnostic_calls)
        self.assertEqual(["Updated Brightness."], shell.notice_calls)
        self.assertEqual([("live", "Updated Brightness.")], shell.status_calls)
        self.assertEqual(["Updated Brightness."], shell.refresh_calls)

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
        diagnostics_source = inspect.getsource(
            PreviewApplication._open_diagnostics
        )
        refresh_source = inspect.getsource(
            PreviewApplication._refresh_control_surface
        )
        camera_controls_source = inspect.getsource(
            PreviewApplication._build_camera_controls_section_widget
        )
        user_controls_source = inspect.getsource(
            PreviewApplication._build_user_controls_section_widget
        )
        reset_defaults_source = inspect.getsource(
            PreviewApplication._reset_controls_to_defaults
        )

        self.assertNotIn("def sync_field", numeric_builder_source)
        self.assertIn("def sync_slider", numeric_builder_source)
        self.assertIn("def handle_slider_change", numeric_builder_source)
        self.assertIn("def handle_slider_commit", numeric_builder_source)
        self.assertIn("def sync_spinbox", numeric_builder_source)
        self.assertIn("def handle_spinbox_change", numeric_builder_source)
        self.assertIn("QSpinBox", numeric_builder_source)
        self.assertIn("QDoubleSpinBox", numeric_builder_source)
        self.assertIn("Auto", numeric_builder_source)
        self.assertIn("auto_control_inverted", numeric_builder_source)
        self.assertNotIn("def handle_field_commit", numeric_builder_source)
        self.assertNotIn("def handle_step", numeric_builder_source)
        self.assertIn("def choose_directory", preferences_source)
        self.assertIn("Named Presets", preferences_source)
        self.assertIn("Save Current", preferences_source)
        self.assertIn("Apply Selected", preferences_source)
        self.assertIn("refresh_preset_combo", preferences_source)
        self.assertNotIn("_workspace_notes", window_source)
        self.assertIn("QTabWidget", diagnostics_source)
        self.assertIn("Recent Notices", diagnostics_source)
        self.assertIn("Exit Checks", diagnostics_source)
        self.assertIn("copy_current_report", diagnostics_source)
        self.assertIn("class ResizeAwareLabel", window_source)
        self.assertIn("class ResizeAwareMainWindow", window_source)
        self.assertIn("def resizeEvent", window_source)
        self.assertIn("QApplication.instance", launch_source)
        self.assertIn("PreferencesRole", actions_source)
        self.assertIn("AboutRole", actions_source)
        self.assertIn("QuitRole", actions_source)
        self.assertIn("setShortcut", actions_source)
        self.assertIn("fullscreen-surface", fullscreen_source)
        self.assertIn("Resolution", camera_controls_source)
        self.assertIn("Light", camera_controls_source)
        self.assertIn("Exposure Priority", camera_controls_source)
        self.assertIn("Zoom", camera_controls_source)
        self.assertIn('auto_checkbox_label="Auto"', camera_controls_source)
        self.assertIn("disable_when_auto=True", camera_controls_source)
        self.assertIn("Reset to Defaults", user_controls_source)
        self.assertIn("white_balance_temperature", user_controls_source)
        self.assertIn("white_balance_automatic", user_controls_source)
        self.assertIn("Gain", user_controls_source)
        self.assertIn("Power Line Frequency", user_controls_source)
        self.assertNotIn("_software_controls_for_descriptor", refresh_source)
        self.assertIn("source_format", reset_defaults_source)

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
