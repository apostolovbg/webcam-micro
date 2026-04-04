"""Stage 4 tests for the camera backend and control contract layer."""

from __future__ import annotations

import unittest

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
    CameraSession,
    FfmpegCameraBackend,
    FfmpegCameraSession,
    MissingCameraDependencyError,
    NullCameraBackend,
    NullCameraControlBackend,
    NullCameraSession,
    PreviewFrame,
    build_backend_plan,
)


class CameraContractTest(unittest.TestCase):
    """Verify the preview-backend contract and documented backend plan."""

    def test_backend_plan_names_the_active_preview_target(self) -> None:
        """Assert the backend plan captures the Stage 4 preview target."""

        plan = build_backend_plan()

        self.assertIsInstance(plan, BackendPlan)
        self.assertEqual("FfmpegCameraBackend", plan.active_backend)
        self.assertIn("FFmpeg", plan.first_device_backend_target)
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
        self.assertEqual("CameraSession", CameraSession.__name__)
        self.assertEqual(
            "CameraControlApplyError",
            CameraControlApplyError.__name__,
        )
        self.assertEqual(
            "MissingCameraDependencyError",
            MissingCameraDependencyError.__name__,
        )
        self.assertEqual("FfmpegCameraBackend", FfmpegCameraBackend.__name__)
        self.assertEqual("FfmpegCameraSession", FfmpegCameraSession.__name__)
        self.assertEqual("NullCameraBackend", NullCameraBackend.__name__)
        self.assertEqual(
            "NullCameraControlBackend",
            NullCameraControlBackend.__name__,
        )
        self.assertEqual("NullCameraSession", NullCameraSession.__name__)
        self.assertEqual("PreviewFrame", PreviewFrame.__name__)

        avfoundation_backend = AvFoundationCameraControlBackend()
        self.assertIsInstance(avfoundation_backend.available, bool)

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
