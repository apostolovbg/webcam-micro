# Project Specification
**Doc ID:** SPEC
**Doc Type:** specification
**Project Version:** 0.2.0
**Project Stage:** alpha
**Maintenance Stance:** active
**Compatibility Policy:** forward-only
**Versioning Mode:** versioned
**Last Updated:** 2026-04-07
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
- `webcam-micro` is a cross-platform microscope camera app on PyPI for
  live preview, camera control, still capture, video recording, crop and
  framing, calibration work, and per-camera defaults.

- Release identity comes from `webcam_micro/VERSION`, and the shell chrome
  carries the full legal-owner notice.

- Existing viewers waste preview space, hide controls, or force terminal
  workflows; this project fixes that for microscope use.

- Current scope: all platforms, source-run development, PyPI packaging,
  live preview, fullscreen mode, detachable controls, configurable
  crop/framing, still capture, video recording, persistent folders,
  shortcuts, presets, defaults, a single authoritative device-control
  layer, and microscope-specific workflows such as calibration and
  overlays.

- Success means a user can run from source or PyPI, open a supported
  camera, see preview, adjust exposed controls through one stable family-
  based control surface, switch fit/fill/crop, capture stills and video
  without terminal interaction, and keep per-camera defaults while the UI
  stays compact.

## Workflow
- Keep durable product requirements here.
- Keep active execution work in `PLAN.md`.
- Update this spec when stable product rules change.
- Update operational docs in the same slice when runtime behavior changes.
- Treat this spec as durable guidance, not as an audit notebook or release
  checklist.

## Project Intent
`webcam-micro` turns a webcam or microscope camera into a microscope
workstation rather than a generic viewer.

It should let a microscope user favor preview area, tune only the settings
the active camera actually supports, frame the circular field with fit,
fill, and crop, capture stills and video with the same framing they see in
preview, keep remembered defaults and presets, and dock or detach controls
without losing the preview-first workspace. A developer should be able to
install from PyPI or run from source on all platforms.

The project matters because microscope work is repetitive and precision-
sensitive, and a tool built around microscope reality is more useful than a
generic webcam app with accidental microscope applicability.

## Goals
- Provide live preview, still capture, video recording, camera control,
  crop/framing control, and persistent defaults without terminal workflows.

- Keep the experience preview-first, with controls that can dock or detach
  without permanently consuming preview space and fullscreen that remains
  practical and safe.

- Provide a capability-driven control surface that feels like a microscope
  workstation rather than a settings dialog with a preview attached.

- Provide a cross-platform release line on PyPI that also runs from source
  and hides backend differences behind stable product behavior.

## Non-Goals
- The project is not a general photo editor, video editor, or image-
  processing suite.

- It does not target non-desktop cameras, cloud services, or account-based
  dependencies for core local operation.

- It does not promise identical controls on every camera or emulate
  unsupported backend features as native camera capabilities.

## Users and Actors
- Primary user: a microscope user on a desktop machine who needs preview-
  first GUI, sensible framing, easy capture, a dedicated controls surface,
  persistent defaults, and shortcuts that reduce repetitive setup.

- Secondary user: a power user or lab-style operator who switches between
  cameras, source modes, presets, and capture workflows, and needs device
  discovery, calibration-aware features, predictable folders, diagnostics,
  and trustworthy persistence.

- Operational actor: a developer, maintainer, or tester running from source
  or installing the package. This actor needs a stable entrypoint, a clear
  source-run workflow, PyPI readiness, modular backend boundaries, and
  diagnostics that expose runtime state and backend failures.

## Core Workflows
1. Open a camera session and preview the microscope image.
   - Trigger: the user launches the application and selects or confirms a
     camera.
   - Main path: the application discovers cameras, opens the selected one,
     applies saved or built-in defaults where valid, opens live preview,
     restores the preferred framing, and lets the user show or hide the
     controls surface.
   - Result: the user gets a usable live microscope preview with the
     expected framing and accessible controls.

2. Capture stills or video with the current microscope framing.
   - Trigger: the user presses a toolbar button, menu action, or shortcut.
   - Main path: the application uses the configured capture settings,
     folders, and framing behavior, records visible status, and finalizes
     the output file into the configured destination.
   - Result: the user gets a saved image or video and can keep working
     without restarting the session.

3. Work in fullscreen microscope mode.
   - Trigger: the user enters fullscreen from the toolbar, menu, or
     shortcut.
   - Main path: preview fills the screen, the windowed command surfaces
     collapse into a compact fullscreen surface, the user may collapse it
     further, and the application preserves a clear path back to windowed
     mode.
   - Result: the user gets an immersive microscope view while keeping safe
     access to essential actions and exit controls.

4. Discover and tune camera controls.
   - Trigger: the user opens the controls surface or the preferences
     dialog.
   - Main path: the application discovers the active camera's controls,
     groups them into stable families, renders each control with the right
     widget type, lets the user adjust supported values live, and stores
     per-camera or named-preset values where appropriate.
   - Result: the user can tune exposure, white balance, flicker, light,
     zoom, and vendor-specific controls without leaving the preview
     workspace.

## Workspace Model
`webcam-micro` should behave like a microscope control workstation, not a
settings dialog with a preview attached.

- Live preview is the primary visual target.
- The native menu bar covers the command surface.
- The top toolbar carries camera refresh, open/close, framing, still,
  record, fullscreen, controls, and preferences.
- The controls pane is dockable, detachable, hideable, and floatable, but
  hidden or moved controls must not consume preview space.
- The controls pane defaults to one column. Wide layouts may use two if the
  control order and section grouping stay stable.
- Capture settings such as output folders, formats, and sequence rules live
  in Preferences or Settings, not in the live camera control pane.
- The status bar stays compact and structured; long help and recovery text
  belong in diagnostics.
- One authoritative device-control layer owns each camera's control
  surface, and canonical hardware identity chooses that owner so one
  physical camera maps to one source of truth. The UI does not merge
  competing control owners.
- Camera-native controls are separate from genuine software-side image
  adjustments. Device-owned controls belong to the device-control layer.
- The product exposes the controls the active backend reports and can
  apply, with authoritative device-reported minimums, maximums, step
  sizes, defaults, and menu values.
- Control-family order stays stable across layouts and backends; unsupported
  families disappear cleanly instead of leaving placeholders.
- The product renders Resolution, Exposure, Focus, White balance, Backlight
  compensation, Brightness, Contrast, Hue, Saturation, Sharpness, Gamma,
  Light, Power line frequency, AC flicker compensation, Zoom, and
  vendor-specific controls with the widget type and value metadata the
  backend reports. Resolution is a dropdown source selector. Numeric
  controls use slider+spinbox rows with min/mid/max hints, step size, and
  default value. Enumerated controls, including 50/60 Hz and similar
  flicker menus, use dropdowns or combo boxes. Exposure and focus keep the
  manual value visible; auto or lock decides whether the backend drives the
  live value or the manual baseline. Light exposes on/off and level
  subcontrols when available, and missing subcontrols disable cleanly.
- When a camera reports an Auto checkbox or lock state for Exposure or
  Focus, the UI keeps the paired numeric control visible and synchronized
  with the live device value. Auto-enabled controls may grey out if the
  backend requires it, but the manual baseline stays available when the
  device supports manual adjustment.
- Additional backend-specific controls stay in Other Controls when exposed,
  while the split between camera-native controls and software-side
  adjustments remains intact.
- Numeric controls that expose values use native UVC-style settings
  components: a slider, min/mid/max labels below it, and an adjacent input
  field with up/down arrows. The input updates live from the slider, and
  invalid typed values clear to blank. Slider and spinbox ranges come from
  the active backend, not fixed UI guesses.
- Boolean controls use checkboxes.
- Enumerated controls use dropdowns or combo boxes.
- Read-only controls use labels or disabled value fields.
- Action controls use push buttons or equivalent one-shot actions.
- The product tolerates cameras that expose only a subset of common
  controls and must not fail simply because some expected controls are
  absent.

## Functional Requirements
- The product must be published as a Python package on PyPI and work on all
  platforms.

- The product must run both as an installed package and directly from source
  during development and testing.

- The main window must contain a primary command surface, a central preview
  area, a toggleable and detachable controls pane, and a compact status bar.

- The controls pane must be shown, hidden, docked, or detached without
  permanently consuming preview space.

- The product must provide a standard desktop command structure covering
  File, Edit, View, Camera, Capture, Tools, and Help.

- The windowed command surfaces must expose the primary actions, including
  controls toggle, still capture, record toggle, fullscreen/windowed toggle,
  preferences, and camera or preset actions.

- The rightmost visible end of the main toolbar must display
  `© 2026 Black Epsilon Ltd. and Apostol Apostolov`.

- The product must provide fullscreen mode in which preview fills the screen
  and the windowed command surfaces are replaced by a compact fullscreen
  command surface.

- The fullscreen command surface must support expanded and collapsed states,
  and the fullscreen/windowed toggle and collapse/expand control must remain
  visible in both.

- The product must provide fit-to-screen, fill-screen, and crop-based
  preview modes, and must apply crop, framing, and preview-layout changes
  live whenever backend capabilities permit.

- The product must allow preview framing and capture framing defaults to be
  configured and persisted.

- Source mode selection and output framing behavior are distinct concepts.

- The product must enumerate available cameras and the source capabilities
  the active backend exposes, including pixel formats, frame sizes, and
  frame rates.

- The product must not present unsupported synthetic source modes as native
  device modes.

- Supported source resolutions and frame sizes must appear through a
  dropdown source selector.

- Controls must follow the widget rules in Workspace Model, and the product
  must tolerate cameras that expose only a subset of common controls.

- The product must support common microscope-relevant controls where
  exposed, including backlight compensation, power line frequency, AC
  flicker compensation, white balance automatic/manual and temperature,
  exposure automatic/manual/lock, focus automatic/manual, zoom, brightness,
  contrast, saturation, hue, gamma, sharpness, lamp or LED, color profile,
  and vendor-specific extension controls.

- Automatic Video HDR must appear only when the active format reports HDR
  support; unsupported formats must skip the row and fail closed on writes.

- Camera-native controls must include light on/off and level subcontrols
  when exposed, and missing subcontrols must disable cleanly instead of
  presenting fake values.

- The user-controls section must reserve space for backend-owned image-
  quality adjustments when the active camera/backend reports them. It must
  not relabel device-owned brightness, contrast, hue, saturation, sharpness,
  gamma, backlight compensation, white balance, or similar camera controls
  as shell-managed rows.

- The user-controls section must place a Reset to Defaults button at the
  bottom.

- If a camera exposes a lamp, illumination, or activity LED control, the
  product must surface it and allow it to be turned off when supported.

- The product must keep live capture settings separate from camera controls
  and place image and video output configuration in Preferences or Settings,
  not in the live control pane.

- The built-in default preferred microscope values must be the default
  values for device-owned controls where the camera exposes them:
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
- External interfaces: desktop GUI, command surfaces, keyboard shortcuts,
  image and video outputs, platform camera backends, the PyPI package, and
  the `webcam-micro` entrypoint.

- Internal interfaces: UI, camera discovery, a single device-control layer,
  preview/capture, persistence, diagnostics, calibration or overlays, and
  platform adapters that translate native APIs into the stable control
  families above.

- Dependencies: Python, a cross-platform GUI toolkit, platform camera APIs
  or backend adapters, encoding support, and the integration hooks required
  by the active platform. The GUI shell baseline is `PySide6` with Qt
  Widgets; preview may stay on Qt Multimedia, but the control layer must be
  one authoritative device-control layer per camera.

- Compatibility expectations: the PyPI package must work on all platforms,
  source-run development must be supported, backend differences must not
  leak into broken user-facing contracts, and the control model must stay
  stable even when the native control shapes differ.

## Constraints and Assumptions
- Constraint: camera backends differ materially in control exposure and
  behavior across platforms, so the product cannot assume identical control
  surfaces everywhere.

- Constraint: on macOS, one authoritative control owner must handle writes
  for each camera. Preview may stay on Qt Multimedia, but unsupported
  native control paths must fail closed instead of being simulated in the
  shell.

- Assumption: the active camera/backend usually exposes a useful subset of
  controls and source modes, but the exact set varies by device. Some
  cameras expose light, LED, or flicker controls and some do not; the UI
  must surface only what the backend reports.

- Explicit tradeoff: the product is optimized for microscope-friendly
  preview, framing, control visibility, and repeatable local workflows
  rather than a generic camera ecosystem that promises identical hardware
  behavior everywhere.

## Acceptance Criteria
- A developer can clone the repository, install dependencies, install the
  package from PyPI or run it from source on any platform, open a camera
  session, and use the main preview workflow without terminal interaction.

- A user can open the controls surface, adjust the controls the active
  camera exposes, dock or detach it, switch between fit/fill/crop framing,
  capture still images, start and stop video recording, and find outputs in
  the configured folders.

- A user can choose a supported source resolution from a dropdown, see
  auto-enabled exposure or focus controls gray while the live value stays
  visible, use the split camera-controls and user-controls layout, adjust
  light on/off and level controls when exposed, and reset visible user
  controls from the bottom-most button.

- A user can tune exposure, white balance, backlight compensation, flicker
  compensation, power line frequency, zoom, brightness, contrast, hue,
  saturation, gamma, sharpness, and any activity LED or vendor-specific
  control that the active camera exposes.

- A user can adjust backlight compensation, white balance, brightness,
  contrast, hue, saturation, sharpness, and gamma through slider+spinbox
  widgets, with Auto or lock controls reflecting backend capabilities.
  Camera-owned exposure, focus, and white-balance sliders stay usable so
  moving them can switch the camera into manual mode.

- A user on any platform can enter fullscreen mode, use the fullscreen
  command surface in expanded and collapsed states, exit fullscreen safely,
  relaunch later, and observe persisted defaults, folders, presets,
  shortcuts, and controls-surface layout.

- The status bar stays compact while detailed runtime history remains in
  diagnostics.

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
