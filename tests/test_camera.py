"""Stage 2 tests for the camera backend contract layer."""

from __future__ import annotations

import unittest

from webcam_micro.camera import (
    BackendPlan,
    CameraBackend,
    CameraDescriptor,
    CameraSession,
    FfmpegCameraBackend,
    FfmpegCameraSession,
    MissingCameraDependencyError,
    NullCameraBackend,
    NullCameraSession,
    PreviewFrame,
    build_backend_plan,
)


class CameraContractTest(unittest.TestCase):
    """Verify the preview-backend contract and documented backend plan."""

    def test_backend_plan_names_the_active_preview_target(self) -> None:
        """Assert the backend plan captures the Stage 2 preview target."""

        plan = build_backend_plan()

        self.assertIsInstance(plan, BackendPlan)
        self.assertEqual("FfmpegCameraBackend", plan.active_backend)
        self.assertIn("FFmpeg", plan.first_device_backend_target)
        self.assertTrue(any("newest frame" in note for note in plan.notes))

    def test_camera_contract_symbols_stay_explicit(self) -> None:
        """Assert the backend contract symbols stay public and named."""

        self.assertEqual("BackendPlan", BackendPlan.__name__)
        self.assertEqual("CameraBackend", CameraBackend.__name__)
        self.assertEqual("CameraDescriptor", CameraDescriptor.__name__)
        self.assertEqual("CameraSession", CameraSession.__name__)
        self.assertEqual(
            "MissingCameraDependencyError",
            MissingCameraDependencyError.__name__,
        )
        self.assertEqual("FfmpegCameraBackend", FfmpegCameraBackend.__name__)
        self.assertEqual("FfmpegCameraSession", FfmpegCameraSession.__name__)
        self.assertEqual("NullCameraSession", NullCameraSession.__name__)
        self.assertEqual("PreviewFrame", PreviewFrame.__name__)

    def test_null_backend_discovers_no_cameras(self) -> None:
        """Assert the fallback backend stays empty by design."""

        backend = NullCameraBackend()

        self.assertEqual((), backend.discover_cameras())

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
