# Development Plan
**Doc ID:** PLAN
**Doc Type:** plan
**Project Version:** 0.2.0
**Project Stage:** alpha
**Maintenance Stance:** active
**Compatibility Policy:** forward-only
**Versioning Mode:** versioned
**Last Updated:** 2026-04-06
**DevCovenant Version:** 1.0.1b1

<!-- DEVCOV:BEGIN -->
This opening section is managed by DevCovenant.
Use `PLAN.md` to track active implementation work below this block.
<!-- DEVCOV:END -->

Use this plan to track the active implementation work that follows the
revised workstation-shell contract in `SPEC.md`. Keep durable product rules
in `SPEC.md` and history in `CHANGELOG.md`.

## Table of Contents
1. [Overview](#overview)
2. [Workflow](#workflow)
3. [Implementation Direction](#implementation-direction)
4. [Roadmap](#roadmap)
5. [Exit Criteria](#exit-criteria)
6. [Validation Routine](#validation-routine)

## Overview
- `PLAN.md` tracks active implementation work, not durable requirements.
- This roadmap replaces the finished beta-plan tracker and now focuses on the
  workstation-shell contract in `SPEC.md`.
- The next phase is to make the Qt shell feel like a microscope workstation:
  capability-driven controls, dockable and detachable surfaces, compact
  status, and a clear separation between live controls and capture settings.
  The next slice is to move camera-owned controls onto a native device-
  control backend that reads real device ranges and modes instead of
  shell-managed stand-ins.

## Workflow
- Work in dependency order unless a real blocker forces reordering.
- Keep each item concrete enough that another person can continue it.
- Update status in the same session when work lands.
- Split large themes into numbered items with clear closure criteria.

## Implementation Direction
- Start from the current Qt shell baseline and tighten it toward `SPEC.md`.
- Prioritize daily microscope use: preview-first layout, capability-driven
  controls, quiet capture, fullscreen safety, and persistence.
- Treat control discovery, widget typing, and backend-specific capability
  bridges as product work, not ad-hoc exceptions.
- Keep live camera controls separate from capture settings and status text.
- Keep preview on Qt Multimedia, but let native device-control backends
  own device-adjustment writes. On macOS, UVC-capable camera controls
  should go through a native control backend or adapter when the platform
  capture stack cannot safely apply them; AVFoundation stays for preview
  and any control it can truly support.
- Use device-reported minimums, maximums, step sizes, defaults, and menu
  values as the source of truth for native camera controls.
- Gate format-dependent controls such as video HDR on explicit
  active-format support so unsupported cameras do not surface
  crash-prone rows.
- Prefer stable control families and predictable layout over ad-hoc polish.
- Preserve the alpha delivery history in `CHANGELOG.md`; do not carry it
  forward here.

## Roadmap
1. [done] Rebuild the controls surface around stable control families and
   type-aware widgets.
   Goal:
   - surface camera controls with native UVC-style affordances
   Work:
   - group controls into Exposure, Focus, White Balance, Light/Flicker,
     Color/Image Quality, Zoom, Source Info, Actions, and Other Controls
   - render numeric controls with sliders, min/mid/max labels, and input
     fields
   - render booleans as checkboxes, enums as combo boxes, read-only items as
     labels, and action controls as buttons
   - hide unsupported families cleanly instead of leaving placeholders
   Done when:
   - control groups are stable, readable, and match the active backend's
     capabilities

2. [done] Make the controls surface dockable, detachable, and
   preview-friendly.
   Goal:
   - let the pane move without consuming preview space
   Work:
   - support hide, dock, float, and restore behavior
   - persist the controls-surface visibility and dock state
   - keep a one-column default layout and allow a wider two-column variant
     when the layout can support it
   - keep preview central even when the control surface is floating
   Done when:
   - users can dock, detach, hide, and restore the control pane without
     losing the preview-first layout

3. [done] Separate high-frequency shell actions from capture settings.
   Goal:
   - keep toolbar and status bar lean
   Work:
   - keep refresh, open and close, framing, still, record, fullscreen,
     controls, and preferences in the live command surfaces
   - move image and video output configuration into Settings or Preferences
   - keep the status bar compact and structured
   - remove narrative helper text and other wall-of-text drift from the
     main shell
   Done when:
   - the live shell is concise and the capture settings live in the settings
     workflow instead of the control pane

4. [done] Expand backend capability handling for light, flicker, and vendor
   controls.
   Goal:
   - expose more of what cameras actually offer
   Work:
   - normalize backend discovery across macOS, Windows, and Linux
   - surface AC flicker compensation, color profiles, backlight, and vendor
     extension controls when the backend reports them
   - surface lamp, illumination, or activity LED controls when available
   - preserve per-camera defaults and named presets for supported controls
   Done when:
   - the active camera's supported control set appears faithfully and
     persists per camera and per preset

5. [done] Validate the revised workstation shell across supported
   platforms.
   Goal:
   - keep the new layout and control model stable
   Work:
   - run focused smoke and manual checks for launch, controls discovery,
     fullscreen overlay, recording, still capture, and settings persistence
   - record any OS- or device-specific gaps as follow-up slices
   - keep the workflow notes aligned with the observed platform behavior
   Done when:
   - the revised SPEC contract is verified by automated tests and
     operational checks on the supported environments we can run here

6. [done] Rework the controls pane into camera controls and user
   controls.
   Goal:
   - match the exact camera-controls and user-controls split now
     expected by the spec
   Work:
   - expose supported camera resolutions in a dropdown menu
   - render exposure as a slider+spinbox with an Auto checkbox when the
     camera exposes auto exposure; when Auto is enabled, the slider and
     spinbox grey out and snap to the auto value
   - render focus as a slider+spinbox with an Auto checkbox when the
     camera exposes auto focus; when Auto is enabled, the slider and
     spinbox grey out and snap to the auto value
   - render light as an on/off checkbox when exposed, plus a level
     slider when exposed; any missing on/off or level subcontrol must be
     disabled cleanly
   - keep backlight compensation and white balance in the user-controls
     section when the active camera exposes them, and always surface
     backend-owned brightness, contrast, hue, saturation, sharpness,
     gamma, gain, and power-line-frequency rows with slider+spinbox
     widgets, with Auto checkboxes on contrast, hue, and white balance;
     camera-owned exposure, focus, and white-balance sliders stay usable
     so moving them can switch the camera into manual mode
   - place the reset-to-defaults button at the bottom of the user-
     controls section
   Done when:
   - the pane cleanly separates camera-native controls from backend-
     owned image-quality adjustments and keeps Auto rows disabled while
     camera-owned exposure, focus, and white-balance sliders stay
     interactive

7. [done] Move camera-owned rows onto a native device-control backend.
   Goal:
   - make the camera-adjustment rows match the camera's own control model
   Work:
   - read device-reported minimums, maximums, step sizes, defaults, and
     menu values for every exposed control
   - route exposure, exposure lock or priority, focus, white balance,
     backlight compensation, power line frequency, AC flicker
     compensation, brightness, contrast, hue, saturation, gamma,
     sharpness, zoom, lamp, LED, and vendor-specific controls through the
     device-control backend
   - keep preview and recording on the platform capture stack, but stop
     simulating device-owned control rows in the shell
   - render power-line frequency and similar mode selectors as dropdowns
     and preserve the manual exposure baseline while auto or lock modes are
     active
   - hide or disable controls the backend cannot safely apply instead of
     guessing at a behavior
   Done when:
   - the user-visible camera-adjustment rows come from the device-control
     backend, with live ranges and menu values matching the camera rather
     than fixed UI defaults, and the macOS control path uses libuvc while
     Linux keeps V4L2-backed control discovery for matching devices

## Exit Criteria
- The controls surface is capability-driven and grouped into stable
  families.
- The controls pane can dock, detach, hide, and restore without breaking
  the preview-first layout.
- Capture settings are no longer mixed into the live camera control
  surface.
- The status bar stays compact and structured.
- Supported camera controls and presets persist per camera.
- Platform checks cover launch, controls, fullscreen, stills, recording,
  and persistence.

## Validation Routine
- Use `devcovenant gate --start`, `gate --mid`, `devcovenant run`, and
  `gate --end` for implementation slices.
- Keep operational test notes in `CHANGELOG.md` when behavior changes are
  confirmed.
- Replace this plan again when the next major implementation phase is
  complete.
