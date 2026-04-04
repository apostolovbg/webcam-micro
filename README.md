# webcam-micro
**Doc ID:** README
**Doc Type:** repo-readme
**Project Version:** 0.0.1
**Last Updated:** 2026-04-04
**DevCovenant Version:** 1.0.1b1

<!-- DEVCOV:BEGIN -->

<!-- DEVCOV:END -->

Cross-platform microscope camera application distributed as a Python package
on PyPI.

## Overview
`webcam-micro` is a preview-first microscope camera application for live
viewing, camera control, still capture, and recording.

The current prototype is on the Qt Widgets migration foundation. Today it
opens a native desktop Qt Widgets workspace with a native menu bar, toolbar,
Qt Multimedia-backed camera discovery, live preview, typed camera controls,
fit/fill/crop framing, a toggleable controls dock, a compact fullscreen
command surface with expanded and collapsed states, and visible session
status. Still capture, video recording, preferences, persistence, and
diagnostics remain in progress.

## Installation
The packaged app supports Python `3.11+`.
After installation, launch it with:

```bash
webcam-micro
```

## What Works Today
- native desktop menu bar and toolbar on the Qt Widgets shell baseline
- live camera discovery through Qt Multimedia device inputs
- safe session open, close, and camera switching
- low-latency preview that keeps only the newest surfaced frame
- typed camera controls with numeric, boolean, enum, read-only, and action
  widgets
- fit, fill, and microscope-centered crop preview framing
- toggleable controls dock that keeps the preview central when hidden
- compact fullscreen command surface with expanded and collapsed states
- visible backend, camera, framing, and recording status summaries

## Interface
The main window is organized around the microscope preview.
The native menu bar and toolbar keep the primary actions close to the live
image, the preview workspace stays central, the controls dock can be shown or
hidden when needed, fullscreen replaces the windowed chrome with a compact
overlay command surface, and the status bar keeps backend and session state
visible in windowed mode.

Numeric camera controls use guvcview-style affordances.
Each numeric control keeps a slider, min/mid/max labels, and a nearby value
field with step buttons that clears invalid typed input instead of silently
accepting a bad value.

## Platform Notes
The preview path is built on Qt Multimedia camera devices and capture
sessions.
On macOS, camera controls can bridge into AVFoundation through
`rubicon-objc` when the active device exposes real controls.
Available controls and source capabilities still depend on the camera and
platform, so the app only surfaces what the active backend can actually use.

## Current Limitations
The current prototype does not yet finish the capture and persistence parts of
the workstation flow.
Still capture, video recording, preferences, defaults, presets, shortcut
editing, and diagnostics are planned slices on top of the Qt shell
foundation that already landed.

<!-- REPO-ONLY:BEGIN -->
## Development Quick Start
Run the headless source entrypoint smoke test:

```bash
.venv/bin/python -m webcam_micro --smoke-test
```

Launch the prototype main window from source:

```bash
.venv/bin/python -m webcam_micro
```

Build installable package artifacts:

```bash
.venv/bin/python -m build --sdist --wheel --outdir /tmp/webcam-micro-dist
```

## Workflow
Follow the governed edit sequence in `AGENTS.md`.
Keep durable product rules in `SPEC.md`, active implementation sequencing in
`PLAN.md`, and landed history in `CHANGELOG.md`.

## Docs Map
- `README.md`: canonical full repository readme
- `webcam_micro/README.md`: package-facing mirror stripped of repo-only blocks
- `SPEC.md`: durable product contract and scope
- `PLAN.md`: active build roadmap and slice ordering
- `CHANGELOG.md`: newest-first change history
- `AGENTS.md`: workflow contract and active policy output

## Configuration Checkpoints
The current preview runtime depends on `PySide6` through the package-runtime
lock under `webcam_micro/`.
On macOS the runtime also depends on `rubicon-objc` for the AVFoundation
control bridge.

The package-facing README now mirrors this file through the
`package-doc-sync` policy and strips content fenced inside the repo-only
marker block shown in this document.
<!-- REPO-ONLY:END -->

## Security, Privacy, and Support
`webcam-micro` is a local desktop utility by default.
The core camera workflow does not depend on cloud services, accounts, or
telemetry, and the app should stay usable without terminal interaction during
normal microscope work.

## License
Document the repository licensing terms here.
