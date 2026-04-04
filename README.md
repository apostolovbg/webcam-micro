# webcam-micro
**Doc ID:** README
**Doc Type:** repo-readme
**Project Version:** 0.1.0a1
**Last Updated:** 2026-04-04
**DevCovenant Version:** 1.0.1b1

<!-- DEVCOV:BEGIN -->

<!-- DEVCOV:END -->

Cross-platform microscope camera application distributed as a Python package
on PyPI.

## Table of Contents
1. [Overview](#overview)
2. [Alpha Status](#alpha-status)
3. [What Works Today](#what-works-today)
4. [Installation](#installation)
5. [Launch](#launch)
6. [Windowed Workspace](#windowed-workspace)
7. [Fullscreen Workspace](#fullscreen-workspace)
8. [Preview and Framing](#preview-and-framing)
9. [Camera Controls](#camera-controls)
10. [Capture and Recording](#capture-and-recording)
11. [Preferences, Defaults, and Presets](#preferences-defaults-and-presets)
12. [Diagnostics and Status](#diagnostics-and-status)
13. [Platform Notes](#platform-notes)
14. [Current Limitations](#current-limitations)
15. [Packaging and Distribution](#packaging-and-distribution)
16. [Security, Privacy, and Support](#security-privacy-and-support)
17. [Repository Notes](#repository-notes)
18. [License](#license)

## Overview
`webcam-micro` is a preview-first microscope camera application for live
viewing, camera control, still capture, and recording.

![webcam-micro preview](https://raw.githubusercontent.com/apostolovbg/webcam-micro/main/webcam_micro/webcam-micro.png)

The current alpha release runs on the Qt Widgets shell baseline. Today it opens
a native desktop workspace with a menu bar, toolbar, central preview area,
toggleable controls dock, still-image save, native recording, session
preferences, diagnostics, and a compact fullscreen command surface with
expanded and collapsed states. Preview framing, capture framing, camera
selection, window layout, current preset name, output folders, and
per-camera control values persist across launches. User-editable defaults,
keyboard shortcuts, and named presets are available, while broader platform
validation remains in progress.

## Alpha Status
`webcam-micro` is now the official alpha release.
The release version is sourced from `webcam_micro/VERSION`, and the shell
chrome carries the full legal-owner notice.
The Qt Widgets baseline is usable for live preview, camera control, still
capture, recording, presets, and diagnostics, but backend-specific
recording containers, camera controls, and platform validation still need
operational testing before beta planning begins.

## What Works Today
- Launch and entrypoint: the application starts from the `webcam-micro`
  command and can also run from source during development.
- Windowed workspace: the main shell keeps the preview central while the
  menu bar, toolbar, controls dock, and status bar expose the primary
  microscope actions.
- Fullscreen workspace: the preview expands to the full screen and the
  command surface collapses into a compact overlay with safe exit paths.
- Preview and framing: live preview supports fit, fill, and centered crop
  modes, and the preview can be resized without losing the newest frame.
- Camera controls: the active backend exposes numeric, boolean, enum,
  read-only, and action controls when the device supports them.
- Capture and recording: still images and recordings use the current capture
  framing and save through native dialogs or native recording controls.
- Preferences, defaults, and presets: framing, output folders, keyboard
  shortcuts, defaults, and named presets are stored with the workspace.
- Diagnostics and status: the shell reports runtime state, recent failures,
  and prototype exit checks in a visible diagnostics dialog and status bar.
- Platform notes: Qt Multimedia owns the camera and recording stack, while
  platform and device differences still shape the available controls.

## Installation
The packaged app supports Python `3.11+`.
Install it from PyPI or a built wheel, then launch it with:

```bash
webcam-micro
```

## Launch
The application starts in a preview-first Qt Widgets window.
The command bar and native menu bar provide access to the core camera,
capture, framing, preference, and diagnostics actions without requiring a
terminal once the app is running.

## Windowed Workspace
The main window keeps the microscope preview central.
The native menu bar carries File, Edit, View, Camera, Capture, Tools, and
Help actions. The toolbar keeps the main working actions close to the live
image, including controls, camera refresh, open and close, framing, still
capture, recording, fullscreen, and preferences. The right edge of the
toolbar displays `© 2026 Black Epsilon Ltd. and Apostol Apostolov`.

The controls dock can be shown or hidden so camera controls do not consume
preview space permanently. Numeric controls use guvcview-style affordances:
a slider, min/mid/max labels, and an adjacent field with step buttons.
Boolean, enumerated, read-only, and action controls appear when the backend
exposes them.

## Fullscreen Workspace
Fullscreen replaces the windowed chrome with a compact command surface.
Expanded fullscreen shows the core microscope actions plus collapse and safe
windowed exit. Collapsed fullscreen keeps only collapse/expand and the
fullscreen/windowed toggle visible. Escape returns to windowed mode.

## Preview and Framing
Preview framing supports fit, fill, and centered crop modes.
The live preview rerenders from the newest cached frame when the window or
preview area changes size. Capture framing is separate from preview framing
so stills and videos can follow their own output rules without changing the
live microscope view.

## Camera Controls
The app exposes the real control surface reported by the active camera and
backend. Supported controls include numeric, boolean, enumerated, read-only,
and action widgets. The app tolerates partial control sets and does not fail
just because a camera lacks an expected control.

On macOS, the active camera can bridge into AVFoundation through
`rubicon-objc` when the backend exposes real native controls.

## Capture and Recording
Still images are saved through native file dialogs using PNG or JPEG output.
Recording starts and stops natively in the Qt shell and shows elapsed status
while it runs. Recorded video uses the active capture-framing choice and
remembers the output folder across launches.

## Preferences, Defaults, and Presets
Preferences store preview framing, capture framing, output folders, editable
defaults, keyboard shortcuts, and named presets.
The app remembers the current preset name, restores per-camera control values
when available, and lets users save or apply named presets from the same
preferences dialog.

## Diagnostics and Status
The diagnostics dialog shows a runtime report, a recent-failures log, and
prototype exit checks. The status bar summarizes backend, camera, source
mode, preview framing, capture framing, controls state, preset name,
recording state, and the current status notice.

## Platform Notes
Qt Multimedia owns camera discovery, preview, and recording.
Actual controls and container support vary by camera, backend, and platform.
The app only surfaces controls the backend can actually use.

## Current Limitations
Wider cross-platform recording validation is still planned on top of the Qt
shell baseline.
Some camera controls and output formats remain backend-dependent.

## Packaging and Distribution
`webcam-micro` is shipped as a Python package on PyPI.
The package-facing README lives at `webcam_micro/README.md`, where the
repo-only notes are stripped out before packaging. The launcher name is
`webcam-micro`, and the source package remains runnable during development.

## Security, Privacy, and Support
`webcam-micro` is a local desktop utility by default.
The core camera workflow does not depend on cloud services, accounts, or
telemetry, and the app should stay usable without terminal interaction
during normal microscope work.

<!-- REPO-ONLY:BEGIN -->
## Repository Notes
The package-facing mirror is synchronized from this file through the
`package-doc-sync` policy. Keep user-facing behavior documented here first,
then let the mirror carry only the same public-facing content.

### Development Quick Start
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

### Docs Map
- `README.md`: canonical full repository readme
- `webcam_micro/README.md`: package-facing mirror stripped of repo-only
  blocks
- `SPEC.md`: durable product contract and scope
- `PLAN.md`: active build roadmap and slice ordering
- `CHANGELOG.md`: newest-first change history
- `AGENTS.md`: workflow contract and active policy output

### Workflow Notes
Follow the governed edit sequence in `AGENTS.md`.
Keep durable product rules in `SPEC.md`, active implementation sequencing in
`PLAN.md`, and landed history in `CHANGELOG.md`.

### Configuration Checkpoints
The current preview runtime depends on `PySide6` through the package-runtime
lock under `webcam_micro/`.
On macOS the runtime also depends on `rubicon-objc` for the AVFoundation
control bridge.
<!-- REPO-ONLY:END -->

## License
Document the repository licensing terms here.
