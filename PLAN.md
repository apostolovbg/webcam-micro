# Development Plan
**Doc ID:** PLAN
**Doc Type:** plan
**Project Version:** 0.1.0a1
**Project Stage:** alpha
**Maintenance Stance:** active
**Compatibility Policy:** forward-only
**Versioning Mode:** versioned
**Last Updated:** 2026-04-05
**DevCovenant Version:** 1.0.1b1

<!-- DEVCOV:BEGIN -->
This opening section is managed by DevCovenant.
Use `PLAN.md` to track active implementation work below this block.
<!-- DEVCOV:END -->

Use this plan to track the beta-hardening work that follows the official
alpha release. Alpha delivery is complete, so keep active implementation
work here and keep durable product rules in `SPEC.md` and history in
`CHANGELOG.md`.

## Table of Contents
1. [Overview](#overview)
2. [Workflow](#workflow)
3. [Beta Direction](#beta-direction)
4. [Roadmap](#roadmap)
5. [Beta Exit Criteria](#beta-exit-criteria)
6. [Validation Routine](#validation-routine)

## Overview
- `PLAN.md` tracks active implementation work, not durable requirements.
- This replacement plan starts after the official alpha release.
- The beta goal is to tighten the current Qt shell toward the `SPEC.md`
  workstation contract using operational-test feedback.

## Workflow
- Work in dependency order unless a real blocker forces reordering.
- Keep each item concrete enough that another person can continue it.
- Update status in the same session when work lands.
- Split large themes into numbered items with clear closure criteria.

## Beta Direction
- Start from the current alpha behavior and remove the rough edges
  exposed in manual testing.
- Treat placeholder or truncated shell behavior as beta work.
- Prioritize changes that affect daily use: layout, capture friction,
  control discovery, preview responsiveness, persistence, and platform
  behavior.
- Preserve the alpha delivery history in `CHANGELOG.md`; do not carry it
  forward here.

## Roadmap
1. [done] Align the Qt shell layout and command placement with SPEC.
   Goal:
   - make the menu, toolbar, controls dock, and status surfaces match the
     documented workstation flow
   Work:
   - move commands that currently sit in the wrong surface
   - remove placeholder labels and truncated affordances
   - keep the primary workflow close to the preview area
   Done when:
   - the visible shell follows `SPEC.md`'s command model without obvious
     mismatch

2. [done] Make still capture silent and folder-driven.
   Goal:
   - save stills straight to the configured folder without repeated prompts
   Work:
   - use the persisted still output folder as the default destination
   - save stills immediately without a save dialog
   - preserve the chosen folder across launches
   Done when:
   - a still capture saves silently to the configured directory by default
   - still capture never blocks on a save dialog

3. [done] Improve preview responsiveness and frame cadence.
   Goal:
   - reduce visible lag in live preview while keeping recording smooth
   Work:
   - use a tighter preview polling cadence and precise timer for cached
     frame updates
   - rerender the newest cached frame as soon as it is available
   - keep the recorded video path at least as smooth as current alpha
   Done when:
   - preview lag is materially lower on supported cameras
   - recording remains smooth and stable under the same test cameras

4. [done] Complete camera-control exposure and placement.
   Goal:
   - expose the supported controls cleanly and in the right workspace
     surfaces
   Work:
   - surface all supported controls that SPEC calls for
   - put related control groups where users expect them
   - hide backend-specific clutter and unsupported controls
   - keep per-camera defaults and named presets usable from Preferences
   Done when:
   - supported controls are discoverable and editable without hunting
   - control state persists per camera and per preset as expected

5. [done] Harden platform permissions, recording, and containers.
   Goal:
   - make cross-platform runtime behavior consistent enough for beta
     testing
   Work:
   - keep camera permission prompts reliable on macOS and other supported
     OSes
   - validate recording containers and output formats on each platform
   - preserve the no-surprise launch behavior after permission is granted
   Done when:
   - first-launch camera permission works reliably where required
   - the supported recording path is verified on each desktop target

6. [done] Defer the remaining cross-platform validation until after beta
   publication.
   Goal:
   - ship the beta candidate without blocking on Windows and Linux
     operational tests
   Work:
   - record the deferred Windows and Linux camera and recording checks
     as post-beta follow-up
   - keep the release docs and package metadata truthful about the
     published beta path
   Done when:
   - the beta publication path is unblocked
   - the remaining platform validation is explicitly deferred instead of
     treated as pre-beta work

## Beta Exit Criteria
- No placeholder shell surfaces remain in the primary workspace.
- Still capture saves silently to the configured folder by default.
- Live preview feels responsive enough for microscope work.
- Supported controls and named presets are exposed where users expect
  them.
- Permission, recording, and output behavior are stable across supported
  desktop platforms.
- Operational-testing findings are recorded and turned into a short beta
  follow-up plan.

## Validation Routine
- Use `devcovenant gate --start`, `gate --mid`, `devcovenant run`, and
  `gate --end` for implementation slices.
- Keep operational test notes in `CHANGELOG.md` when behavior changes are
  confirmed.
- Replace this plan again when beta work is complete.
