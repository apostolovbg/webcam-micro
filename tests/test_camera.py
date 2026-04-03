"""Stage 1 tests for the camera backend contract layer."""

from __future__ import annotations

import unittest

from webcam_micro.camera import (
    CameraDescriptor,
    NullCameraBackend,
    build_backend_plan,
)


class CameraContractTest(unittest.TestCase):
    """Verify the placeholder backend and documented backend plan."""

    def test_backend_plan_names_the_first_real_target(self) -> None:
        """Assert the backend plan captures the OpenCV target."""

        plan = build_backend_plan()

        self.assertEqual("NullCameraBackend", plan.stage_one_backend)
        self.assertIn("OpenCV", plan.first_device_backend_target)

    def test_null_backend_discovers_no_cameras(self) -> None:
        """Assert the placeholder backend stays empty by design."""

        backend = NullCameraBackend()

        self.assertEqual((), backend.discover_cameras())

    def test_null_backend_opens_placeholder_session(self) -> None:
        """Assert the placeholder backend still provides session semantics."""

        backend = NullCameraBackend()
        descriptor = CameraDescriptor(
            stable_id="stage1-demo",
            display_name="Stage 1 Demo Camera",
            backend_name=backend.backend_name,
        )

        session = backend.open_session(descriptor)

        self.assertFalse(session.closed)
        self.assertEqual(descriptor, session.descriptor)
        session.close()
        self.assertTrue(session.closed)
