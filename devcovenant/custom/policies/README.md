# Custom Policies
**Last Updated:** 2026-04-03
**Project Version:** 1.0.1b1

## Table of Contents
- [Overview](#overview)
- [Directory Layout](#directory-layout)
- [Override Semantics](#override-semantics)
- [Metadata and Assets](#metadata-and-assets)
- [Workflow](#workflow)

## Overview
Custom policies live under `devcovenant/custom/policies/<policy-id>/`.
They are repository-owned extensions and can fully replace builtin policies
with matching IDs.

## Directory Layout
Expected files mirror builtin policy structure:
- `<policy-id>.yaml` descriptor
- `<policy-id>.py` check script
- optional `autofix/*.py`
- optional `assets/` templates

## Override Semantics
When a custom policy ID matches a builtin policy ID:
- custom script is loaded
- builtin script is suppressed
- builtin autofix helpers for that policy are suppressed

Activation remains config-driven via `policy_state`.

## Metadata and Assets
Descriptor metadata is merged with profile/config layers in the standard
precedence order.

Policy-owned asset files should be declared via profile manifests so refresh
can materialize them consistently. Avoid hidden side-channel file writes from
policy scripts when declarative assets are sufficient.

## Workflow
1. Change descriptor and script together.
2. Update mirrored tests under `tests/devcovenant/custom/policies/...`.
3. Run `devcovenant refresh` after descriptor/profile updates.
4. Run full gate sequence:
   `gate --start` -> `gate --mid` (rerun until clean) ->
   `run` -> `gate --end`.
