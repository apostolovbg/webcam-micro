"""Tests for the macOS camera-permission adapter."""

from __future__ import annotations

import unittest
from unittest import mock

from webcam_micro.macos_permission import wrap_completion_handler


class MacOSPermissionTest(unittest.TestCase):
    """Verify the repo-owned macOS permission wrapper."""

    def test_wrap_completion_handler_is_identity_off_darwin(self) -> None:
        """Assert the helper leaves non-macOS callables untouched."""

        def handler(granted: object) -> object:
            """Return the granted value unchanged."""

            return granted

        with mock.patch("webcam_micro.macos_permission.sys.platform", "linux"):
            self.assertIs(handler, wrap_completion_handler(handler))
