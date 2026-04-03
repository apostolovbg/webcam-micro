# Development Plan
**Doc ID:** PLAN
**Doc Type:** plan
**Project Version:** 0.0.1
**Project Stage:** prototype
**Maintenance Stance:** active
**Compatibility Policy:** forward-only
**Versioning Mode:** versioned
**Last Updated:** 2026-04-03
**DevCovenant Version:** 1.0.1b1

<!-- DEVCOV:BEGIN -->
This opening section is managed by DevCovenant.
Use `PLAN.md` to track active implementation work below this block.
<!-- DEVCOV:END -->

Use this plan to track active implementation work.
Keep items dependency-ordered, concrete, and current.
Use it to take `webcam-micro` from governed prototype scaffolding to a usable
PyPI-distributed microscope camera application.

## Table of Contents
1. [Overview](#overview)
2. [Workflow](#workflow)
3. [Writing Direction](#writing-direction)
4. [Active Work](#active-work)
5. [Validation Routine](#validation-routine)

## Overview
- Use `PLAN.md` for active multi-slice work, not for durable product
  requirements.
- Record durable project requirements in `SPEC.md` when your repo uses SPEC.

- Record completed slice history in `CHANGELOG.md`.

- Mark completed items as `[done]` and outstanding items as `[not done]`.

- Prefer one roadmap that people can execute over a long wish list of vague
  intentions.

## Workflow
- Work in dependency order unless a real blocker forces reordering.

- Keep each item concrete enough that another person can continue it.

- Update status in the same session when work lands.

- Split very large themes into numbered items with clear closure criteria.

## Writing Direction
- State what the work is, why it matters, what has to happen, and how you
  will know it is done.
- Prefer plain language over slogans.

- Use bullets for requirements and acceptance checks.

- Treat vague work items as unfinished planning, not as good enough
  planning.

## Active Work
1. [done] Decide the application foundation and ship the package skeleton.
   Goal:
   - establish the initial package layout, application entrypoint, and
     implementation baseline for the prototype
   Completed work:
   - chose `ttkbootstrap` on top of Tk as the initial GUI shell baseline
     because it remains compatible with the repository's governed package-lock
     matrix
   - chose a pluggable camera-backend contract with a stage-one null backend
     and an FFmpeg-backed discovery/preview backend as the first concrete
     target
   - created the single `webcam_micro/` app directory, the `webcam-micro`
     console entrypoint, and a minimal launchable shell path
   - colocated the version file, package-runtime lock, and package licenses
     inside `webcam_micro/` instead of splitting them into a second app-owned
     folder
   - added headless smoke tests and package-contract checks for the new
     entrypoint and foundation modules
   Outcome:
   - the repository now ships a real package skeleton with a documented Stage
     1 baseline that later camera and UI work can build on directly

2. [done] Implement camera discovery, session lifecycle, and live preview.
   Goal:
   - let a user open a supported camera and see a stable live microscope
     preview
   Completed work:
   - implemented FFmpeg-backed camera discovery through platform-aware device
     enumeration in the active backend
   - added session open, close, and switch handling with a low-latency reader
     that keeps only the newest frame instead of queueing stale preview data
   - rendered live preview frames inside the main preview area and exposed
     backend, camera, and preview state in visible runtime status
   - handled missing dependencies, missing devices, and recoverable open or
     preview failures without crashing the UI shell
   Outcome:
   - the prototype now launches a real preview workspace where a user can
     discover cameras, choose one, and see live video while session state
     remains visible

3. [done] Build the main window and preview-first working shell.
   Goal:
   - deliver the main window, menu bar, toolbar, status bar, and separate
     controls window defined by the spec
   Completed work:
   - built the governed main window shell with the required menu bar, top
     toolbar, central preview area, and dynamic bottom status bar
   - added a separate controls window that opens and closes independently of
     the preview workspace
   - exposed the required File, Edit, View, Camera, Capture, Tools, and Help
     menu sections plus the primary toolbar actions for controls, camera
     refresh and open, still capture, recording, fullscreen, and preferences
   - rendered `© Apostol Apostolov` at the rightmost visible end of the main
     toolbar
   Outcome:
   - the prototype now presents the governed preview-first shell contract
     while keeping the low-latency live preview path intact for later control,
     fullscreen, and capture work

4. [not done] Expose camera controls with guvcview-style numeric widgets.
   Goal:
   - expose real backend controls through a trustworthy and usable settings
     surface
   Why this matters:
   - camera control is a core value of the product, and the numeric widget
     behavior is now a durable spec requirement
   Work to do:
   - map numeric, boolean, enumerated, read-only, and action controls from
     the active backend into UI components
   - implement the numeric control widget with a slider, min/mid/max labels
     beneath it, and an adjacent input field with up/down arrows
   - keep the input field synchronized live from slider movement
   - clear invalid typed numeric values to blank instead of accepting bad
     input
   - fail softly when cameras omit controls or reject a requested value
   Done when:
   - exposed numeric controls use the required slider-plus-input behavior
   - control updates apply live where the backend supports them
   - unsupported or incompatible controls do not break the session

5. [not done] Implement preview framing and fullscreen microscope workflows.
   Goal:
   - support the live viewing behaviors that make microscope work practical
   Why this matters:
   - fit, fill, crop, and fullscreen handling define whether the application
     feels built for microscope use instead of generic webcam use
   Work to do:
   - implement fit-to-screen, fill-screen, and crop-based preview behavior
   - keep preview framing and capture framing as distinct concepts in state
   - add fullscreen mode with the detached movable toolbar and handle
   - support expanded and collapsed fullscreen-toolbar states with safe exit
     controls
   Done when:
   - a user can switch framing modes live during preview
   - fullscreen mode preserves access to essential actions and safe exit
   - the detached toolbar behaves as specified in both states

6. [not done] Deliver still capture, video recording, and output handling.
   Goal:
   - let users save microscope stills and videos without leaving the GUI
   Why this matters:
   - preview alone is not enough; capture is one of the primary working
     outcomes promised by the product
   Work to do:
   - implement still capture with timestamp-based default naming and JPEG/PNG
     output
   - implement video recording with explicit start and stop, visible
     recording state, and elapsed time
   - add default image and video folder handling and create missing folders
     automatically
   - wire capture and recording actions into toolbar, menu, and shortcut
     flows
   Done when:
   - stills and videos save into the configured destinations
   - recording start, stop, and status are visible and reliable
   - capture output follows the configured framing and output rules

7. [not done] Add persistence, defaults, presets, and shortcuts.
   Goal:
   - make repeated microscope sessions fast and predictable
   Why this matters:
   - remembered settings and shortcuts are what turn a one-off viewer into a
     practical workstation tool
   Work to do:
   - persist output folders, framing choices, window geometry, fullscreen
     toolbar state, and selected camera where appropriate
   - implement built-in defaults, user-editable defaults, per-camera
     remembered settings, and named presets
   - apply default values only when the active camera exposes compatible
     controls
   - implement shortcut editing and conflict prevention for the primary
     actions
   Done when:
   - relaunching the app restores meaningful working state
   - defaults and presets degrade gracefully on cameras with partial control
     surfaces
   - shortcut conflicts are detected and blocked

8. [not done] Add diagnostics, package-release readiness, and prototype
   exit checks.
   Goal:
   - make the prototype debuggable, testable, and ready for package
     distribution and broader evaluation
   Why this matters:
   - the prototype is only useful if failures are explainable and the package
     can be installed and exercised on real platforms
   Work to do:
   - add a user-accessible diagnostics surface or log view for runtime state
     and non-fatal failures
   - expand automated coverage beyond bootstrap so core app flows are tested
   - complete package metadata and release-path validation for PyPI
   - verify the prototype against the spec acceptance criteria and capture
     open gaps before any stage change discussion
   Done when:
   - runtime diagnostics make backend and session failures inspectable
   - the package is ready for reliable installation and release validation
   - the team can evaluate the prototype against explicit, tested exit checks

## Validation Routine
- Verify checks and tests pass.

- Verify generated artifacts are synchronized after refresh.

- Verify documentation and changelog were updated where behavior changed.

- Verify `devcovenant check` passes after the slice closes.
