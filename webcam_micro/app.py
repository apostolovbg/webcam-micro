"""Application entrypoints for the Stage 1 prototype foundation."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Sequence

from webcam_micro import APP_NAME, BACKEND_STRATEGY, GUI_BASELINE, PACKAGE_NAME
from webcam_micro.camera import build_backend_plan
from webcam_micro.ui import MissingGuiDependencyError, launch_main_window


@dataclass(frozen=True)
class LaunchPlan:
    """Describe the chosen Stage 1 launch baseline."""

    app_name: str
    package_name: str
    entrypoint_name: str
    gui_baseline: str
    backend_strategy: str
    first_device_backend_target: str


def build_launch_plan() -> LaunchPlan:
    """Return the current Stage 1 application-foundation decision."""

    backend_plan = build_backend_plan()
    return LaunchPlan(
        app_name=APP_NAME,
        package_name=PACKAGE_NAME,
        entrypoint_name="webcam-micro",
        gui_baseline=GUI_BASELINE,
        backend_strategy=BACKEND_STRATEGY,
        first_device_backend_target=backend_plan.first_device_backend_target,
    )


def _build_parser() -> argparse.ArgumentParser:
    """Build the Stage 1 command-line parser."""

    parser = argparse.ArgumentParser(prog="webcam-micro")
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="exercise the Stage 1 entrypoint without launching the GUI",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Stage 1 application entrypoint."""

    parsed = _build_parser().parse_args(argv)
    if parsed.smoke_test:
        return 0
    try:
        return launch_main_window()
    except MissingGuiDependencyError as exc:
        raise SystemExit(str(exc)) from exc
