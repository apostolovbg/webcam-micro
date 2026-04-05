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
    _preferred_recording_output_suffix,
    _qt_recording_output_path_for_path,
    _request_macos_camera_permission,
    _request_qt_camera_permission,
    build_backend_plan,
    build_recording_file_filter,
    pack_preview_rgb_rows,
    request_camera_permission,
)


def _identity_completion_handler(handler: object) -> object:
    """Return the test handler unchanged."""

    return handler


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

    @mock.patch("webcam_micro.camera._load_avfoundation_modules")
    @mock.patch("webcam_micro.camera.sys.platform", "darwin")
    def test_avfoundation_control_surface_hides_backend_clutter(
        self,
        load_modules: mock.MagicMock,
    ) -> None:
        """Assert the macOS control surface keeps backend clutter hidden."""

        class FakeDevice:
            """Provide the minimum AVFoundation surface for the backend."""

            def localizedName(self) -> str:
                """Return the device name used for descriptor matching."""

                return "Microscope Camera"

            def uniqueID(self) -> str:
                """Return the device identifier used for descriptor
                matching."""

                return "camera-1"

            def isExposureModeSupported_(self, mode_value: int) -> bool:
                """Report support for the writable exposure modes."""

                return mode_value in {0, 2}

            def exposureMode(self) -> int:
                """Return the current writable exposure mode."""

                return 2

            def minAvailableVideoZoomFactor(self) -> float:
                """Return the minimum zoom factor."""

                return 1.0

            def maxAvailableVideoZoomFactor(self) -> float:
                """Return the maximum zoom factor."""

                return 4.0

            def videoZoomFactor(self) -> float:
                """Return the current zoom factor."""

                return 2.0

            def activeFormat(self) -> str:
                """Return one readable source-mode summary."""

                return "1920x1080"

            def lockForConfiguration_(self, _error) -> bool:
                """Pretend the device can be configured."""

                return True

            def unlockForConfiguration(self) -> None:
                """No-op for the fake device."""

                return None

            def setExposureMode_(self, mode_value: int) -> None:
                """Accept exposure updates in the test double."""

                return None

            def setVideoZoomFactor_(self, zoom_value: float) -> None:
                """Accept zoom updates in the test double."""

                return None

        class FakeCaptureDeviceClass:
            """Return one fake device for the macOS control backend."""

            @staticmethod
            def devicesWithMediaType_(media_type: object) -> tuple[FakeDevice]:
                """Return the fake device list for the selected media type."""

                return (FakeDevice(),)

        load_modules.return_value = (FakeCaptureDeviceClass, object())
        backend = AvFoundationCameraControlBackend()
        descriptor = CameraDescriptor(
            stable_id="camera-1",
            display_name="Microscope Camera",
            backend_name="avfoundation",
            device_selector="camera-1",
            native_identifier="camera-1",
        )

        control_ids = tuple(
            control.control_id for control in backend.list_controls(descriptor)
        )

        self.assertEqual(
            (
                "exposure_mode",
                "exposure_locked",
                "zoom_factor",
                "active_format",
                "restore_auto_exposure",
            ),
            control_ids,
        )
        self.assertNotIn("control_backend", control_ids)
        self.assertNotIn("low_light_boost_support", control_ids)

    def test_recording_container_helpers_track_supported_formats(self) -> None:
        """Assert recording helpers expose only supported video formats."""

        class FakeFormat:
            """Provide one simple Qt media file-format token."""

            def __init__(self, name: str) -> None:
                """Store the enum-style file-format name."""

                self.name = name

        class FakeQMediaFormat:
            """Provide the minimal media-format surface used by helpers."""

            class ConversionMode:
                """Expose the encode mode used by the helpers."""

                Encode = object()

            class FileFormat:
                """Expose the format tokens queried by the helpers."""

                AVI = FakeFormat("AVI")
                MPEG4 = FakeFormat("MPEG4")
                QuickTime = FakeFormat("QuickTime")

            def supportedFileFormats(
                self, mode: object
            ) -> tuple[FakeFormat, ...]:
                """Return the supported video formats for this runtime."""

                return (
                    self.FileFormat.QuickTime,
                    self.FileFormat.MPEG4,
                )

            def fileFormatDescription(self, file_format: FakeFormat) -> str:
                """Return one readable file-format label."""

                descriptions = {
                    "MPEG4": "MPEG-4 Video",
                    "QuickTime": "QuickTime Movie",
                }
                return descriptions[file_format.name]

            def fileFormatName(self, file_format: FakeFormat) -> str:
                """Return the enum-style file-format name."""

                return file_format.name

        fake_qt_multimedia = mock.MagicMock(QMediaFormat=FakeQMediaFormat)

        self.assertEqual(
            "MPEG-4 Video (*.mp4);;QuickTime Movie (*.mov)",
            build_recording_file_filter(fake_qt_multimedia),
        )
        self.assertEqual(
            ".mp4",
            _preferred_recording_output_suffix(fake_qt_multimedia),
        )

        output_path, file_format = _qt_recording_output_path_for_path(
            Path("/tmp/microscope"),
            fake_qt_multimedia,
        )
        self.assertEqual(Path("/tmp/microscope.mp4"), output_path)
        self.assertIs(file_format, FakeQMediaFormat.FileFormat.MPEG4)

        with self.assertRaises(CameraOutputError):
            _qt_recording_output_path_for_path(
                Path("/tmp/microscope.avi"),
                fake_qt_multimedia,
            )

    @mock.patch(
        "webcam_micro.camera.wrap_completion_handler",
        new=_identity_completion_handler,
    )
    @mock.patch("webcam_micro.camera._load_avfoundation_modules")
    @mock.patch("webcam_micro.camera.sys.platform", "darwin")
    def test_camera_permission_helper_requests_macos_prompt(
        self,
        load_modules: mock.MagicMock,
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
