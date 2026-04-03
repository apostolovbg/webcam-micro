"""Stage 1 tests for the GUI shell description layer."""

from __future__ import annotations

import unittest

from webcam_micro.ui import build_shell_spec


class ShellSpecTest(unittest.TestCase):
    """Verify the headless-friendly shell description."""

    def test_shell_spec_mentions_stage_one_baseline(self) -> None:
        """Assert the shell spec captures the GUI and backend choices."""

        spec = build_shell_spec()
        combined_body = " ".join(spec.hero_body)

        self.assertEqual("webcam-micro prototype shell", spec.title)
        self.assertEqual("litera", spec.theme_name)
        self.assertIn("ttkbootstrap", combined_body)
        self.assertIn("OpenCV", combined_body)
