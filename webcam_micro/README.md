# webcam-micro
**Doc ID:** README
**Doc Type:** repo-readme
**Project Version:** 0.0.1
**Last Updated:** 2026-04-04
**DevCovenant Version:** 1.0.1b1

<!-- DEVCOV:BEGIN -->

<!-- DEVCOV:END -->

![webcam-micro preview](https://raw.githubusercontent.com/apostolovbg/webcam-micro/main/webcam_micro/webcam-micro.png)

Cross-platform microscope camera application distributed as a Python package
on PyPI.

## Overview
`webcam-micro` is a preview-first microscope camera application for live
viewing, camera control, still capture, and recording.

The current prototype is on the Qt Widgets migration foundation. Today it
opens a native desktop Qt Widgets workspace with a native menu bar, toolbar,
Qt Multimedia-backed camera discovery, live preview, typed camera controls,
fit/fill/crop framing, a toggleable controls dock, still-image save,
native recording start and stop, session preferences, diagnostics, a compact
fullscreen command surface with expanded and collapsed states, and visible
session status. Output folders, framing choices, selected camera, window
layout, current preset name, and per-camera remembered control values now
persist across launches, and recorded video follows the active capture-
framing choice. User-editable defaults, configurable shortcuts, and named
presets are available, while broader platform validation remains in
progress.

## Installation
The packaged app supports Python `3.11+`.
After installation, launch it with:

```bash
webcam-micro
```

## What Works Today
- live camera discovery through Qt Multimedia device inputs
- safe session open, close, and camera switching
- low-latency preview that keeps only the newest surfaced frame
- typed camera controls with numeric, boolean, enum, read-only, and action
  widgets
- fit, fill, and microscope-centered crop preview framing
- framed still-image save through native PNG or JPEG file dialogs
- native Qt video recording with visible start, stop, and elapsed status
- image and video output folders remembered across launches
- session-level preferences for preview framing, capture framing, output
  folders, editable defaults, keyboard shortcuts, and named presets
- recorded video that follows the current capture-framing rules
- remembered window layout, fullscreen state, selected camera, and
  per-camera control values
- diagnostics dialog that exposes current shell state, a recent-failures log,
  and prototype exit checks
- compact fullscreen command surface with expanded and collapsed states plus
  still, record, and preferences actions
- visible backend, camera, framing, and recording status summaries

## Interface
The main window is organized around the microscope preview.
The native menu bar and toolbar keep the primary actions close to the live
image, the preview workspace stays central, the controls dock can be shown or
hidden when needed, session preferences and diagnostics open through native
desktop dialogs, fullscreen replaces the windowed chrome with a compact
overlay command surface, and the status bar keeps backend and session state
visible in windowed mode.

Numeric camera controls use guvcview-style affordances.
Each numeric control keeps a slider, min/mid/max labels, and a nearby value
field that clears invalid typed input instead of silently accepting a bad
value.

## Platform Notes
The preview and recording path are built on Qt Multimedia camera devices,
capture sessions, and the native Qt recorder.
Still-image save and recorded video both use the current capture-framing
choice instead of saving the raw camera feed.
On macOS, camera controls can bridge into AVFoundation through
`rubicon-objc` when the active device exposes real controls.
Available controls and source capabilities still depend on the camera and
platform, so the app only surfaces what the active backend can actually use.
Recording container support also depends on the platform multimedia stack.

## Current Limitations
The current prototype does not yet finish the broader workstation polish
parts of the flow.
Wider cross-platform recording validation remains planned on top of the
now-working Qt shell baseline.

## Security, Privacy, and Support
`webcam-micro` is a local desktop utility by default.
The core camera workflow does not depend on cloud services, accounts, or
telemetry, and the app should stay usable without terminal interaction during
normal microscope work.

## License
Document the repository licensing terms here.
