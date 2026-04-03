# Custom Profiles
**Last Updated:** 2026-04-03
**Project Version:** 1.0.1b1

## Table of Contents
- [Overview](#overview)
- [Directory Layout](#directory-layout)
- [Override Semantics](#override-semantics)
- [Translator Declarations](#translator-declarations)
- [Workflow](#workflow)

## Overview
Custom profiles live under `devcovenant/custom/profiles/<profile-name>/`.
They let a repository tailor assets, overlays, selectors, hooks, and
translator declarations without editing shipped builtin profile manifests.
Custom profile payloads are repository-owned and should not be documented as
packaged builtin inventory.
Package builds keep custom-folder scaffolding (`README.md`, `__init__.py`) but
do not ship repository-specific custom profile payload directories.

## Directory Layout
A custom profile typically contains:
- `<profile-name>.yaml` manifest
- optional `assets/` templates
- optional `<profile-name>_translator.py` for language profiles

## Override Semantics
When custom and builtin profiles share a profile name:
- custom profile takes precedence
- builtin profile with that name is not applied

For unique profile names, custom profiles are additive and may be selected in
`config.yaml` under `profiles.active`.

## Translator Declarations
Custom language profiles may declare translators using the same schema as core
language profiles.

Translator declarations should stay policy-agnostic and return normalized
language units through shared translator runtime contracts.

## Workflow
1. Edit custom profile manifest/assets.
2. Refresh to regenerate registries and generated assets.
3. Verify with full gate sequence:
   `gate --start` -> `gate --mid` (rerun until clean) ->
   `run` -> `gate --end`.
4. Keep `PROFILE_MAP.md` and docs aligned when adding new profiles.
