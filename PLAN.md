# Development Plan
**Doc ID:** PLAN
**Doc Type:** plan
**Project Version:** 0.2.0
**Project Stage:** alpha
**Maintenance Stance:** active
**Compatibility Policy:** forward-only
**Versioning Mode:** versioned
**Last Updated:** 2026-04-07
**DevCovenant Version:** 1.0.1b1

<!-- DEVCOV:BEGIN -->
This opening section is managed by DevCovenant.
Use `PLAN.md` to track active implementation work below this block.
<!-- DEVCOV:END -->

Use this plan to track the active implementation work that follows the
current workstation-shell contract in `SPEC.md`. Keep durable product rules
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
- This roadmap follows the workstation-shell contract in `SPEC.md`.
- The current phase is to keep the shell preview-first, capability-driven,
  and owned by one device-control layer per camera.
- The control plumbing is now collapsed to one owner per camera, so
  device-reported ranges and menus come from a single source of truth.

## Workflow
- Work in dependency order unless a real blocker forces reordering.
- Keep each item concrete enough that another person can continue it.
- Update status in the same session when work lands.
- Split large themes into numbered items with clear closure criteria.

## Implementation Direction
- Start from the current Qt shell baseline and tighten it toward `SPEC.md`.
- Keep preview on Qt Multimedia.
- Give each camera one authoritative device-control layer.
- Use device-reported minimums, maximums, step sizes, defaults, and menu
  values as the source of truth.
- Keep live camera controls separate from capture settings and status text.
- Gate format-dependent controls such as video HDR on explicit support.
- Prefer stable control families and predictable layout.
- Do not reintroduce shell-managed stand-ins for device-owned controls.
- Preserve the alpha delivery history in `CHANGELOG.md`; do not carry it
  forward here.

## Roadmap
1. [done] Shape the preview-first shell and stable control families.
   Goal:
   - make the shell feel like a microscope workstation
   Work:
   - group controls into Exposure, Focus, White Balance, Light/Flicker,
     Color/Image Quality, Zoom, Source Info, Actions, and Other Controls
   - render numeric controls with sliders, min/mid/max labels, and input
     fields
   - render booleans as checkboxes, enums as combo boxes, read-only items
     as labels, and action controls as buttons
   - hide unsupported families cleanly instead of leaving placeholders
   - keep controls dockable, detachable, and separate from capture settings
   Done when:
   - control groups are stable, readable, and fit the preview-first shell

2. [done] Cover backend capability handling and platform validation.
   Goal:
   - expose what cameras actually offer and keep it working
   Work:
   - normalize backend discovery across macOS, Windows, and Linux
   - surface AC flicker compensation, color profiles, backlight, vendor
     extension, lamp, illumination, and activity LED controls when
     reported
   - preserve per-camera defaults and named presets for supported controls
   - run launch, controls, fullscreen, still capture, recording, and
     persistence checks on supported platforms
   Done when:
   - supported control sets appear faithfully and the validated shell
     stays stable

3. [done] Collapse the control path into one authoritative device-
   control layer.
   Goal:
   - make each camera have one control owner
   Work:
   - choose one authoritative control owner at discovery or open time
   - query only that owner for controls, ranges, and menu values
   - route every control write through that owner
   - remove composite merge logic from the control path
   - keep preview and capture adapters separate from control ownership
   Done when:
   - the control path no longer merges competing backends and each camera
     exposes one source of truth for discovery and writes

## Exit Criteria
- The controls surface is capability-driven, grouped into stable families,
  and owned by one device-control layer per camera.
- The controls pane can dock, detach, hide, and restore without breaking
  the preview-first layout.
- Capture settings stay out of the live camera control surface.
- The status bar stays compact and structured.
- Supported camera controls and presets persist per camera.
- Platform checks cover launch, controls, fullscreen, stills, recording,
  and persistence.

## Validation Routine
- Use `devcovenant gate --start`, `gate --mid`, `devcovenant run`, and
  `gate --end` for implementation slices.
- Keep confirmed behavior notes in `CHANGELOG.md`.
- Replace this plan when the next major implementation phase is complete.
