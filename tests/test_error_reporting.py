"""Tests for the structured error-reporting helpers."""

from __future__ import annotations

import unittest

from webcam_micro.error_reporting import (
    ErrorReport,
    WebcamMicroError,
    build_error_report,
)


class ErrorReportingTest(unittest.TestCase):
    """Verify the shared error-reporting layer."""

    def test_error_reporting_symbols_stay_explicit(self) -> None:
        """Assert the shared error-reporting names stay importable."""

        self.assertEqual("WebcamMicroError", WebcamMicroError.__name__)
        self.assertEqual("ErrorReport", ErrorReport.__name__)
        self.assertTrue(callable(build_error_report))

    def test_error_report_uses_the_error_type_as_a_fallback(self) -> None:
        """Assert empty messages still produce structured notices."""

        report = build_error_report(WebcamMicroError())

        self.assertEqual("WebcamMicroError", report.error_type)
        self.assertEqual("WebcamMicroError", report.display_message)
        self.assertEqual(
            "WebcamMicroError: WebcamMicroError",
            report.diagnostic_message,
        )
