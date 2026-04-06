"""Public launcher that prepares the runtime before starting the app."""

from __future__ import annotations

import sys
from typing import Sequence

from webcam_micro.error_reporting import WebcamMicroError, build_error_report
from webcam_micro.runtime_bootstrap import bootstrap_runtime


def _run_app(argv: Sequence[str]) -> int:
    """Import the GUI entrypoint lazily after the runtime is ready."""

    from webcam_micro.app import main as app_main

    return app_main(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Bootstrap the runtime interpreter and then start the application."""

    argv_list = list(sys.argv[1:] if argv is None else argv)
    try:
        bootstrap_runtime(argv_list)
    except WebcamMicroError as exc:
        raise SystemExit(build_error_report(exc).display_message) from exc
    return _run_app(argv_list)
