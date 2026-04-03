# webcam-micro
**Doc ID:** README
**Doc Type:** repo-readme
**Project Version:** 0.0.1
**Last Updated:** 2026-04-03
**DevCovenant Version:** 1.0.1b1

<!-- DEVCOV:BEGIN -->

<!-- DEVCOV:END -->

Cross-platform microscope camera application distributed as a Python package
on PyPI.

## Overview
`webcam-micro` is a preview-first microscope camera application for live
viewing, camera control, still capture, and recording.

The current prototype uses `ttkbootstrap` on top of Tk for the GUI shell and
a pluggable camera-backend layer. Stage 3 now ships the preview-first main
window with a governed menu bar, top toolbar, bottom status bar, a separate
controls window, FFmpeg-backed camera discovery, safe session open and close
handling, visible backend and camera status, and a low-latency live preview
path that keeps only the newest frame instead of queueing stale preview
images. The app-owned source, version, and package-runtime artifacts live
together under `webcam_micro/`.

## Quick Start
Run the source entrypoint smoke test:

```bash
.venv/bin/python -m webcam_micro --smoke-test
```

Launch the prototype main window from source:

```bash
.venv/bin/python -m webcam_micro
```

Build installable package artifacts:

```bash
.venv/bin/python -m build --sdist --wheel --outdir /tmp/webcam-micro-dist
```

Launch the installed package entrypoint after installation:

```bash
webcam-micro
```

## Workflow
Follow the governed edit sequence in `AGENTS.md`.
Keep durable product rules in `SPEC.md`, active implementation sequencing in
`PLAN.md`, and landed history in `CHANGELOG.md`.

## Configuration Checkpoints
Call out the few settings or files a human must review consciously.
Prefer short explanations of what each checkpoint controls.
For most repositories, keep `devcovuser` active and add a repository-specific
custom profile on top when the repository needs its own reusable rules,
assets, or workflow additions.

The current preview runtime depends on `imageio-ffmpeg`, `pillow`, and
`ttkbootstrap` through the package-runtime lock under `webcam_micro/`.

## Docs Map
- `SPEC.md`: durable product contract and scope
- `PLAN.md`: active build roadmap and slice ordering
- `CHANGELOG.md`: newest-first change history
- `AGENTS.md`: workflow contract and active policy output

## Security, Privacy, and Support
Point readers at the trust-surface docs that matter for the repository.

## License
Document the repository licensing terms here.
