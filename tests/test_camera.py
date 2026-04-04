"""Stage 4 tests for the camera backend and control contract layer."""

from __future__ import annotations

import inspect
import unittest
from pathlib import Path
from unittest import mock

from webcam_micro.camera import (
    AvFoundationCameraControlBackend,
    BackendPlan,
    CameraBackend,
    CameraControl,
    CameraControlApplyError,
    CameraControlBackend,
    CameraControlChoice,
    CameraControlError,
    CameraDescriptor,
    CameraOutputError,
    CameraSession,
    FfmpegCameraBackend,
    FfmpegCameraSession,
    MissingCameraDependencyError,
    NullCameraBackend,
    NullCameraControlBackend,
    NullCameraSession,
    PreviewFrame,
    QtCameraBackend,
    QtCameraSession,
    RecordingCropPlan,
    _request_macos_camera_permission,
    _request_qt_camera_permission,
    build_backend_plan,
    pack_preview_rgb_rows,
    request_camera_permission,
)


class CameraContractTest(unittest.TestCase):
    """Verify the preview-backend contract and documented backend plan."""

    def test_backend_plan_names_the_active_preview_target(self) -> None:
        """Assert the backend plan captures the Qt preview target."""

        plan = build_backend_plan()

        self.assertIsInstance(plan, BackendPlan)
        self.assertEqual("QtCameraBackend", plan.active_backend)
        self.assertIn("Qt Multimedia", plan.first_device_backend_target)
        self.assertTrue(any("newest frame" in note for note in plan.notes))
        self.assertTrue(any("AVFoundation" in note for note in plan.notes))

    def test_camera_contract_symbols_stay_explicit(self) -> None:
        """Assert the backend contract symbols stay public and named."""

        self.assertEqual("BackendPlan", BackendPlan.__name__)
        self.assertEqual(
            "AvFoundationCameraControlBackend",
            AvFoundationCameraControlBackend.__name__,
        )
        self.assertEqual("CameraBackend", CameraBackend.__name__)
        self.assertEqual(
            "CameraControlBackend",
            CameraControlBackend.__name__,
        )
        self.assertEqual("CameraControl", CameraControl.__name__)
        self.assertEqual("CameraControlChoice", CameraControlChoice.__name__)
        self.assertEqual("CameraDescriptor", CameraDescriptor.__name__)
        self.assertEqual("CameraControlError", CameraControlError.__name__)
        self.assertEqual("CameraOutputError", CameraOutputError.__name__)
        self.assertEqual("CameraSession", CameraSession.__name__)
        self.assertEqual(
            "CameraControlApplyError",
            CameraControlApplyError.__name__,
        )
        self.assertEqual(
            "MissingCameraDependencyError",
            MissingCameraDependencyError.__name__,
        )
        self.assertEqual("QtCameraBackend", QtCameraBackend.__name__)
        self.assertEqual("QtCameraSession", QtCameraSession.__name__)
        self.assertEqual("FfmpegCameraBackend", FfmpegCameraBackend.__name__)
        self.assertEqual("FfmpegCameraSession", FfmpegCameraSession.__name__)
        self.assertEqual("NullCameraBackend", NullCameraBackend.__name__)
        self.assertEqual(
            "NullCameraControlBackend",
            NullCameraControlBackend.__name__,
        )
        self.assertEqual("NullCameraSession", NullCameraSession.__name__)
        self.assertEqual("PreviewFrame", PreviewFrame.__name__)
        self.assertEqual("RecordingCropPlan", RecordingCropPlan.__name__)

        avfoundation_backend = AvFoundationCameraControlBackend()
        self.assertIsInstance(avfoundation_backend.available, bool)

    @mock.patch("rubicon.objc.Block", side_effect=lambda func: func)
    @mock.patch("webcam_micro.camera._load_avfoundation_modules")
    @mock.patch("webcam_micro.camera.sys.platform", "darwin")
    def test_camera_permission_helper_requests_macos_prompt(
        self,
        load_modules: mock.MagicMock,
        _block: mock.MagicMock,
    ) -> None:
        """Assert the macOS helper requests camera access explicitly."""

        class FakeLoop:
            """Provide the minimal Qt event-loop surface for the helper."""

            def __init__(self) -> None:
                """Initialize the test event-loop bookkeeping."""

                self.quit_called = False
                self.exec_called = False

            def quit(self) -> None:
                """Record that the helper asked the loop to stop."""

                self.quit_called = True

            def exec(self) -> None:
                """Record that the helper entered the loop."""

                self.exec_called = True

        class FakeQtCore:
            """Provide the QtCore pieces used by the permission helper."""

            QEventLoop = FakeLoop

        class FakeCaptureDeviceClass:
            """Record the macOS permission request path."""

            requested_media_types: list[object] = []

            @staticmethod
            def authorizationStatusForMediaType_(media_type: object) -> int:
                """Return the prompt-needed authorization state."""

                return 0

            @classmethod
            def requestAccessForMediaType_completionHandler_(
                cls,
                media_type: object,
                completion_handler,
            ) -> None:
                """Record the prompt request and invoke the callback."""

                cls.requested_media_types.append(media_type)
                completion_handler(True)

        media_type = object()
        load_modules.return_value = (FakeCaptureDeviceClass, media_type)

        granted, notice = request_camera_permission(FakeQtCore)

        self.assertTrue(granted)
        self.assertEqual("", notice)
        self.assertEqual(
            [media_type], FakeCaptureDeviceClass.requested_media_types
        )

    def test_camera_permission_helper_mentions_callback_names(self) -> None:
        """Assert the permission helper keeps the callback symbols visible."""

        macos_source = inspect.getsource(_request_macos_camera_permission)
        qt_source = inspect.getsource(_request_qt_camera_permission)

        self.assertIn("completion_handler", macos_source)
        self.assertIn("PermissionReceiver", qt_source)
        self.assertIn("on_permission", qt_source)

    def test_null_backend_discovers_no_cameras(self) -> None:
        """Assert the fallback backend stays empty by design."""

        backend = NullCameraBackend()
        control_backend = NullCameraControlBackend()
        descriptor = CameraDescriptor(
            stable_id="null-camera",
            display_name="Null Camera",
            backend_name=backend.backend_name,
            device_selector="null-camera",
        )

        self.assertEqual((), backend.discover_cameras())
        self.assertEqual(
            (),
            backend.list_controls(descriptor),
        )
        self.assertEqual((), control_backend.list_controls(descriptor))

    def test_null_backend_opens_placeholder_session(self) -> None:
        """Assert the fallback backend still provides session semantics."""

        backend = NullCameraBackend()
        descriptor = CameraDescriptor(
            stable_id="stage1-demo",
            display_name="Stage 1 Demo Camera",
            backend_name=backend.backend_name,
            device_selector="stage1-demo",
        )

        session = backend.open_session(descriptor)

        self.assertFalse(session.closed)
        self.assertIsInstance(session, NullCameraSession)
        self.assertEqual(descriptor, session.descriptor)
        self.assertIsNone(session.failure_reason)
        self.assertIsNone(session.get_latest_frame())
        self.assertFalse(session.recording_available)
        self.assertEqual("not ready", session.recording_state)
        self.assertEqual(0, session.recording_duration_milliseconds)
        self.assertIsNone(session.recording_output_path)
        self.assertIsNone(session.recording_error)
        with self.assertRaises(CameraOutputError):
            session.start_recording(
                Path("/tmp/null-camera.mp4"),
                crop_plan=RecordingCropPlan(
                    source_x=0,
                    source_y=0,
                    source_width=320,
                    source_height=240,
                ),
            )
        self.assertIsNone(session.stop_recording())
        session.close()
        self.assertTrue(session.closed)

    def test_null_backend_rejects_control_writes(self) -> None:
        """Assert the fallback backend fails softly on control writes."""

        backend = NullCameraBackend()
        descriptor = CameraDescriptor(
            stable_id="null-camera",
            display_name="Null Camera",
            backend_name=backend.backend_name,
            device_selector="null-camera",
        )

        with self.assertRaises(CameraControlApplyError):
            backend.set_control_value(descriptor, "zoom_factor", 2.0)
        with self.assertRaises(CameraControlApplyError):
            backend.trigger_control_action(
                descriptor,
                "restore_auto_exposure",
            )

        control_backend = NullCameraControlBackend()
        with self.assertRaises(CameraControlApplyError):
            control_backend.trigger_control_action(
                descriptor,
                "restore_auto_exposure",
            )

    def test_camera_control_preserves_typed_metadata(self) -> None:
        """Assert control dataclasses preserve the metadata contract."""

        control = CameraControl(
            control_id="zoom_factor",
            label="Zoom Factor",
            kind="numeric",
            value=1.0,
            choices=(CameraControlChoice(value="one", label="One"),),
            min_value=1.0,
            max_value=4.0,
            step=0.1,
            read_only=False,
            enabled=True,
            unit="x",
            details="Camera zoom factor.",
            action_label="Reset",
        )

        self.assertEqual("zoom_factor", control.control_id)
        self.assertEqual("Zoom Factor", control.label)
        self.assertEqual("numeric", control.kind)
        self.assertEqual(1.0, control.value)
        self.assertEqual("one", control.choices[0].value)
        self.assertEqual("One", control.choices[0].label)
        self.assertEqual(1.0, control.min_value)
        self.assertEqual(4.0, control.max_value)
        self.assertEqual(0.1, control.step)
        self.assertFalse(control.read_only)
        self.assertTrue(control.enabled)
        self.assertEqual("x", control.unit)
        self.assertEqual("Camera zoom factor.", control.details)
        self.assertEqual("Reset", control.action_label)

    def test_preview_frame_preserves_rgb_dimensions(self) -> None:
        """Assert preview frames carry the UI-ready RGB payload metadata."""

        frame = PreviewFrame(
            width=320,
            height=240,
            rgb_bytes=b"rgb",
            frame_number=4,
        )

        self.assertEqual(320, frame.width)
        self.assertEqual(240, frame.height)
        self.assertEqual(b"rgb", frame.rgb_bytes)
        self.assertEqual(4, frame.frame_number)

    def test_pack_preview_rgb_rows_removes_row_padding(self) -> None:
        """Assert padded RGB rows compact into one packed preview payload."""

        self.assertEqual(
            bytes(range(12)),
            pack_preview_rgb_rows(
                bytes(
                    [
                        0,
                        1,
                        2,
                        3,
                        4,
                        5,
                        90,
                        91,
                        6,
                        7,
                        8,
                        9,
                        10,
                        11,
                        92,
                        93,
                    ]
                ),
                width=2,
                height=2,
                bytes_per_line=8,
            ),
        )
