# Changelog
**Doc ID:** CHANGELOG
**Doc Type:** changelog
**Project Version:** 0.0.1
**Project Stage:** prototype
**Maintenance Stance:** active
**Compatibility Policy:** forward-only
**Versioning Mode:** versioned
**Last Updated:** 2026-04-03
**DevCovenant Version:** 1.0.1b1

<!-- DEVCOV:BEGIN -->
## DevCovenant Change Logging Rules
This opening section is managed by DevCovenant for repositories that
use DevCovenant.
Add one entry for each substantive change under the current version header.
Keep entries newest-first and record dates in ISO format (`YYYY-MM-DD`).
Each entry must include Change/Why/Impact summary lines with action verbs.
Example:
```
## Version 1.2.3

- 2026-01-23:
  Change: Fixed null-pointer crash in invoice import.
  Why: Production job failed when optional contact data was missing.
  Impact: Imports complete for records with partial contact details.
  Files:
  billing/imports/parser.py
  billing/imports/test_parser.py
  docs/imports.md
  Long paths should be wrapped with a trailing \
  backslash and continued on the next indented line.
  Example:
  services/customer/contact/normalization/\
    fallback_rules.py

- 2026-01-22:
  Change: Fixed duplicate email notifications on retry.
  Why: Retry worker re-enqueued already-confirmed notification events.
  Impact: Users receive one email per successful notification event.
  Files:
  notifications/worker.py
  notifications/retry.py
  notifications/test_retry.py

## Version 1.2.2

- 2026-01-21:
  Change: Added initial release for invoice import and notification flow.
  Why: Defined a first production-ready baseline for billing automation.
  Impact: Teams can import invoices and send notifications end-to-end.
  Files:
  billing/imports/parser.py
  notifications/worker.py
  CHANGELOG.md
```
<!-- DEVCOV:END -->

## Log changes here

## Version 0.0.1

- 2026-04-03:
  Change: Completed the Stage 3 preview-first shell with the governed main
    window layout, separate controls window, and the FFmpeg wording fix in
    the durable docs.
  Why: Aligned the prototype with the real menu-and-toolbar shell promised by
    the
    spec while keeping the docs truthful about the active FFmpeg preview
    backend.
  Impact: `webcam-micro` now exposes the main shell contract from menus,
    toolbar, status bar, and the separate controls window, and the plan plus
    spec now describe the live FFmpeg path accurately.
  Files:
  CHANGELOG.md
  PLAN.md
  README.md
  SPEC.md
  tests/test_app.py
  tests/test_ui.py
  webcam_micro/__init__.py
  webcam_micro/app.py
  webcam_micro/ui.py

- 2026-04-03:
  Change: Enabled `raw-string-escapes`, `version-governance`, and
    `version-sync`, and defined the repo-owned `pep440` versioning and
    `forward-only` compatibility metadata in the custom profile.
  Why: Aligned policy activation with the current package version file and
    moved the repository from an unversioned display contract to a governed
    versioned baseline with an explicit forward-only compatibility stance that
    the version policies can enforce coherently.
  Impact: Updated governed docs and changelog surfaces to track
    `webcam_micro/VERSION` as version `0.0.1`, and the three requested
    policies now run on a consistent repo contract with explicit forward-only
    guidance.
  Files:
  AGENTS.md
  CHANGELOG.md
  CONTRIBUTING.md
  PLAN.md
  README.md
  SPEC.md
  devcovenant/config.yaml
  devcovenant/custom/profiles/webcam-micro/webcam-micro.yaml

## Unreleased

- 2026-04-03:
  Change: Restored the completed Stage 2 preview slice with an FFmpeg-backed
    live-view backend, explicit UI method coverage, and refreshed runtime and
    license artifacts.
  Why: Restored the earlier working low-latency preview path and aligned the
    dependency route with the governed refresh matrix after the repository
    drifted toward the interim OpenCV path.
  Impact: Restored `webcam-micro` to the fast newest-frame FFmpeg preview
    baseline, recorded Slice 2 as complete, and aligned the root plus package
    dependency artifacts with the runtime again.
  Files:
  CHANGELOG.md
  PLAN.md
  README.md
  pyproject.toml
  requirements.in
  requirements.lock
  licenses/THIRD_PARTY_LICENSES.md
  licenses/pillow-12.2.0.txt
  licenses/ttkbootstrap-1.20.2.txt
  tests/test_app.py
  tests/test_camera.py
  tests/test_ui.py
  webcam_micro/__init__.py
  webcam_micro/app.py
  webcam_micro/camera.py
  webcam_micro/licenses/THIRD_PARTY_LICENSES.md
  webcam_micro/licenses/imageio-ffmpeg-0.6.0.txt
  webcam_micro/licenses/pillow-12.2.0.txt
  webcam_micro/licenses/ttkbootstrap-1.20.2.txt
  webcam_micro/runtime-requirements.lock
  webcam_micro/ui.py

- 2026-04-03:
  Change: Reset the interrupted dirty tree to `HEAD`, upgraded the vendored
    DevCovenant payload, and restored the governed Stage 1 baseline plus the
    explicit symbol assertions required by active policy.
  Why: Clarified the mixed interrupted repo state so the current gate
    session could align to the rebuilt DevCovenant baseline and the repo's
    Stage 1 test-coverage contract.
  Impact: Aligned `webcam-micro` to the current vendored DevCovenant
    baseline with the governed Stage 1 docs, package artifacts, launcher,
    camera, and UI contracts under active checks.
  Files:
  CHANGELOG.md
  PLAN.md
  README.md
  devcovenant/README.md
  devcovenant/builtin/policies/dependency_management/\
    dependency_lock_runtime.py
  devcovenant/builtin/policies/dependency_management/\
    dependency_management.py
  devcovenant/builtin/profiles/README.md
  devcovenant/builtin/profiles/global/assets/config.yaml
  devcovenant/builtin/profiles/global/assets/devcovenant/README.yaml
  devcovenant/builtin/profiles/userproject/userproject.yaml
  devcovenant/config.yaml
  devcovenant/core/refresh_runtime.py
  devcovenant/custom/README.md
  devcovenant/custom/__init__.py
  devcovenant/custom/policies/README.md
  devcovenant/custom/policies/__init__.py
  devcovenant/custom/profiles/README.md
  devcovenant/custom/profiles/__init__.py
  devcovenant/docs/config.md
  devcovenant/docs/installation.md
  devcovenant/docs/policies.md
  devcovenant/docs/profiles.md
  devcovenant/docs/project_governance.md
  devcovenant/docs/refresh.md
  devcovenant/docs/registry.md
  devcovenant/install.py
  devcovenant/registry/registry.yaml
  licenses/THIRD_PARTY_LICENSES.md
  licenses/imageio-ffmpeg-0.6.0.txt
  licenses/pillow-12.2.0.txt
  licenses/ttkbootstrap-1.20.2.txt
  pyproject.toml
  requirements.in
  requirements.lock
  tests/test_app.py
  tests/test_camera.py
  tests/test_ui.py
  webcam_micro/__init__.py
  webcam_micro/app.py
  webcam_micro/camera.py
  webcam_micro/licenses/THIRD_PARTY_LICENSES.md
  webcam_micro/licenses/imageio-ffmpeg-0.6.0.txt
  webcam_micro/licenses/ttkbootstrap-1.20.2.txt
  webcam_micro/runtime-requirements.lock
  webcam_micro/ui.py

- 2026-04-03:
  Change: Consolidated the app-owned package, version, and package-runtime
    artifacts into the single `webcam_micro/` directory.
  Why: The repository should not split the Stage 1 app layout across both
    `webcam_micro/` and `webcam-micro/`.
  Impact: The Python package, version file, runtime lock, and package
    licenses now share one app-owned path, and tests pin that layout.
  Files:
  CHANGELOG.md
  PLAN.md
  README.md
  pyproject.toml
  devcovenant/config.yaml
  devcovenant/custom/profiles/webcam-micro/webcam-micro.yaml
  devcovenant/registry/registry.yaml
  tests/test_app.py
  webcam-micro/VERSION
  webcam-micro/licenses/README.md
  webcam-micro/licenses/THIRD_PARTY_LICENSES.md
  webcam-micro/runtime-requirements.lock
  webcam_micro/VERSION
  webcam_micro/licenses/README.md
  webcam_micro/licenses/THIRD_PARTY_LICENSES.md
  webcam_micro/runtime-requirements.lock

- 2026-04-03:
  Change: Cleaned the Stage 1 package metadata and documented the installed
    launcher path in the README quick start.
  Why: The isolated package build surfaced a deprecated manifest form, and
    Stage 1 docs needed to show the governed console entrypoint explicitly.
  Impact: The package manifest now uses the non-deprecated license field form,
    and the README shows how the installed `webcam-micro` launcher fits into
    the prototype workflow.
  Files:
  CHANGELOG.md
  README.md
  pyproject.toml

- 2026-04-03:
  Change: Built the Stage 1 application foundation with a real package
    skeleton, console entrypoint, minimal GUI shell, and backend contracts.
  Why: The prototype needed a concrete installable starting point before
    camera preview, controls, and capture work could land.
  Impact: The repository now has a `webcam_micro` package, a governed Stage 1
    architecture baseline, and tests that verify the entrypoint and
    foundation wiring.
  Files:
  CHANGELOG.md
  PLAN.md
  README.md
  SPEC.md
  pyproject.toml
  devcovenant/config.yaml
  devcovenant/custom/profiles/webcam-micro/webcam-micro.yaml
  webcam_micro/__init__.py
  webcam_micro/__main__.py
  webcam_micro/app.py
  webcam_micro/camera.py
  webcam_micro/ui.py
  tests/test_app.py
  tests/test_camera.py
  tests/test_ui.py
  webcam-micro/runtime-requirements.lock
  webcam-micro/licenses/README.md
  webcam-micro/licenses/THIRD_PARTY_LICENSES.md

- 2026-04-03:
  Change: Replaced the placeholder development plan with a concrete
    dependency-ordered roadmap for building the prototype application.
  Why: The repository needed an actionable active-work plan aligned with the
    current product spec instead of template text.
  Impact: `PLAN.md` now describes the build sequence from package foundation
    through preview, controls, capture, persistence, diagnostics, and release
    readiness.
  Files:
  CHANGELOG.md
  PLAN.md

- 2026-04-03:
  Change: Updated the product spec to define PyPI package distribution,
    all-platform support, and guvcview-style numeric settings controls.
  Why: Align the durable requirements with the intended package model and the
    required settings-widget behavior.
  Impact: The governed spec now treats PyPI publishing, all-platform runtime,
    and the slider-plus-input control contract as canonical.
  Files:
  CHANGELOG.md
  SPEC.md

- 2026-04-03:
  Change: Removed the stray ` 2`-suffixed repository directory.
  Why: Keep the tree free of accidental duplicate-named paths.
  Impact: Leave the governed repository layout cleaner and easier to trust.
  Files:
  CHANGELOG.md
  devcovenant/core 2

- 2026-04-03:
  Change: Bootstrap DevCovenant governance, generated assets, and
    bootstrap test coverage for the repository.
  Why: Record the reviewed repo setup and keep the intentional descriptor
    and scaffolding deletions in the deployed tree.
  Impact: Enable governed docs, hooks, CI, dependency artifacts, and a
    passing bootstrap workflow run for the fresh repository.
  Files:
  CHANGELOG.md
  devcovenant/builtin/profiles/global/assets/devcovenant/README.yaml
  devcovenant/custom/policies/README.md
  devcovenant/custom/policies/__init__.py
  devcovenant/registry/registry.yaml
  tests/__init__.py
  tests/test_bootstrap.py
