# webcam-micro
**Doc ID:** README
**Doc Type:** repo-readme
**Project Version:** Unversioned
**Last Updated:** 2026-04-03
**DevCovenant Version:** 1.0.1b1

<!-- DEVCOV:BEGIN -->

<!-- DEVCOV:END -->

Cross-platform microscope camera application distributed as a Python package
on PyPI.

## Overview
`webcam-micro` is a preview-first microscope camera application for live
viewing, camera control, still capture, and recording.

The current prototype foundation uses `ttkbootstrap` on top of Tk for the GUI
shell and a pluggable camera-backend layer. Stage 1 ships the package
entrypoint, a minimal application shell, and a null backend while targeting an
OpenCV-backed device backend as the first concrete preview implementation.
The app-owned source, version, and package-runtime artifacts now live together
under `webcam_micro/`.

## Quick Start
Run the source entrypoint smoke test:

```bash
.venv/bin/python -m webcam_micro --smoke-test
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

## Docs Map
- `SPEC.md`: durable product contract and scope
- `PLAN.md`: active build roadmap and slice ordering
- `CHANGELOG.md`: newest-first change history
- `AGENTS.md`: workflow contract and active policy output

## Security, Privacy, and Support
Point readers at the trust-surface docs that matter for the repository.

## License
Document the repository licensing terms here.
