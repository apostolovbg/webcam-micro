# Contributing
**Doc ID:** CONTRIBUTING
**Doc Type:** contributing-guide
**Project Version:** 0.2.0
**Last Updated:** 2026-04-06
**DevCovenant Version:** 1.0.1b1

<!-- DEVCOV:BEGIN -->
This opening section is managed by DevCovenant.
It defines the standard contributor workflow used by repositories that use
DevCovenant. Add repository-specific contributor notes below the managed
section.
<!-- DEVCOV:END -->

## Overview
This project uses DevCovenant.
Contributors should read `AGENTS.md` first, use `README.md` as the
entrypoint, and treat this guide as the short explanation of how work is
expected to land.

## Before You Change Files
Make sure you understand:

- the active workflow law in `AGENTS.md`

- the current plan in `PLAN.md` when the repository uses one

- the current project requirements in `SPEC.md` when the repository uses one

- whether the repository expects a managed environment

## Workflow
Follow the canonical gate sequence for every repository change, including
documentation-only edits:

```bash
python3 -m devcovenant gate --start
python3 -m devcovenant gate --mid
python3 -m devcovenant run
python3 -m devcovenant gate --end
```

If the console script is available on PATH, use `devcovenant ...` instead of
`python3 -m devcovenant ...`.

## Changelog And Documentation
Update the changelog when the repository rules require it.
Update the relevant docs in the same slice when behavior, workflow,
configuration, or other user-facing surfaces changed.

## Managed Files
Never edit content inside managed `<!-- DEVCOV* -->` blocks by hand.
Change the owning inputs and let refresh or the gate workflow regenerate the
managed output.

## Repository Notes
Add repository-specific contributor notes here. This section is preserved
across DevCovenant refresh and upgrade runs.

- Treat `webcam_micro/VERSION` as the release version source of truth for
  alpha work.
- When validating macOS camera controls, exercise the Qt-backed
  exposure, ISO, focus, white balance, and backlight path after a fresh
  reinstall, and confirm the shell-managed brightness, contrast, hue,
  saturation, sharpness, and gamma rows still appear in User Controls.
  Confirm unsupported AVFoundation custom-exposure writes fail closed,
  smooth autofocus stays gated by native support, and Automatic Video HDR
  stays hidden when the active format does not report support.
