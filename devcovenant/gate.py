#!/usr/bin/env python3
"""Gate command implementation for DevCovenant."""

from __future__ import annotations

if __package__ in {None, ""}:  # pragma: no cover
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse

import devcovenant.core.cli_support as cli_args_module


def _build_parser() -> argparse.ArgumentParser:
    """Build parser for gate command."""
    parser = cli_args_module.build_command_parser(
        "gate",
        "Run DevCovenant gate session lifecycle commands.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--start",
        action="store_true",
        help="Run pre-commit and record gate session start evidence.",
    )
    group.add_argument(
        "--end",
        action="store_true",
        help="Run pre-commit and record gate session end evidence.",
    )
    group.add_argument(
        "--mid",
        action="store_true",
        help=(
            "Run a non-lifecycle mid-session pre-commit sweep "
            "(mutating checks/autofix may apply)."
        ),
    )
    group.add_argument(
        "--status",
        action="store_true",
        help=(
            "Show short gate session status without mutating lifecycle state."
        ),
    )
    return parser


def run(args: argparse.Namespace) -> int:
    """Execute gate command."""
    from devcovenant.core.execution import (
        print_banner,
        print_step,
        resolve_repo_root,
    )
    from devcovenant.core.gate_runtime import (
        run_pre_commit_gate,
        show_gate_status,
    )

    repo_root = resolve_repo_root(require_install=True)
    if getattr(args, "status", False):
        return show_gate_status(repo_root)

    if getattr(args, "start", False):
        stage = "start"
    elif getattr(args, "mid", False):
        stage = "mid"
    else:
        stage = "end"

    print_banner("Devflow gate", "🚦")
    print_step(f"Running `{stage}` pre-commit gate", "▶️")
    exit_code = run_pre_commit_gate(repo_root, stage)
    if exit_code == 0:
        if stage == "mid":
            print_step("Mid gate completed", "✅")
        else:
            print_step(f"{stage.capitalize()} gate recorded", "✅")
    return exit_code


def main(argv: list[str] | None = None) -> None:
    """CLI entry point."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    cli_args_module.apply_output_mode_override_from_namespace(args)
    raise SystemExit(run(args))


if __name__ == "__main__":
    main()
