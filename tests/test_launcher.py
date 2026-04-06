"""Tests for the launcher and runtime bootstrap wiring."""

from __future__ import annotations

import inspect
import unittest
from unittest import mock

from webcam_micro.launcher import main as launcher_main
from webcam_micro.runtime_bootstrap import RuntimeBootstrapError


class LauncherTest(unittest.TestCase):
    """Verify the public launcher delegates through the bootstrap path."""

    def test_launcher_main_symbol_stays_explicit(self) -> None:
        """Assert the launcher exports the expected entrypoint name."""

        self.assertEqual("main", launcher_main.__name__)
        self.assertTrue(callable(launcher_main))

    def test_launcher_bootstraps_before_running_the_app(self) -> None:
        """Assert the launcher prepares the runtime before app startup."""

        with (
            mock.patch(
                "webcam_micro.launcher.bootstrap_runtime",
            ) as bootstrap_runtime_mock,
            mock.patch(
                "webcam_micro.launcher._run_app",
                return_value=0,
            ) as run_app_mock,
        ):
            self.assertEqual(0, launcher_main(["--smoke-test"]))

        bootstrap_runtime_mock.assert_called_once_with(["--smoke-test"])
        run_app_mock.assert_called_once_with(["--smoke-test"])

    def test_launcher_reports_bootstrap_failures_as_system_exit(self) -> None:
        """Assert bootstrap failures surface as typed launcher exits."""

        with mock.patch(
            "webcam_micro.launcher.bootstrap_runtime",
            side_effect=RuntimeBootstrapError("boom"),
        ):
            with self.assertRaises(SystemExit) as context:
                launcher_main(["--smoke-test"])

        self.assertEqual("boom", str(context.exception))

    def test_python_module_launcher_mentions_the_bootstrap_module(
        self,
    ) -> None:
        """Assert the module launcher keeps the runtime hop visible."""

        from webcam_micro import __main__ as module_main

        source = inspect.getsource(module_main)
        self.assertIn("launcher", source)
        self.assertIn("SystemExit", source)
