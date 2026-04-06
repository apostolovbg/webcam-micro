"""Structured error-reporting helpers for webcam-micro."""

from __future__ import annotations

from dataclasses import dataclass


class WebcamMicroError(Exception):
    """Base class for typed, user-facing webcam-micro failures."""


@dataclass(frozen=True)
class ErrorReport:
    """Describe one user-facing error and its diagnostic text."""

    error_type: str
    display_message: str
    diagnostic_message: str


def build_error_report(error: BaseException) -> ErrorReport:
    """Return structured notice and diagnostic text for one error."""

    error_type = error.__class__.__name__
    display_message = str(error).strip() or error_type
    diagnostic_message = f"{error_type}: {display_message}"
    return ErrorReport(
        error_type=error_type,
        display_message=display_message,
        diagnostic_message=diagnostic_message,
    )
