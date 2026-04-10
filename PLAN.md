# Development Plan
**Doc ID:** PLAN
**Doc Type:** plan
**Project Version:** 0.2.0
**Project Stage:** alpha
**Maintenance Stance:** active
**Compatibility Policy:** forward-only
**Versioning Mode:** versioned
**Last Updated:** 2026-04-08
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
2. [Gap Map](#gap-map)
3. [Slice Plan](#slice-plan)
4. [Exit Criteria](#exit-criteria)
5. [Validation Routine](#validation-routine)

## Overview
- `PLAN.md` tracks active implementation work, not durable requirements.
- This plan follows the workstation-shell contract in `SPEC.md`.
- The current implementation still has a video save dialog, no recording
  profile negotiation, and a preview path that does expensive frame
  conversion and smooth scaling on the UI thread.
- The goal is to close the new capture and preview gaps in as few slices
  as possible without turning the work into a risky monolith.

## Gap Map
- Gap A: still capture is lossless by default, but video still depends on
  a save dialog in the normal record flow.
- Gap B: recording only chooses container and quality today, so the UI
  cannot yet expose a fast hardware-accelerated profile or a backend-
  supported raw or uncompressed path.
- Gap C: preview rendering still pays for copy-heavy RGB conversion and
  smooth scaling on the UI thread, which matches the reported split-second
  freezes.
- Gap D: the new save policy, profile negotiation, and preview fast path
  need backend-specific regression coverage before the behavior counts as
  stable.

## Slice Plan
1. [pending] Direct-save capture policy.
   Goal:
   - make still and video capture land in configured folders without a
     normal-flow save dialog
   Work:
   - keep stills lossless by default and keep JPEG as an explicit opt-in
   - move video capture to direct-save behavior using the configured folder
     and remembered name policy
   - keep save-path persistence and status messages aligned with the new
     direct-save flow
   Done when:
   - stills and video both save directly to configured folders by default,
     and no normal record action opens a save dialog

2. [pending] Recording profile negotiation.
   Goal:
   - expose the fastest supported recording path and the best quality path
     the backend can actually encode
   Work:
   - surface backend-supported recording profiles in Preferences
   - map profiles to codec, container, and quality choices per backend
   - prefer hardware-accelerated encode paths when available
   - expose raw or uncompressed recording only when the active backend can
     actually produce it
   Done when:
   - supported profiles are selectable, unsupported ones fail closed, and
     the chosen profile is what records

3. [pending] Preview fast path and regression coverage.
   Goal:
   - remove the recurring preview freezes and keep live view smooth
   Work:
   - profile the frame delivery and render path
   - cut redundant frame copies and avoid unnecessary smooth scaling on
     the hot path
   - keep the newest frame only and drop stale frames rather than stalling
     the UI
   - use backend-specific GPU or zero-copy paths when the runtime exposes
     them
   - add regression coverage for direct-save capture, profile selection,
     and preview stutter behavior
   Done when:
   - preview stays smooth over long runs and tests cover the new capture
     and preview policies

## Exit Criteria
- Stills stay lossless by default and can use backend-supported raw or
  uncompressed export when available.
- Video records directly into the configured folder without a normal-flow
  dialog.
- Recording profiles are visible, backend-aware, and fail closed on
  unsupported combinations.
- Preview stays responsive without recurring split-second freezes.
- The new behavior is covered by tests and the docs match the shipped
  behavior.

## Validation Routine
- Use `devcovenant gate --start`, `gate --mid`, `devcovenant run`, and
  `gate --end` for implementation slices.
- Keep confirmed behavior notes in `CHANGELOG.md`.
- Replace this plan when the capture and preview target slice set is
  complete.
