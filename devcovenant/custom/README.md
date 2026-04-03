# Custom Extensions
**Last Updated:** 2026-04-03
**Project Version:** 1.0.1b1

## Table of Contents
- [Overview](#overview)
- [Policy Extensions](#policy-extensions)
- [Profile Extensions](#profile-extensions)
- [Override Rules](#override-rules)
- [Workflow](#workflow)

## Overview
`devcovenant/custom/` is the repository-owned extension surface.

Use this directory to add or override behavior without editing shipped builtin
files. Everything here is project-specific and stays under repository control.

## Policy Extensions
Place custom policies under:
- `devcovenant/custom/policies/<policy-id>/`

Typical custom policy files:
- `<policy-id>.py` for check logic
- `<policy-id>.yaml` for descriptor text and metadata defaults
- optional `autofix/` modules
- optional `assets/` templates referenced by profiles

## Profile Extensions
Place custom profiles under:
- `devcovenant/custom/profiles/<profile-name>/`

Typical profile files:
- `<profile-name>.yaml` manifest
- optional `assets/` templates
- optional `<profile-name>_translator.py` when profile category is language

## Override Rules
- Same-id custom policy overrides same-id builtin policy.
- Same-name custom profile overrides same-name builtin profile.
- Policy activation still comes only from `config.policy_state`.
- Profiles contribute overlays, assets, selectors, hooks, and translators.

Custom changes should keep contract compatibility unless a contract change is
intentional and documented in `SPEC.md`.

## Workflow
1. Implement custom policy/profile changes in this directory.
2. Update tests under mirrored `tests/devcovenant/custom/...` paths.
3. Update relevant docs and maps (`POLICY_MAP.md`, `PROFILE_MAP.md`).
4. Run `devcovenant refresh` after manifest or descriptor changes.
5. Run full gate sequence before handing off changes:
   `gate --start` -> `gate --mid` (rerun until clean) ->
   `run` -> `gate --end`.
