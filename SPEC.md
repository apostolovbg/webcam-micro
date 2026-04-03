# Project Specification
**Doc ID:** SPEC
**Doc Type:** specification
**Project Version:** Unversioned
**Project Stage:** prototype
**Maintenance Stance:** active
**Compatibility Policy:** unspecified
**Versioning Mode:** unversioned
**Last Updated:** 2026-04-03
**DevCovenant Version:** 1.0.1b1

<!-- DEVCOV:BEGIN -->
This opening section is managed by DevCovenant.
Use `SPEC.md` only for durable project rules below this block.
<!-- DEVCOV:END -->

Use this document for durable product requirements and stable project
decisions.
Keep active execution work in `PLAN.md`, change history in `CHANGELOG.md`,
and required workflow law in `AGENTS.md`.

## Table of Contents
1. [Overview](#overview)
2. [Workflow](#workflow)
3. [Project Intent](#project-intent)
4. [Goals](#goals)
5. [Non-Goals](#non-goals)
6. [Users and Actors](#users-and-actors)
7. [Core Workflows](#core-workflows)
8. [Functional Requirements](#functional-requirements)
9. [Non-Functional Requirements](#non-functional-requirements)
10. [Data and State](#data-and-state)
11. [Interfaces and Dependencies](#interfaces-and-dependencies)
12. [Constraints and Assumptions](#constraints-and-assumptions)
13. [Acceptance Criteria](#acceptance-criteria)
14. [Open Questions](#open-questions)
15. [Pointers](#pointers)

## Overview
- Project summary: `webcam-micro` is a cross-platform microscope camera
  application distributed as a Python package on PyPI. It is a GUI-first tool
  for live preview, camera control, still capture, video recording, crop and
  framing control, calibration-oriented microscope work, and persistent
  per-camera defaults.

- Primary problem: existing webcam viewers either waste preview space, do not
  expose camera controls well, do not support microscope-friendly crop and
  framing behavior, or force terminal-heavy workflows that are awkward for
  repeated microscope use.

- Current scope: the current release line covers all platforms from the
  start, source-run development workflows, PyPI distribution as a proper
  Python package, live preview, fullscreen mode, a separate controls window,
  configurable crop and framing behavior, still capture, video recording,
  persistent folders, shortcuts, presets, defaults, and microscope-specific
  workflow support such as calibration and overlays.

- Success signal: the product is clearly working when a user can run it from
  source or install it from PyPI, open a supported camera, see a preview,
  adjust exposed controls, switch between fit/fill/crop preview behavior,
  capture stills and video without terminal interaction, persist defaults per
  camera, and use the application comfortably on all platforms.

## Workflow
- Keep durable product requirements here.

- Keep active execution work in `PLAN.md`.

- Update this spec when stable product rules change.

- Update operational docs in the same slice when runtime behavior changes.

- Treat this spec as durable product guidance, not as a temporary audit
  notebook or release checklist.

## Project Intent
`webcam-micro` exists to turn a generic webcam or microscope camera into a
usable microscope workstation application rather than a generic webcam viewer.

It should make the following possible:

- a microscope user can prioritize preview area instead of fighting UI chrome
- a user can expose and control the settings that the active camera actually
  supports
- a user can frame the circular microscope field sensibly using fit, fill,
  and crop controls
- a user can capture stills and video using the same practical framing they
  see in preview
- a user can work repeatedly with remembered defaults, presets, folders, and
  shortcuts
- a developer can install the package from PyPI or run it directly from
  source during development on all platforms

The project is worth building because microscope workflows are repetitive and
precision-sensitive. A tool built around microscope reality is materially more
useful than a generic webcam app with accidental microscope applicability.

## Goals
- Provide a microscope camera application that supports live preview, still
  capture, video recording, camera control, crop/framing control, and
  persistent defaults without requiring terminal-based workflows.

- Provide a preview-first user experience in which controls do not permanently
  consume preview space and fullscreen operation remains practical and safe.

- Provide a healthy cross-platform release line in which the application is
  published on PyPI, works on all platforms, runs from source during
  development, and contains backend/platform differences behind stable product
  behavior.

## Non-Goals
- The project is not trying to be a generic all-purpose photo editor, video
  editor, or image-processing suite.

- The project is not trying to support arbitrary non-desktop or cloud camera
  workflows, account-based services, or remote SaaS dependencies for core
  local operation.

- The project is not promising that every camera on every platform will expose
  identical controls or that unsupported backend/device features will be
  emulated as native camera capabilities.

## Users and Actors
- Primary user or actor: a microscope user working with a webcam or microscope
  camera on a desktop machine. This user needs a preview-first GUI, sensible
  microscope framing, easy image and video capture, a separate controls
  window, persistent defaults, and shortcuts that reduce repetitive setup.

- Secondary user or actor: a power user or laboratory-style operator who
  switches between cameras, source modes, presets, and capture workflows. This
  user needs device discovery, mode selection, calibration-aware features,
  predictable output folders, diagnostics, and trustworthy persistence.

- Operational actor: a developer, maintainer, or tester running the program
  from source or installing and publishing it as a Python package. This actor
  needs a stable application entrypoint, a clear source-run workflow, PyPI
  distribution readiness, modular backend boundaries, and diagnostics that
  expose runtime state and backend failures.

## Core Workflows
1. Open camera session and preview microscope image.
   - Trigger: the user launches the application and selects or confirms an
     active camera.

   - Main path: the application discovers cameras, opens the selected device,
     applies saved or built-in defaults where valid, opens the live preview,
     restores the preferred framing mode, and allows the user to open the
     separate controls window.

   - Result: the user gets a usable live microscope preview with the expected
     framing and accessible camera controls.

2. Capture still image or video using the current microscope framing.
   - Trigger: the user presses a toolbar button, menu action, or configured
     keyboard shortcut for image capture or recording.

   - Main path: the application uses the configured capture settings, output
     folders, and framing behavior, records visible status, and finalizes the
     output file into the configured destination.

   - Result: the user gets a saved image or video that follows the configured
     framing/output rules and can continue working without restarting the
     session.

3. Work in fullscreen microscope mode.
   - Trigger: the user enters fullscreen mode from the toolbar, menu, or
     shortcut.

   - Main path: the preview expands to the full screen, the normal toolbar
     transitions into a detached movable toolbar, the user may collapse it to
     the minimal fullscreen control surface, and the application preserves a
     clear path back to windowed mode.

   - Result: the user gets an immersive microscope view while retaining access
     to essential actions and safe fullscreen exit controls.

## Functional Requirements
- The product must be published as a Python package on PyPI and must work on
  all platforms.

- The product must be runnable both as an installed package and directly from
  source during development and testing.

- The main application window must contain a menu bar, a top toolbar, a
  central preview area, and a dynamic status bar at the bottom.

- The product must provide a separate controls window that can be opened and
  closed independently of the main window so that camera controls do not
  permanently consume preview space.

- The product must provide a standard desktop menu structure covering File,
  Edit, View, Camera, Capture, Tools, and Help functional areas.

- The windowed main toolbar must expose the primary working actions, including
  at minimum controls-window toggle, still capture, record toggle,
  fullscreen/windowed toggle, preferences access, and camera or preset related
  actions.

- The rightmost visible end of the main toolbar must display:
  `© Apostol Apostolov`

- The product must provide a dedicated fullscreen mode in which the preview
  occupies the full screen and the normal toolbar is replaced by a detached
  movable toolbar with a handle.

- The detached fullscreen toolbar must support expanded and collapsed states.

- In expanded fullscreen-toolbar state, the toolbar must include the normal
  fullscreen action set, the fullscreen/windowed toggle, the collapse/expand
  control, and the toolbar handle.

- In collapsed fullscreen-toolbar state, the toolbar must reduce to the
  collapse/expand control and the fullscreen/windowed toggle only.

- The fullscreen/windowed toggle and collapse/expand control must remain
  visible in both expanded and collapsed fullscreen-toolbar states.

- The product must provide live preview layout modes appropriate for
  microscope work, including fit-to-screen, fill-screen, and crop-based
  framing behavior.

- The product must allow crop, framing, and preview layout to be changed by
  the user and should apply these changes live whenever backend capabilities
  permit.

- The product must allow defaults for preview framing and capture framing to
  be configured and persisted.

- The product must treat source mode selection and output framing behavior as
  distinct concepts.

- The product must enumerate the cameras available through the active platform
  backend and allow camera selection, refresh, and inspection of active device
  identity information.

- The product must enumerate the source capabilities exposed by the active
  camera/backend, including where available pixel formats, frame sizes, and
  frame rates.

- The product must not present unsupported synthetic source modes as though
  they were native device modes.

- The product must expose the controls that the active camera/backend actually
  provides, including numeric, boolean, enumerated, read-only, and meaningful
  action controls.

- Numeric controls that expose values must use guvcview-style settings
  components: a slider, min/mid/max labels shown beneath the slider, and an
  adjacent input field with up/down arrows. The input field must update live
  from the slider, and invalid typed values must clear to blank.

- The product must tolerate cameras that expose only a subset of common
  controls and must not fail simply because some expected controls are absent.

- The product must support common microscope-relevant controls where exposed,
  including brightness, contrast, saturation, hue, gamma, gain, sharpness,
  backlight compensation, power line frequency, white balance automatic
  control, white balance temperature, exposure automatic and manual controls,
  focus automatic and manual controls, and zoom controls.

- The built-in default preferred microscope values must be:
  - Brightness = 0
  - Contrast = 20
  - Saturation = 128
  - Hue = 0
  - White Balance Automatic = off
  - Gamma = 72
  - Gain = 20
  - Power Line Frequency = 50 Hz
  - White Balance Temperature = 2800
  - Sharpness = 0
  - Backlight Compensation = 0

- Built-in defaults must only be applied where the active camera exposes the
  control, the requested value is valid, and any prerequisite auto/manual
  dependency order has been satisfied.

- If a default or preset value cannot be applied because the control is
  missing or incompatible, the application must fail softly and continue
  operating.

- The product must support built-in defaults, user-editable defaults,
  per-camera remembered settings, and named user presets.

- Presets and defaults must degrade gracefully when the active camera does not
  expose all controls referenced by the preset.

- The product must support still image capture from toolbar, menu, and
  keyboard shortcut actions.

- Still image capture must support timestamp-based file naming by default,
  saving to the configured image folder, and capture framing behavior
  consistent with configured output rules.

- The product must support at least JPEG and PNG still-image output formats.

- The product must support video recording from toolbar, menu, and keyboard
  shortcut actions.

- Video recording must support explicit start and stop control, visible
  recording state, visible elapsed time, saving to the configured video
  folder, and clean output finalization on stop.

- The product must provide separate user-configurable output folders for still
  images and video recordings.

- The default image folder must be `~/microscope/images`.

- The default video folder must be `~/microscope/videos`.

- The product must create missing output folders automatically when needed and
  must persist user-selected output folders across launches.

- The product must provide user-configurable keyboard shortcuts for primary
  actions including still capture, record toggle, controls-window toggle,
  fullscreen/windowed toggle, fullscreen-toolbar collapse/expand, preferences
  access, and framing-mode changes.

- Shortcut conflicts must be detected and prevented.

- The dynamic status bar must reflect runtime state, including the active
  camera, active backend, source mode, framing mode, current preset, output
  destinations, recording state, elapsed recording time, and warnings or
  recoverable errors.

- The application must persist user preferences across launches, including at
  minimum selected camera where appropriate, source mode preferences, preview
  framing mode, capture framing mode, image folder, video folder, shortcuts,
  main-window geometry, controls-window geometry, fullscreen-toolbar state,
  and per-camera defaults or presets.

- The product must provide a user-accessible diagnostics surface or log view
  that exposes runtime state, active backend, active camera identity, and
  non-fatal failures such as control-application errors or capture failures.

- Microscope-specific tooling is in scope and the product must preserve room
  for calibration profiles, measurement-related configuration, and scale or
  framing overlays as part of the durable product contract.

## Non-Functional Requirements
- Performance: the application must feel responsive for normal desktop
  microscope use, keep preview interaction practical during active sessions,
  and avoid unnecessary mode-switching latency during framing, capture, and
  fullscreen transitions.

- Reliability: unsupported controls, missing controls, invalid values, backend
  differences, and capture failures must be handled gracefully. Failure to
  apply one control must not prevent the rest of the session from working
  unless capture itself is impossible.

- Security: the product is a local desktop utility by default and must not
  require cloud services, accounts, or telemetry for its core local camera
  features.

- Maintainability: the codebase must separate UI, camera-backend abstraction,
  capture and recording pipeline, settings and persistence, and
  platform-specific integrations so that all-platform support remains
  maintainable.

- Usability: the application must remain GUI-first, preview-first, and quiet
  in normal operation, must avoid requiring terminal interaction, and must
  preserve a clear and safe user path into and out of fullscreen mode.

## Data and State
- Important entities: active camera identity, camera capability set, source
  mode, preview framing mode, capture framing mode, per-camera settings,
  built-in defaults, user presets, image outputs, video outputs, keyboard
  shortcut map, window geometry, controls-window state, and fullscreen-toolbar
  state.

- Important state transitions: the application moves between no-camera and
  active-camera states, windowed and fullscreen states, expanded and collapsed
  fullscreen-toolbar states, idle and recording states, and unsaved/runtime
  state versus persisted preference state.

- Persistence rules: per-camera settings, output folders, shortcuts, framing
  defaults, selected modes, and window/layout state must be stored
  persistently. Live frame buffers and transient backend session state are
  ephemeral.

- Audit or history needs: the product should preserve enough diagnostics and
  runtime reporting for a user or maintainer to understand which camera,
  backend, source mode, framing mode, and preset were active when a warning or
  failure occurred.

## Interfaces and Dependencies
- External interfaces: desktop GUI, application menus, toolbar actions,
  keyboard shortcuts, image and video output files, platform camera backends,
  the PyPI package distribution, and the application entrypoint exposed as
  `webcam-micro`.

- Internal interfaces: UI layer, camera-discovery layer, camera-control
  abstraction, preview/capture pipeline, persistence layer, diagnostics
  surface, calibration or overlay logic, and platform-specific backend
  adapters.

- Dependencies: Python runtime, a cross-platform Python GUI toolkit, platform
  camera APIs or compatible backend integrations, image/video encoding support,
  and platform integration mechanisms appropriate to the active platform. The
  initial GUI shell baseline is `ttkbootstrap` on top of Tk, and the first
  concrete device-backend target is OpenCV-backed discovery and preview
  behind a backend adapter layer.

- Compatibility expectations: the PyPI package is intended to work on all
  platforms; source-run development must be supported; platform backend
  differences must not leak upward into broken user-facing contracts.

## Constraints and Assumptions
- Constraint: camera backends differ materially in control exposure and device
  behavior across platforms, so the product cannot assume identical control
  surfaces across all devices and platforms.

- Assumption: the active camera/backend will usually expose at least a
  meaningful subset of controls and source modes sufficient for microscope
  preview and capture, but the exact set may vary widely by device.

- Explicit tradeoff: the product is optimized for microscope-friendly preview,
  framing, control visibility, and repeatable local workflows rather than for
  becoming a generic camera ecosystem that promises identical hardware
  behavior everywhere.

## Acceptance Criteria
- A developer can clone the repository, install development dependencies,
  install the package from PyPI or run the application directly from source
  on any platform, open a camera session, and use the main preview workflow
  without needing a terminal for runtime interaction.

- A user can open the controls window, adjust the controls that the active
  camera exposes, switch between fit/fill/crop framing behavior, capture a
  still image, start and stop a video recording, and find the outputs in the
  configured folders.

- A user on any platform can enter fullscreen mode, use the detached toolbar
  in expanded and collapsed states, exit fullscreen safely, relaunch the
  application later, and observe persisted defaults, folders, presets, and
  shortcut behavior consistent with the saved configuration.

## Open Questions
- What should the exact default keyboard-shortcut map be for first release,
  including still capture, record toggle, framing-mode change, and
  fullscreen-toolbar collapse/expand actions?

- Should the first release support optional uncropped capture alongside the
  default “capture follows configured preview/output framing” behavior, or
  should that remain a later refinement within the same product scope?

## Pointers
Add pointers to the docs that hold operational detail, architecture notes,
API descriptions, calibration behavior, packaging details, and supporting
decision records.

Recommended supporting documents include:

- `PLAN.md` for active work slices and delivery sequencing
- `AGENTS.md` for workflow law and required development behavior
- architecture documentation for backend design and platform abstraction
- user documentation for installation, development setup, and usage
- operational documentation for packaging and release workflows
- calibration or microscope-workflow documentation for measurement-related
  features
