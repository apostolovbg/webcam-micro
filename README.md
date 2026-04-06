# webcam-micro
**Doc ID:** README
**Doc Type:** repo-readme
**Project Version:** 0.2.0
**Last Updated:** 2026-04-06
**DevCovenant Version:** 1.0.1b1

<!-- DEVCOV:BEGIN -->

<!-- DEVCOV:END -->

Cross-platform microscope camera application distributed as a Python package
on PyPI.

![webcam-micro preview](https://raw.githubusercontent.com/apostolovbg/webcam-micro/main/webcam_micro/webcam-micro.png)

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

The current alpha release runs on the Qt Widgets shell baseline. Today it
opens a native desktop workspace with a menu bar, toolbar, central preview
area, toggleable controls dock, quiet still-image save to the configured
folder, a tighter preview refresh cadence, native recording, session
preferences, diagnostics, and a compact fullscreen command surface with
expanded and collapsed states. Preview framing, capture framing, camera
selection, window layout, current preset name, and per-camera control
values persist across launches. Image and video output folders live in
Preferences, and the compact status bar stays structured. User-editable
defaults, keyboard shortcuts, and named presets are available, while
broader platform validation is covered by automated tests and Linux smoke
checks here.

## Alpha Status
`webcam-micro` is now the official alpha release.
The release version is sourced from `webcam_micro/VERSION`, and the shell
chrome carries the full legal-owner notice.
The Qt Widgets baseline is usable for live preview, camera control, still
capture, recording, presets, and diagnostics. The remaining beta-prep work
is now deferred until after beta publication, so the beta plan is
complete for the current release path.

## What Works Today
- Launch and entrypoint: the application starts from the `webcam-micro`
  command, bootstraps a stable per-user runtime interpreter on every
  supported OS, and can also run from source during development.
- Windowed workspace: the main shell keeps the preview central while the
  menu bar, toolbar, and status bar expose the primary microscope
  actions, and the controls dock can dock, float, hide, and restore
  without taking the preview off center. A visible Restore Dock action
  keeps detached controls easy to reattach.
- Fullscreen workspace: the preview expands to the full screen and the
  command surface collapses into a compact overlay with safe exit paths.
- Preview and framing: live preview supports fit, fill, and centered crop
  modes, and a tighter refresh cadence keeps the newest frame close to live
  motion when the preview resizes.
- Camera controls: the dock splits native controls into Camera Controls
  and User Controls. Camera Controls expose Resolution as a dropdown,
  Exposure and Focus as slider-plus-spinbox controls with Auto
  checkboxes when the camera reports them, and Light as an on/off
  checkbox plus a level slider when exposed. When Auto is enabled, the
  paired numeric control stays visible, greys out, and tracks the auto
  value. User Controls expose Backlight compensation, Brightness,
  Contrast, Hue, Saturation, Sharpness, Gamma, and White balance, with
  Auto checkboxes on Contrast, Hue, and White balance when the backend
  exposes them, and a Reset to Defaults button at the bottom.
- The active backend still exposes numeric, boolean, enum, read-only,
  and action controls when the device supports them. Qt Multimedia now
  surfaces backlight compensation, manual exposure time and ISO, focus
  auto and distance, white balance automatic and temperature, flash or
  torch, and source-format details when the device reports them. On
  macOS, including Intel Macs, AVFoundation adds exposure mode, manual
  exposure time and ISO, backlight compensation when the camera reports
  a supported bias range, white balance temperature when it can lock
  white balance, focus, flash, torch, smooth autofocus, automatic video
  HDR, and zoom when the camera reports them. On Linux, V4L2 adds power
  line frequency, brightness, contrast, saturation, hue, gamma, gain,
  sharpness, lamp, illumination, activity LED, and vendor-specific
  extension controls when the camera reports them.
- Capture and recording: still images save quietly to the configured folder
  with the current capture framing, and recordings use native controls with
  platform-supported containers.
- Preferences, defaults, and presets: framing, keyboard shortcuts,
  defaults, and named presets are stored with the workspace, while image
  and video output folders live in Preferences.
- Diagnostics and status: the shell reports runtime state, recent failures,
  and prototype exit checks in a visible diagnostics dialog and status bar.
- Platform notes: Qt Multimedia owns the camera and recording stack, while
  platform and device differences still shape the available controls. On
  macOS, exposure, focus, backlight compensation, and white balance
  updates now wait for AVFoundation completion on the caller thread
  before releasing configuration locks, so slider-driven control changes
  stay stable and the shared error-reporting layer keeps launcher,
  runtime bootstrap, and camera failures as typed notices and
  diagnostics instead of raw tracebacks.

## Installation
The packaged app supports Python `3.11+`.
Install it from PyPI or a built wheel, then launch it with:

```bash
webcam-micro
```

## Launch
The application starts in a preview-first Qt Widgets window.
The `webcam_micro.launcher` module uses `webcam_micro.runtime_bootstrap` to
create or reuse a stable per-user runtime interpreter on Windows, macOS,
and Linux before the Qt shell starts, so the first launch sets up the
Python identity that will own later camera access on macOS. The runtime
bridge keeps the package imports visible in that interpreter so Qt still
loads from the installed package set. On macOS, the camera permission
prompt runs through a repo-owned adapter so the same code path stays
import-safe on Windows and Linux.
The command bar and native menu bar provide access to the core camera,
capture, framing, preference, and diagnostics actions without requiring a
terminal once the app is running.
On macOS, the runtime interpreter requests camera permission the first time
a camera opens through that adapter; if it was denied before, reset the
Camera privacy setting and relaunch.

## Windowed Workspace
The main window keeps the microscope preview central.
The native menu bar carries File for Exit, Edit for copy status, View for
controls and framing, Camera for camera refresh, open, and close, Capture
for still and recording actions, Tools for preferences and diagnostics, and
Help for About. The toolbar keeps the main working actions close to the live
image, including controls, camera refresh, camera open and close, framing,
still capture, recording, fullscreen, and preferences. The right edge of
the toolbar displays `© 2026 Black Epsilon Ltd. and Apostol Apostolov`.

The controls dock can be shown, hidden, floated, or restored so camera
controls do not consume preview space permanently. It keeps the preview
central even when detached, defaults to one vertical column, and widens to
two columns on roomier layouts while preserving the section order.
Numeric controls use guvcview-style affordances: a slider, min/mid/max
labels, and an adjacent field with step buttons. Boolean, enumerated,
read-only, and action controls appear when the backend exposes them.

## Fullscreen Workspace
Fullscreen replaces the windowed chrome with a compact command surface.
Expanded fullscreen shows the core microscope actions plus collapse and safe
windowed exit. Collapsed fullscreen keeps only collapse/expand and the
fullscreen/windowed toggle visible. Escape returns to windowed mode.

## Preview and Framing
Preview framing supports fit, fill, and centered crop modes.
The live preview rerenders from the newest cached frame when the window or
preview area changes size, and the tighter poll cadence keeps the visible
motion closer to the live feed. Capture framing is separate from preview
framing so stills and videos can follow their own output rules without
changing the live microscope view.

## Camera Controls
The app exposes the real control surface reported by the active camera and
backend. The dock splits those controls into Camera Controls and User
Controls. Camera Controls expose Resolution as a dropdown, Exposure and
Focus as slider-plus-spinbox widgets with Auto checkboxes when the camera
reports them, and Light as an on/off checkbox plus a level slider when
available. When Auto is enabled, the paired numeric control stays visible,
greys out, and tracks the auto value. User Controls expose Backlight
compensation, Brightness, Contrast, Hue, Saturation, Sharpness, Gamma, and
White balance, with Auto checkboxes on Contrast, Hue, and White balance
when the backend exposes them, and a Reset to Defaults button at the
bottom.
Qt Multimedia covers the common exposure, focus, white balance, flash,
torch, zoom, and source-format controls across supported platforms, while
Linux V4L2 adds power line frequency, image-quality controls, lamp,
illumination, activity LED, and vendor-specific extensions when the device
reports them. Supported controls include numeric, boolean, enumerated,
read-only, and action widgets. The app tolerates partial control sets and
does not fail just because a camera lacks an expected control.
On macOS, backlight compensation only appears when AVFoundation reports a
supported exposure-bias range, white balance temperature only appears
when the device can lock white balance, and the app skips saved values
for unsupported devices instead of reopening the camera with a crash.

## Capture and Recording
Still images save quietly to the configured image folder as PNG or JPEG
output. Recording starts and stops natively in the Qt shell, shows elapsed
status while it runs, and only offers containers that the current Qt
Multimedia runtime supports. The `webcam_micro.camera` recording helper
rejects unsupported suffixes before recording starts. Recorded video uses
the active capture-framing choice and remembers the output folder across
launches.

## Preferences, Defaults, and Presets
Preferences store preview framing, capture framing, output folders, editable
defaults, keyboard shortcuts, and named presets.
The app remembers the current preset name, restores per-camera control
values when available, and keeps editable control defaults grouped by the
same section names inside Preferences. It also lets users save or apply
named presets from the same preferences dialog.

## Diagnostics and Status
The diagnostics dialog shows a runtime report, a recent-failures log, and
prototype exit checks. The status bar summarizes backend, camera, source
mode, preview framing, capture framing, controls state, preset name,
recording state, and the current status notice.

## Platform Notes
Qt Multimedia owns camera discovery, preview, recording, and the common
control surface. On Linux, V4L2 contributes extra control discovery for
device-specific and vendor-specific settings when available. Actual
controls and container support vary by camera, backend, and platform. The
app only surfaces controls the backend can actually use, and the recording
path filters the save dialog to supported containers.

## Current Limitations
Some camera controls and output formats remain backend-dependent.

## Packaging and Distribution
`webcam-micro` is shipped as a Python package on PyPI.
The package-facing README lives at `webcam_micro/README.md`, where the
repo-only notes are stripped out before packaging. The `webcam_micro.launcher`
entrypoint uses `webcam_micro.runtime_bootstrap` to create or reuse the
per-user runtime interpreter on every supported OS before handing off to
the GUI app, and the source package remains runnable during development.

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
