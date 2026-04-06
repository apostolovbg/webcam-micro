# Project Specification
**Doc ID:** SPEC
**Doc Type:** specification
**Project Version:** 0.2.0
**Project Stage:** alpha
**Maintenance Stance:** active
**Compatibility Policy:** forward-only
**Versioning Mode:** versioned
**Last Updated:** 2026-04-06
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
8. [Workspace Model](#workspace-model)
9. [Functional Requirements](#functional-requirements)
10. [Non-Functional Requirements](#non-functional-requirements)
11. [Data and State](#data-and-state)
12. [Interfaces and Dependencies](#interfaces-and-dependencies)
13. [Constraints and Assumptions](#constraints-and-assumptions)
14. [Acceptance Criteria](#acceptance-criteria)
15. [Open Questions](#open-questions)
16. [Pointers](#pointers)

## Overview
- Project summary: `webcam-micro` is a cross-platform microscope camera
  application distributed as a Python package on PyPI. It is a GUI-first tool
  for live preview, camera control, still capture, video recording, crop and
  framing control, calibration-oriented microscope work, and persistent
  per-camera defaults.

- Release identity: the version is sourced from `webcam_micro/VERSION`, and
  the shell chrome displays the full legal-owner notice.

- Primary problem: existing webcam viewers either waste preview space, do not
  expose camera controls well, do not support microscope-friendly crop and
  framing behavior, or force terminal-heavy workflows that are awkward for
  repeated microscope use.

- Current scope: the current release line covers all platforms from the
  start, source-run development workflows, PyPI distribution as a proper
  Python package, live preview, fullscreen mode, a dedicated and detachable
  controls surface, configurable crop and framing behavior, still capture,
  video recording, persistent folders, shortcuts, presets, defaults,
  guvcview-style camera-control discovery, and microscope-specific workflow
  support such as calibration and overlays.

- Success signal: the product is clearly working when a user can run it from
  source or install it from PyPI, open a supported camera, see a preview,
  adjust exposed controls through a clear family-based control surface,
  switch between fit/fill/crop preview behavior, capture stills and video
  without terminal interaction, persist defaults per camera, and use the
  application comfortably on all platforms without the status bar turning
  into a wall of text.

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
  supports, including light, flicker, color, and vendor-specific controls
  when the camera exposes them
- a user can frame the circular microscope field sensibly using fit, fill,
  and crop controls
- a user can capture stills and video using the same practical framing they
  see in preview
- a user can work repeatedly with remembered defaults, presets, folders,
  shortcuts, and per-camera control layouts
- a user can keep camera controls docked, detached, or hidden without losing
  the preview-first workspace
- a developer can install the package from PyPI or run it directly from
  source during development on all platforms

The project is worth building because microscope workflows are repetitive and
precision-sensitive. A tool built around microscope reality is materially more
useful than a generic webcam app with accidental microscope applicability.

## Goals
- Provide a microscope camera application that supports live preview, still
  capture, video recording, camera control, crop/framing control, and
  persistent defaults without requiring terminal-based workflows.

- Provide a preview-first user experience in which controls do not
  permanently consume preview space, can dock or detach when needed, and
  fullscreen operation remains practical and safe.

- Provide a capability-driven control surface that feels like a microscope
  workstation rather than a settings dialog with a preview bolted on.

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
- Primary user or actor: a microscope user working with a webcam or
  microscope camera on a desktop machine. This user needs a preview-first
  GUI, sensible microscope framing, easy image and video capture, a dedicated
  controls surface, persistent defaults, and shortcuts that reduce
  repetitive setup.

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
     restores the preferred framing mode, and allows the user to show or hide
     the dedicated controls surface.

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

   - Main path: the preview expands to the full screen, the windowed command
     surfaces transition into a compact fullscreen command surface, the user
     may collapse it to the minimal fullscreen surface, and the application
     preserves a clear path back to windowed mode.

   - Result: the user gets an immersive microscope view while retaining access
     to essential actions and safe fullscreen exit controls.

4. Discover and tune camera controls.
   - Trigger: the user opens the controls surface or the preferences dialog.

   - Main path: the application discovers the active camera/backend
     controls, groups them into stable families, renders each control with
     the correct widget type, lets the user adjust supported values live,
     and stores per-camera or named preset values where appropriate.

   - Result: the user can tune exposure, white balance, flicker, light,
     zoom, and vendor-specific controls without leaving the preview
     workspace.

## Workspace Model
`webcam-micro` should behave like a microscope control workstation, not a
settings dialog with a preview bolted onto it.

- The live preview is the primary visual target.
- The native menu bar provides complete command coverage.
- The top toolbar carries high-frequency actions for camera refresh,
  open and close, preview framing, still capture, recording, fullscreen,
  controls visibility, and preferences.
- The controls surface is dockable and detachable. It may hide, dock, or
  float, but it must preserve preview space when hidden or moved.
- The controls surface should default to a single vertical column. On wide
  layouts it may expand to two columns, but the control order and section
  grouping must remain stable.
- Capture settings such as output folders, formats, and sequence rules
  belong in Preferences or Settings, not in the live camera control pane.
- The status bar must stay compact and structured. It may show runtime
  state, but narrative help, long-form control details, and recovery advice
  belong in the diagnostics surface.
- The overall interaction model should follow the guvcview and quvcview
  concept: capability-driven control discovery, type-aware widgets, and a
  preview-first shell.
- The controls surface should split camera-native controls from software-
  side user controls. The camera section should hold a Resolution
  dropdown of supported camera formats, Exposure as a slider+spinbox
  with an Auto checkbox when the camera exposes auto exposure, Focus as
  a slider+spinbox with an Auto checkbox when the camera exposes auto
  focus, and Light as an on/off checkbox plus a level slider when the
  camera exposes those subcontrols. When Auto is enabled, the paired
  numeric control stays visible, greys out, and snaps to the auto value.
  Any missing Light subcontrol must disable cleanly rather than pretend
  to exist. The user section should hold Backlight compensation,
  Brightness, Contrast, Hue, Saturation, Sharpness, Gamma, and White
  balance as slider+spinbox widgets, with Auto checkboxes on Contrast,
  Hue, and White balance wherever the backend exposes them. Reset to
  defaults should sit at the bottom of the user section.
- When a control exposes both auto and numeric/manual state, the numeric
  widget must stay visible, mirror the current value, snap to the auto
  value when auto is enabled, and become disabled while auto is enabled.
- Camera-native light controls must disable any missing on/off or level
  subcontrol cleanly rather than pretending the control exists.

## Functional Requirements
- The product must be published as a Python package on PyPI and must work on
  all platforms.

- The product must be runnable both as an installed package and directly from
  source during development and testing.

- The main application window must contain a primary command surface, a
  central preview area, a toggleable and detachable dedicated controls
  surface, and a compact dynamic status bar.

- The product must provide a dedicated controls surface that can be shown,
  hidden, docked, or detached from the main workspace so that camera
  controls do not permanently consume preview space.

- The product must provide a standard desktop command structure covering
  File, Edit, View, Camera, Capture, Tools, and Help functional areas.

- The windowed command surfaces must expose the primary working actions,
  including at minimum controls-surface toggle, still capture, record toggle,
  fullscreen/windowed toggle, preferences access, and camera or preset
  related actions.

- The rightmost visible end of the main toolbar must display:
  `© 2026 Black Epsilon Ltd. and Apostol Apostolov`

- The product must provide a dedicated fullscreen mode in which the preview
  occupies the full screen and the windowed command surfaces are replaced by
  a compact fullscreen command surface.

- The fullscreen command surface must support expanded and collapsed states.

- In expanded fullscreen-command state, the surface must include the normal
  fullscreen action set, the fullscreen/windowed toggle, and the
  collapse/expand control.

- In collapsed fullscreen-command state, the surface must reduce to the
  collapse/expand control and the fullscreen/windowed toggle only.

- The fullscreen/windowed toggle and collapse/expand control must remain
  visible in both expanded and collapsed fullscreen-command states.

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

- The product must expose supported source resolutions and frame sizes
  through a dropdown source selector rather than as a freeform field or
  slider.

- The product must expose the controls that the active camera/backend
  actually provides, grouped into stable families and rendered with widgets
  that match the control semantics.

- The product must keep the control-family order stable across layouts and
  backends. When a family is not supported, it must disappear cleanly
  rather than leave a broken placeholder.

- The product must separate camera-native controls from software-side user
  controls within the dedicated controls surface.

- The product must render camera-native Resolution, Exposure, Focus, and
  Light controls with the exact widget composition the device reports:
  Resolution as a dropdown source selector; Exposure and Focus as
  slider+spinbox pairs with Auto checkboxes when exposed; and Light as an
  on/off checkbox plus a level slider when exposed, with any missing
  subcontrol disabled cleanly.

- When a camera reports an Auto checkbox for Exposure or Focus, enabling
  Auto must grey out the paired numeric control and keep it synced to the
  current auto value.

- The product must keep additional backend-specific controls in the Other
  Controls section when the active device exposes them, while preserving
  the camera-controls and user-controls split.

- Numeric controls that expose values must use guvcview-style settings
  components: a slider, min/mid/max labels shown beneath the slider, and an
  adjacent input field with up/down arrows. The input field must update live
  from the slider, and invalid typed values must clear to blank.

- Boolean controls must use checkboxes.

- Enumerated controls must use dropdowns or combo boxes.

- Read-only controls must use labels or disabled value fields.

- Action controls must use push buttons or equivalent one-shot actions.

- The product must tolerate cameras that expose only a subset of common
  controls and must not fail simply because some expected controls are absent.

- The product must support common microscope-relevant controls where
  exposed, including backlight compensation, power line frequency, AC
  flicker compensation, white balance automatic control, white balance
  temperature, exposure automatic and manual controls, focus automatic and
  manual controls, zoom controls, color profile controls, and vendor-
  specific extension controls, plus shell-managed brightness, contrast,
  saturation, hue, gamma, and sharpness adjustments.

- Camera-native controls must include light controls with on/off and level
  subcontrols when exposed, and unsupported subcontrols must disable cleanly
  rather than present fake values.

- The user-controls section must always include shell-managed brightness,
  contrast, hue, saturation, sharpness, and gamma rows with
  slider+spinbox widgets, must keep backlight compensation and white
  balance where the active camera exposes them, and must provide Auto
  toggles on contrast and hue in the shell and on white balance wherever
  the backend exposes it.

- The user-controls section must place a Reset to Defaults button at the
  bottom.

- The user-controls section must end with a reset-to-defaults button that
  restores built-in or remembered values for the visible controls.

- If a camera exposes a lamp, illumination, or activity LED control, the
  product must surface it and allow it to be turned off when the device
  supports that state.

- The product must keep live capture settings separate from camera controls
  and place image and video output configuration in Preferences or Settings,
  not in the live control pane.

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
  actions including still capture, record toggle, controls-surface toggle,
  fullscreen/windowed toggle, fullscreen-surface collapse/expand,
  preferences access, and framing-mode changes.

- Shortcut conflicts must be detected and prevented.

- The dynamic status bar must stay compact and structured. It must reflect
  runtime state, including the active camera, active backend, source mode,
  framing mode, current preset, output destinations, recording state,
  elapsed recording time, and warnings or recoverable errors. It must not
  become a narrative help panel or a wall of text.

- The application must persist user preferences across launches, including at
  minimum selected camera where appropriate, source mode preferences, preview
  framing mode, capture framing mode, image folder, video folder, shortcuts,
  main-window geometry, controls-surface visibility, controls-surface dock
  or float state,
  fullscreen-surface state,
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
- Important entities: active camera identity, camera capability set, control
  family ordering, source mode, preview framing mode, capture framing mode,
  per-camera settings, built-in defaults, user presets, image outputs,
  video outputs, keyboard shortcut map, window geometry,
  controls-surface visibility, controls-surface dock or float state, and
  fullscreen-surface state.

- Important state transitions: the application moves between no-camera and
  active-camera states, windowed and fullscreen states, docked and detached
  control-surface states, expanded and collapsed fullscreen-command states,
  idle and recording states, and unsaved/runtime state versus persisted
  preference state.

- Persistence rules: per-camera settings, output folders, shortcuts, framing
  defaults, selected modes, controls-surface visibility and dock state, and
  window/layout state must be stored persistently. Live frame buffers and
  transient backend session state are ephemeral.

- Audit or history needs: the product should preserve enough diagnostics and
  runtime reporting for a user or maintainer to understand which camera,
  backend, source mode, framing mode, control family, and preset were active
  when a warning or failure occurred.

## Interfaces and Dependencies
- External interfaces: desktop GUI, application command surfaces, keyboard
  shortcuts, image and video output files, platform camera backends, the
  PyPI package distribution, and the application entrypoint exposed as
  `webcam-micro`.

- Internal interfaces: UI layer, camera-discovery layer, camera-control
  abstraction, preview/capture pipeline, persistence layer, diagnostics
  surface, calibration or overlay logic, and platform-specific backend
  adapters that translate native camera APIs and vendor-specific controls
  into the stable control families above.

- Dependencies: Python runtime, a cross-platform Python GUI toolkit, platform
  camera APIs or compatible backend integrations, image/video encoding support,
  and platform integration mechanisms appropriate to the active platform. The
  current GUI shell baseline is `PySide6` with Qt Widgets, and the current
  device-backend target is Qt Multimedia-backed camera discovery and
  low-latency preview behind a thinner backend adapter layer that keeps
  microscope-specific policy and native control bridges without rebuilding a
  parallel preview stack.

- Compatibility expectations: the PyPI package is intended to work on all
  platforms; source-run development must be supported; platform backend
  differences must not leak upward into broken user-facing contracts. The
  user-facing control model must remain stable even when the underlying
  backend exposes different native control shapes.

## Constraints and Assumptions
- Constraint: camera backends differ materially in control exposure and device
  behavior across platforms, so the product cannot assume identical control
  surfaces across all devices and platforms.

- Constraint: on macOS, camera-control ownership must prefer the backend
  that can actually apply the write. Qt Multimedia should own exposure,
  ISO, backlight, focus, and white balance when its setters are
  available, and AVFoundation must fail closed on unsupported
  custom-exposure paths instead of calling them.

- Assumption: the active camera/backend will usually expose at least a
  meaningful subset of controls and source modes sufficient for microscope
  preview and capture, but the exact set may vary widely by device. Some
  cameras expose light, LED, or flicker controls and some do not; the UI
  must surface only what the backend reports.

- Explicit tradeoff: the product is optimized for microscope-friendly preview,
  framing, control visibility, and repeatable local workflows rather than for
  becoming a generic camera ecosystem that promises identical hardware
  behavior everywhere.

## Acceptance Criteria
- A developer can clone the repository, install development dependencies,
  install the package from PyPI or run the application directly from source
  on any platform, open a camera session, and use the main preview workflow
  without needing a terminal for runtime interaction.

- A user can open the controls surface, adjust the controls that the active
  camera exposes, dock or detach it, switch between fit/fill/crop framing
  behavior, capture a still image, start and stop a video recording, and
  find the outputs in the configured folders.

- A user can choose a supported source resolution from a dropdown, keep
  auto-enabled exposure or focus controls gray while the live value stays
  visible and tracks the auto value, use the split camera-controls and
  user-controls layout, adjust light on/off and level controls when
  exposed, and reset visible user controls to their defaults from the
  bottom-most button.

- A user can tune exposure, white balance, backlight compensation, flicker
  compensation, zoom, and any activity LED or vendor-specific control that
  the active camera exposes.

- A user can adjust backlight compensation and white balance through
  slider+spinbox widgets when the camera exposes them, and can adjust
  shell-managed brightness, contrast, hue, saturation, sharpness, and
  gamma through slider+spinbox widgets, with Auto toggles on contrast and
  hue in the shell and on white balance when the camera exposes it.

- A user on any platform can enter fullscreen mode, use the fullscreen
  command surface in expanded and collapsed states, exit fullscreen safely,
  relaunch the application later, and observe persisted defaults, folders,
  presets, shortcuts, and controls-surface layout consistent with the saved
  configuration.

- The status bar stays compact while detailed runtime history remains in the
  diagnostics surface.

## Open Questions
- What should the exact default keyboard-shortcut map be for first release,
  including still capture, record toggle, framing-mode change, controls-
  surface detach or restore, and fullscreen-surface collapse or expand
  actions?

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
