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

The current prototype is on the first Flet rewrite baseline. Today it opens a
single-window desktop workspace with camera discovery, live preview, typed
camera controls, fit/fill/crop framing, fullscreen viewing, and visible
session status. Still capture, video recording, preferences, persistence, and
diagnostics remain in progress.

## Installation
The packaged app supports Python `3.11+`.
After installation, launch it with:

```bash
webcam-micro
```

## What Works Today
- live camera discovery through the active backend
- safe session open, close, and camera switching
- low-latency preview that keeps only the newest frame
- typed camera controls with numeric, boolean, enum, read-only, and action
  widgets
- fit, fill, and microscope-centered crop preview framing
- fullscreen viewing with expanded and collapsed command surfaces
- visible backend, camera, framing, and recording status summaries

## Interface
The main window is organized around the microscope preview.
The app bar and command row keep the primary actions close to the live image,
the preview workspace stays central, the controls surface can be shown or
hidden when needed, and the status bar keeps backend and session state
visible.

Numeric camera controls use guvcview-style affordances.
Each numeric control keeps a slider, min/mid/max labels, and a nearby value
field that clears invalid typed input instead of silently accepting a bad
value.

## Platform Notes
The preview path is built on the FFmpeg-backed backend layer.
On macOS, camera controls can bridge into AVFoundation through
`rubicon-objc` when the active device exposes real controls.
Available controls and source capabilities still depend on the camera and
platform, so the app only surfaces what the active backend can actually use.

## Current Limitations
The current prototype does not yet finish the capture and persistence parts of
the workstation flow.
Still capture, video recording, preferences, defaults, presets, shortcut
editing, and diagnostics are planned slices on top of the Flet shell
foundation that already landed.

## Security, Privacy, and Support
`webcam-micro` is a local desktop utility by default.
The core camera workflow does not depend on cloud services, accounts, or
telemetry, and the app should stay usable without terminal interaction during
normal microscope work.

## License
Document the repository licensing terms here.
