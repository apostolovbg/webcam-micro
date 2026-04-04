# Development Plan
**Doc ID:** PLAN
**Doc Type:** plan
**Project Version:** 0.0.1
**Project Stage:** prototype
**Maintenance Stance:** active
**Compatibility Policy:** forward-only
**Versioning Mode:** versioned
**Last Updated:** 2026-04-04
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
- Note: items 1-5 record the original shell delivery path. Item 6 records
  the completed Flet experiment. Items 7-8 supersede that experiment with a
  `PySide6` and Qt Widgets migration that restores native desktop menu bars
  and leans camera discovery and preview onto Qt-owned media objects.

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

4. [done] Expose camera controls with guvcview-style numeric widgets.
   Goal:
   - expose real backend controls through a trustworthy and usable settings
     surface
   Completed work:
   - defined a typed camera-control surface in the active backend contract so
     numeric, boolean, enumerated, read-only, and action controls can render
     truthfully from backend data
   - added an AVFoundation-backed macOS control bridge under the FFmpeg
     preview backend, with soft fallback when the selected camera or platform
     does not expose controls
   - rebuilt the separate controls window to render numeric sliders with
     min/mid/max labels and adjacent spinbox input, plus boolean, enum,
     read-only, and action widgets
   - kept slider motion synchronized to the adjacent numeric field and cleared
     invalid typed numeric values to blank instead of accepting bad input
   - failed softly when controls were missing, fixed, unsupported, or
     rejected by the backend so the preview session stayed usable
   Outcome:
   - the prototype now exposes the active camera's real control surface in a
     separate settings window, and the governed numeric widget behavior is in
     place for cameras that expose numeric values

5. [done] Implement preview framing and fullscreen microscope workflows.
   Goal:
   - support the live viewing behaviors that make microscope work practical
   Completed work:
   - implemented live fit, fill, and centered crop preview rendering with
     resize-aware rerendering from the newest cached frame
   - separated preview framing and capture framing in runtime state and status
     reporting so later capture work can follow its own framing rules
   - replaced the bare fullscreen toggle with a detached movable toolbar that
     keeps expanded and collapsed states plus safe windowed exit controls
   - mirrored the primary camera and framing actions into the fullscreen
     toolbar and added headless coverage for framing and toolbar helper logic
   Outcome:
   - the prototype now supports microscope-friendly live framing and a real
     fullscreen workflow that preserves essential actions and safe exit paths

6. [done] Start the Flet rewrite with a single-window shell foundation.
   Goal:
   - replace the original Tk shell with a working Flet desktop workspace
     without interrupting the preview, framing, and controls foundation
   Why this matters:
   - the user asked for a modern Flet interface, and the rewrite needs a
     stable baseline before later capture, persistence, and diagnostics work
     can continue safely
   Completed work:
   - replaced the package-runtime GUI dependency with `flet` and refreshed
     the governed lock, license, and registry artifacts for the new surface
   - rebuilt the main shell as a Flet single-window workspace with an app
     bar, command row, dynamic controls side surface, status bar, and
     fullscreen overlay command surface
   - preserved live camera discovery, session open and close, preview
     rendering, fit/fill/crop framing, and typed camera-control widgets on
     the new shell baseline
   - updated the launch contract, headless tests, and durable docs to define
     the two-slice rewrite and the first Flet slice accurately
   Outcome:
   - the prototype now runs on the Flet baseline with the core live preview
     and controls workflow intact, so the second slice can finish shell
     parity and polish instead of bootstrapping the rewrite

7. [done] Start the `PySide6` and Qt Widgets migration foundation.
   Goal:
   - replace the current Flet shell baseline with a working `PySide6`
     and Qt Widgets desktop shell without breaking the preview, framing,
     and controls foundation
   Why this matters:
   - the governed shell requires real native desktop menu bars, and the
     inspected Flet surface does not provide a native macOS, Windows, and
     Linux menu-bar path that matches that contract
   Completed work:
   - replaced the package-runtime GUI dependency with `PySide6` and
     refreshed the governed lock, license, and registry artifacts for the Qt
     surface
   - rebuilt the main shell as a Qt Widgets `QMainWindow` with a native
     desktop menu bar, toolbar, status bar, preview-first central workspace,
     and toggleable controls dock
   - replaced the FFmpeg-first runtime path with a Qt Multimedia camera
     backend so discovery, session ownership, and live preview now ride the
     Qt media stack instead of a separately bundled preview backend
   - preserved fit/fill/crop framing and typed camera-control widgets on the
     new Qt baseline while keeping the remaining repo layer focused on
     microscope-specific policy and the macOS AVFoundation control bridge
   - updated the launch contract, tests, and durable docs so the repository
     now describes the Qt migration truthfully instead of describing Flet as
     the intended shell baseline
   Outcome:
   - the prototype now runs on a Qt Widgets shell foundation with native
     desktop menus, a Qt-owned live preview path, and the core controls
     workflow intact, so the next slice can finish workstation parity instead
     of bootstrapping the migration

8. [not done] Complete the Qt workstation shell and native desktop parity.
   Goal:
   - finish the Qt migration so the modern shell supports the governed
     workstation behaviors and native command surfaces on all desktop
     platforms
   Why this matters:
   - the foundation slice only establishes the new baseline; the native
     command model, fullscreen workflow, and remaining shell affordances
     still need to land on top of it
   Completed work so far:
   - replaced the bare Qt fullscreen toggle with a compact fullscreen
     command surface that keeps expanded and collapsed states plus safe
     windowed exit available
   - hid the windowed toolbar, notes, status bar, and controls dock while
     fullscreen is active so the preview-first shell behaves like a real
     microscope workspace instead of a maximized window
   - aligned native menu actions with Qt menu roles for Preferences, About,
     and Quit so macOS and other desktop shells can place those commands more
     naturally
   Work to do:
   - implement the governed File, Edit, View, Camera, Capture, Tools, and
     Help command structure through native menu-bar actions
   - wire still capture, recording, output handling, and remaining
     device-session behavior through Qt-native media objects where they meet
     the governed product contract instead of rebuilding parallel native
     stacks
   - restore fullscreen, controls-surface, preferences, diagnostics, still,
     and recording shell affordances on the Qt baseline
   - validate preview, controls-surface behavior, fullscreen transitions,
     and menu-bar behavior interactively across supported desktop platforms
   - keep tests, docs, and governed artifacts aligned so only the Qt shell
     baseline remains described in the repository
   Done when:
   - the Qt shell carries the intended desktop workflow with native menu
     bars and no placeholder shell affordances
   - the remaining repo-owned backend layer is thinner, policy-oriented,
     and no longer duplicates Qt-native media and shell responsibilities
   - interactive preview, controls, fullscreen, and menu flows are stable
     enough for later feature slices to build on directly
   - automated tests and docs describe only the Qt Widgets shell baseline

9. [not done] Deliver still capture, video recording, and output handling.
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

10. [not done] Add persistence, defaults, presets, and shortcuts.
   Goal:
   - make repeated microscope sessions fast and predictable
   Why this matters:
   - remembered settings and shortcuts are what turn a one-off viewer into a
     practical workstation tool
   Work to do:
   - persist output folders, framing choices, window geometry,
     controls-surface visibility, fullscreen-surface state, and selected
     camera where appropriate
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

11. [not done] Add diagnostics, package-release readiness, and prototype
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
   - keep the package metadata, CI build artifact flow, and manual publish
     path aligned with the Python `3.11+` support floor and validated CI
     artifacts
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
