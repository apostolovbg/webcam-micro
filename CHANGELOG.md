# Changelog
**Doc ID:** CHANGELOG
**Doc Type:** changelog
**Project Version:** 0.1.0b1
**Project Stage:** alpha
**Maintenance Stance:** active
**Compatibility Policy:** forward-only
**Versioning Mode:** versioned
**Last Updated:** 2026-04-05
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

## Version 0.1.0b1

- 2026-04-05:
  Change: Updated the package version to `0.1.0b1` across the source
    version file, package manifest, managed docs, and version-sensitive
    test coverage.
  Why: Aligned the published metadata and generated headers with the new
    beta prerelease version.
  Impact: Consumers, docs, and tests now read `0.1.0b1` from
    `webcam_micro/VERSION`, `pyproject.toml`, and the synced project
    headers.
  Files:
  AGENTS.md
  CHANGELOG.md
  CONTRIBUTING.md
  PLAN.md
  README.md
  SPEC.md
  pyproject.toml
  tests/test_app.py
  webcam_micro/README.md
  webcam_micro/VERSION

## Version 0.1.0a1

- 2026-04-05:
  Change: Rewrote `PLAN.md` into an implementation roadmap for the
    revised workstation-shell contract.
  Why: Aligned active implementation slices with the new
    guvcview-style control surface, dockable pane, and compact status
    bar requirements.
  Impact: Constrained upcoming work to control-family rendering,
    dock/detach behavior, shell chrome cleanup, and platform
    validation.
  Files:
  CHANGELOG.md
  PLAN.md

- 2026-04-05:
  Change: Amended `SPEC.md` to define the guvcview-style microscope
    workspace, detachable control surface, compact status bar, and
    LED/flicker control families.
  Why: Documented the requested GUI contract at the durable spec layer so
    future UI work stayed aligned with the preview-first control model.
  Impact: Constrained future implementation work to follow the documented
    workspace layout, type-aware control rendering, compact status bar,
    and light/flicker control requirements.
  Files:
  CHANGELOG.md
  SPEC.md

- 2026-04-05:
  Change: Marked the beta plan complete and deferred the remaining
    Windows and Linux validation until after beta publication.
  Why: Preserved truthful release notes after deciding not to block the
    beta path on unrun cross-platform tests.
  Impact: Updated `PLAN.md` and both READMEs to describe the deferred
    follow-up and the completed beta plan.
  Files:
  CHANGELOG.md
  PLAN.md
  README.md
  webcam_micro/README.md

- 2026-04-05:
  Change: Refactored the macOS camera-permission callback through a
    repo-owned adapter so Linux CI no longer imports
    `rubicon.objc.Block` at decorator time.
  Why: Preserved the optional Objective-C dependency behind the
    production boundary and made the permission test portable on
    non-macOS CI.
  Impact: Updated `webcam_micro/camera.py`, `tests/test_camera.py`,
    `tests/test_macos_permission.py`, and both READMEs so the launch
    docs match the import-safe permission path.
  Files:
  CHANGELOG.md
  README.md
  tests/test_camera.py
  tests/test_macos_permission.py
  webcam_micro/README.md
  webcam_micro/camera.py
  webcam_micro/macos_permission.py

- 2026-04-05:
  Change: Aligned the shared preview image placement so it appears
    directly after the package-facing introduction sentence in both
    READMEs.
  Why: Aligned the top-of-file layout with the requested placement and kept
    the canonical and packaged documentation in sync.
  Impact: Updated `README.md` and `webcam_micro/README.md` so the preview
    image sits above the table of contents, and recorded the doc-only
    layout change here.
  Files:
  CHANGELOG.md
  README.md
  webcam_micro/README.md

- 2026-04-05:
  Change: Clarified the beta-prep status in the user-facing READMEs and
    recorded the remaining Windows and Linux platform-validation follow-up
    in the plan.
  Why: Kept the release-prep wording truthful after the recording and
    container hardening work completed on the current runtime.
  Impact: Updated the alpha-status docs, tightened the beta follow-up
    wording in `PLAN.md`, and preserved the cross-platform validation
    handoff for the next slice.
  Files:
  CHANGELOG.md
  PLAN.md
  README.md
  webcam_micro/README.md

- 2026-04-05:
  Change: Hardened the recording save flow so the Qt shell filters
    supported containers and the session normalizes the recorded output
    path before recording starts.
  Why: Preserved the cross-platform launch flow while removing
    backend-specific recording surprises on macOS, Windows, and Linux.
  Impact: Updated the recording dialog, runtime recording validation,
    docs, plan status, and tests for runtime-supported containers.
  Files:
  CHANGELOG.md
  PLAN.md
  README.md
  tests/test_camera.py
  tests/test_ui.py
  webcam_micro/README.md
  webcam_micro/camera.py
  webcam_micro/ui.py

- 2026-04-05:
  Change: Aligned the visible camera controls into Exposure, Zoom, Source
    Info, and Actions sections and removed backend-only macOS rows from
    the control surface.
  Why: Preserved the same cross-platform control model while hiding
    AVFoundation bookkeeping from the dock.
  Impact: Updated the dock and Preferences to use sectioned control
    placement on all supported OSes, removed the macOS bookkeeping rows,
    and added docs and tests for the new grouping.
  Files:
  CHANGELOG.md
  PLAN.md
  README.md
  tests/test_camera.py
  tests/test_ui.py
  webcam_micro/README.md
  webcam_micro/camera.py
  webcam_micro/ui.py

- 2026-04-05:
  Change: Tightened the preview polling cadence so the live shell renders
    fresher frames sooner.
  Why: Reduced visible preview lag while keeping the recording path on the
    existing Qt Multimedia session flow.
  Impact: The shell now polls on a precise 60 Hz cadence, opens cameras
    with an immediate preview poll, and the docs and tests cover the lower-
    lag preview contract.
  Files:
  CHANGELOG.md
  PLAN.md
  README.md
  tests/test_ui.py
  webcam_micro/README.md
  webcam_micro/ui.py

- 2026-04-05:
  Change: Replaced the still-save prompt with silent folder-driven capture.
  Why: Aligned still capture with the configured image-folder workflow and
    removed the misleading save-as path.
  Impact: Still images now save automatically to the user's image folder,
    the plan and docs describe the quiet flow, and the UI test suite covers
    the no-dialog behavior.
  Files:
  CHANGELOG.md
  PLAN.md
  README.md
  tests/test_ui.py
  webcam_micro/README.md
  webcam_micro/ui.py

- 2026-04-05:
  Change: Aligned the Qt shell menu placement so camera session actions live
    under Camera instead of File.
  Why: Aligned the windowed command surface with SPEC's desktop menu model
    and removed the misplaced file-menu camera commands.
  Impact: Updated the File menu to exit-only, aligned Camera menu ownership
    for camera sessions, and refreshed the docs and tests around the new
    layout.
  Files:
  CHANGELOG.md
  PLAN.md
  README.md
  tests/test_ui.py
  webcam_micro/README.md
  webcam_micro/ui.py

- 2026-04-04:
  Change: Replaced the completed alpha roadmap with a beta hardening plan
    focused on layout, capture, preview, controls, and validation.
  Why: The official alpha is complete, and operational testing now defines
    the beta follow-up work rather than the original delivery path.
  Impact: PLAN now defines only the post-alpha slices that tighten the app
    toward beta while preserving the alpha history below it.
  Files:
  CHANGELOG.md
  PLAN.md

- 2026-04-04:
  Change: Fixed the runtime bootstrap so the private interpreter keeps the
    original package bridge instead of overwriting it from the runtime hop.
  Why: Prevented the macOS permission runtime from dropping `PySide6` and
    other package dependencies after the first exec into the private venv.
  Impact: Updated `webcam-micro` so the stable runtime interpreter can start
    its GUI shell on all supported OSes without losing the package imports.
  Files:
  CHANGELOG.md
  README.md
  tests/test_runtime_bootstrap.py
  webcam_micro/runtime_bootstrap.py
  webcam_micro/README.md

- 2026-04-04:
  Change: Bootstrapped a per-user runtime launcher and redirected the
    package entrypoint to it.
  Why: Enabled the app to reuse a stable interpreter identity for macOS
    camera access without giving up cross-platform launches.
  Impact: Updated the launch path so `webcam-micro` starts through
    `webcam_micro.launcher`, `webcam_micro.runtime_bootstrap`, and the
    cross-platform docs and tests on every supported OS.
  Files:
  CHANGELOG.md
  README.md
  pyproject.toml
  tests/test_app.py
  tests/test_launcher.py
  tests/test_runtime_bootstrap.py
  webcam_micro/README.md
  webcam_micro/__main__.py
  webcam_micro/app.py
  webcam_micro/launcher.py
  webcam_micro/runtime_bootstrap.py

- 2026-04-04:
  Change: Fixed the camera-permission launch path so macOS requests access
    before opening the first session.
  Why: Fixed the launch path that left macOS silent on launch, so Python
    never asked for camera access.
  Impact: Updated the Qt shell, docs, and tests so the permission prompt is
    now exercised before opening a camera.
  Files:
  README.md
  tests/test_app.py
  tests/test_camera.py
  tests/test_ui.py
  webcam_micro/README.md
  webcam_micro/app.py
  webcam_micro/camera.py
  webcam_micro/ui.py

- 2026-04-04:
  Change: Synced the alpha release notes, repo guidance, and roadmap with
    the full legal-owner notice and version source.
  Why: Kept the docs-growth surfaces aligned after the latest alpha polish
    and the `webcam_micro/VERSION` handoff.
  Impact: README, package README, governance notes, and the completed plan
    now agree on the official alpha posture.
  Files:
  AGENTS.md
  CHANGELOG.md
  CONTRIBUTING.md
  PLAN.md
  README.md
  SPEC.md
  tests/test_ui.py
  webcam_micro/README.md
  webcam_micro/ui.py

- 2026-04-04:
  Change: Aligned the alpha docs and repo notes with the version source of
    truth and the full legal-owner notice.
  Why: Kept the official alpha release documentation consistent after the
    copyright and version freeze.
  Impact: The repo notes, spec, roadmap, and package-facing docs now agree
    on `webcam_micro/VERSION` and the Black Epsilon owner line.
  Files:
  AGENTS.md
  CHANGELOG.md
  CONTRIBUTING.md
  PLAN.md
  README.md
  SPEC.md
  webcam_micro/README.md

- 2026-04-04:
  Change: Corrected the alpha shell copyright literal and expanded the UI
    contract test coverage for the nested preference and diagnostics
    callbacks.
  Why: Fixed the release-facing legal notice typo and satisfied the
    callback-name coverage expected from the Qt shell slice.
  Impact: The toolbar text now names the full legal owner, and the UI test
    suite now proves the nested preference and diagnostics callbacks stay
    visible by name.
  Files:
  CHANGELOG.md
  tests/test_ui.py
  webcam_micro/ui.py

- 2026-04-04:
  Change: Bumped the repo to official alpha and aligned the canonical
    version, stage, copyright, and public docs with the new release
    posture.
  Why: Marked the Qt Widgets baseline as the first alpha-ready cut while
    keeping the version source of truth in `webcam_micro/VERSION`.
  Impact: The repository now reports alpha status consistently across
    governance, package metadata, README surfaces, the shell chrome, and
    release notes.
  Files:
  AGENTS.md
  CHANGELOG.md
  README.md
  PLAN.md
  SPEC.md
  devcovenant/config.yaml
  devcovenant/registry/registry.yaml
  pyproject.toml
  tests/test_app.py
  tests/test_ui.py
  webcam_micro/README.md
  webcam_micro/VERSION
  webcam_micro/ui.py

## Version 0.0.1

- 2026-04-04:
  Change: Expanded the repo and package READMEs into TOC-driven microscope
    guides with the full Qt shell surface map.
  Why: Aligned the user-facing docs with the current product surfaces while
    preserving the package-facing mirror.
  Impact: Documented launch, preview, framing, capture, recording,
    presets, diagnostics, and platform notes on both readme surfaces.
  Files:
  CHANGELOG.md
  README.md
  webcam_micro/README.md

- 2026-04-04:
  Change: Updated the changelog and diagnostics UI contract test to align
    the current session with the tabbed diagnostics surface.
  Why: Preserved changelog coverage while aligning the nested-shell
    callback assertions with the diagnostics dialog source.
  Impact: The top changelog entry now covers the session-local doc/test
    follow-up without relabeling the earlier feature slice.
  Files:
  CHANGELOG.md
  tests/test_ui.py

- 2026-04-04:
  Change: Completed the tabbed diagnostics view with a recent-failures log
    and prototype exit checks for the Qt shell.
  Why: Exposed recoverable failures and release-readiness checks directly
    in the GUI so the prototype slice can be evaluated without log
    scavenging.
  Impact: Users can inspect runtime state, review recent issues, and see
    explicit exit criteria from the app instead of chasing them in logs.
  Files:
  CHANGELOG.md
  PLAN.md
  README.md
  tests/test_app.py
  tests/test_ui.py
  webcam_micro/README.md
  webcam_micro/app.py
  webcam_micro/ui.py

- 2026-04-04:
  Change: Added a tabbed diagnostics dialog with a recent-failures log and
    prototype exit checks, and tightened the release-readiness contract
    around the Qt shell.
  Why: Finished the diagnostics and package-release readiness slice so the
    prototype can surface recoverable failures and explicit exit criteria.
  Impact: Users can inspect runtime state, recent issues, and release
    readiness from the GUI, while the repo now documents the active exit
    checks alongside the Qt baseline.
  Files:
  CHANGELOG.md
  PLAN.md
  README.md
  tests/test_app.py
  tests/test_ui.py
  webcam_micro/README.md
  webcam_micro/app.py
  webcam_micro/ui.py

- 2026-04-04:
  Change: Added named preset save and recall controls to the Qt
    preferences dialog and persisted the current preset with the rest of
    the workstation state.
  Why: Finished the persistence, defaults, and presets slice so repeated
    microscope setups can be captured and restored from the same shell.
  Impact: Users can store and recall named microscope states, and the
    shell now restores the selected preset alongside framing, defaults,
    shortcuts, and camera state.
  Files:
  CHANGELOG.md
  PLAN.md
  README.md
  tests/test_ui.py
  webcam_micro/README.md
  webcam_micro/ui.py

- 2026-04-04:
  Change: Added persisted workstation state, editable control defaults, and
    configurable shortcut editing for the Qt shell.
  Why: Made repeated microscope sessions recover their framing, window,
    camera, and shortcut preferences without manual reconfiguration.
  Impact: Restores selected camera and workspace layout across launches,
    lets users tune camera defaults per session, and blocks duplicate
    shortcuts before they reach the shell.
  Files:
  CHANGELOG.md
  PLAN.md
  README.md
  tests/test_ui.py
  webcam_micro/README.md
  webcam_micro/ui.py

- 2026-04-04:
  Change: Completed item 9 by persisting the image and video output folders
    across launches and by routing Qt recording through the governed
    capture-framing crop instead of saving the raw camera feed.
  Why: Aligned the working Qt workstation with the promised microscope
    capture flow so saved stills and recorded video follow the same output
    rules and remembered destinations.
  Impact: Added framed Qt recording, remembered output destinations, and
    focused headless coverage for the new output helpers so later work can
    concentrate on broader persistence, presets, and release validation.
  Files:
  CHANGELOG.md
  PLAN.md
  README.md
  tests/test_camera.py
  tests/test_ui.py
  webcam_micro/README.md
  webcam_micro/camera.py
  webcam_micro/ui.py

- 2026-04-04:
  Change: Completed the Qt workstation shell by replacing placeholder
    capture, recording, preferences, and diagnostics actions with real native
    Qt behavior and by cleaning stale active Flet references from the current
    docs and dependency-management profile.
  Why: Finished item 8 so the repo no longer describes or behaves like an
    unfinished migration baseline, and so the active shell now carries the
    intended native desktop workflow.
  Impact: Added real still-save and recording shell flows, session-level
    preferences and diagnostics dialogs, fuller fullscreen actions, and Qt-only
    current docs and config so later work can focus on persistence and output
    rules instead of migration cleanup.
  Files:
  AGENTS.md
  CHANGELOG.md
  PLAN.md
  README.md
  devcovenant/config.yaml
  devcovenant/custom/profiles/userproject/userproject.yaml
  devcovenant/registry/registry.yaml
  tests/test_app.py
  tests/test_camera.py
  tests/test_ui.py
  webcam_micro/README.md
  webcam_micro/app.py
  webcam_micro/camera.py
  webcam_micro/ui.py

- 2026-04-04:
  Change: Restored the image-wiring slice to the requested scope by removing
    the unsolicited root README and `pyproject.toml` edits and switching the
    package README image to the `main`-branch absolute GitHub raw URL.
  Why: Removed the overshoot after the earlier package-image wiring changed
    repo-level docs and package metadata beyond what was requested.
  Impact: Preserved the packaged README image as a PyPI-safe `main`-branch
    absolute URL while leaving the repo README and package metadata
    otherwise untouched.
  Files:
  CHANGELOG.md
  README.md
  pyproject.toml
  webcam_micro/README.md

- 2026-04-04:
  Change: Added the packaged webcam-micro preview image to the repository
    README and package README, and configured the missing `PySide6` license
    source override needed for governed refresh to complete.
  Why: Added the new package-owned image with the same raw GitHub packaging
    pattern DevCovenant uses, added project URL metadata for stable PyPI
    rendering, and fixed the blocking refresh complaint raised by `PySide6`.
  Impact: Shows the app preview in repository docs, keeps the packaged README
    PyPI-safe with an absolute release-stable GitHub image path, and lets the
    dependency-maintenance refresh finish under the Qt dependency set.
  Files:
  CHANGELOG.md
  README.md
  devcovenant/custom/profiles/userproject/userproject.yaml
  pyproject.toml
  webcam_micro/README.md
  webcam_micro/licenses/PySide6-6.11.0.txt
  webcam_micro/licenses/THIRD_PARTY_LICENSES.md
  webcam_micro/licenses/rubicon-objc-0.5.3.txt

- 2026-04-04:
  Change: Restored the Qt fullscreen workflow with a compact command surface
    that supports expanded and collapsed states plus safe Escape or button
    exit back to the windowed workspace.
  Why: Replaced the staged fullscreen placeholder so the native-menu Qt shell
    behaves like a microscope workstation instead of a maximized window with
    missing fullscreen controls.
  Impact: Added real fullscreen shell parity on the Qt baseline, aligned
    native menu roles more cleanly with desktop behavior, and updated the
    headless shell contract/docs to describe the new fullscreen surface.
  Files:
  CHANGELOG.md
  PLAN.md
  README.md
  tests/test_ui.py
  webcam_micro/ui.py

- 2026-04-04:
  Change: Replaced the active Flet shell foundation with a Qt Widgets
    `QMainWindow` shell and updated the repo-owned dependency targets to
    resolve the Qt runtime across the governed hash matrix.
  Why: Required native desktop menu bars and a governed shell baseline that
    matches macOS, Windows, and Linux desktop expectations without leaving
    stale wheel-platform assumptions in the dependency policy surface.
  Impact: Delivered a native-menu Qt preview and controls foundation and
    aligned the repo-owned dependency targets so future workstation slices can
    build on the Qt baseline under DevCovenant.
  Files:
  CHANGELOG.md
  PLAN.md
  README.md
  SPEC.md
  devcovenant/custom/profiles/userproject/userproject.yaml
  pyproject.toml
  tests/test_app.py
  tests/test_ui.py
  webcam_micro/__init__.py
  webcam_micro/app.py
  webcam_micro/ui.py

- 2026-04-04:
  Change: Amended the Qt migration plan to lean the backend around Qt-owned
    media and shell functionality instead of duplicating native behavior.
  Why: Clarified that the `PySide6` migration should keep repo logic focused
    on microscope-specific policy and workflow rather than rebuilding
    `QCamera`-class capabilities in parallel.
  Impact: Aligned the next slices toward a thinner app-facing backend layer
    and a more direct Qt-native preview, capture, recording, and menu model.
  Files:
  CHANGELOG.md
  PLAN.md

- 2026-04-04:
  Change: Revised `PLAN.md` to supersede the active Flet migration with a
    `PySide6` and Qt Widgets desktop migration plan.
  Why: Verified that the current Flet shell cannot satisfy the native
    desktop menu-bar requirement across macOS, Windows, and Linux.
  Impact: Reoriented the next implementation slices around a Qt Widgets
    foundation and native menu-bar parity instead of continuing the Flet
    branch.
  Files:
  CHANGELOG.md
  PLAN.md

- 2026-04-04:
  Change: Updated the package-facing `webcam_micro/README.md` mirror,
    upgraded the vendored dependency-management runtime, and generated fresh
    root and package license inventories for the Flet-based stack.
  Why: Resolved the paused docs slice's wrong package README target and
    cleared the `flet` license-refresh failure after the builtin policy fix
    landed upstream.
  Impact: Enabled governed refresh to sync package metadata from
    `webcam_micro/README.md` and materialize the `flet` license texts instead
    of failing during `gate --mid`.
  Files:
  CHANGELOG.md
  PLAN.md
  README.md
  licenses/anyio-4.13.0.txt
  licenses/build-1.4.2.txt
  licenses/certifi-2026.2.25.txt
  licenses/cfgv-3.5.0.txt
  licenses/click-8.3.2.txt
  licenses/distlib-0.4.0.txt
  licenses/filelock-3.25.2.txt
  licenses/flet-0.84.0.txt
  licenses/h11-0.16.0.txt
  licenses/httpcore-1.0.9.txt
  licenses/httpx-0.28.1.txt
  licenses/identify-2.6.18.txt
  licenses/idna-3.11.txt
  licenses/imageio-ffmpeg-0.6.0.txt
  licenses/iniconfig-2.3.0.txt
  licenses/msgpack-1.1.2.txt
  licenses/nodeenv-1.10.0.txt
  licenses/oauthlib-3.3.1.txt
  licenses/packaging-26.0.txt
  licenses/pillow-12.2.0.txt
  licenses/pip-26.0.1.txt
  licenses/pip-tools-7.5.3.txt
  licenses/platformdirs-4.9.4.txt
  licenses/pluggy-1.6.0.txt
  licenses/pre_commit-4.5.1.txt
  licenses/PyYAML-6.0.3.txt
  licenses/Pygments-2.20.0.txt
  licenses/pyproject_hooks-1.2.0.txt
  licenses/pytest-9.0.2.txt
  licenses/python-discovery-1.2.1.txt
  licenses/repath-0.9.0.txt
  licenses/rubicon-objc-0.5.3.txt
  licenses/semver-3.0.4.txt
  licenses/setuptools-82.0.1.txt
  licenses/six-1.17.0.txt
  licenses/THIRD_PARTY_LICENSES.md
  licenses/virtualenv-21.2.0.txt
  licenses/wheel-0.46.3.txt
  pyproject.toml
  tests/test_app.py
  tests/test_bootstrap.py
  webcam_micro/README.md
  webcam_micro/licenses/flet-0.84.0.txt
  webcam_micro/licenses/imageio-ffmpeg-0.6.0.txt
  webcam_micro/licenses/pillow-12.2.0.txt
  webcam_micro/licenses/rubicon-objc-0.5.3.txt
  webcam_micro/licenses/THIRD_PARTY_LICENSES.md

- 2026-04-04:
  Change: Replaced the Tk shell baseline with the first Flet rewrite slice
    and refreshed the governed dependency surfaces for the new GUI runtime.
  Why: Aligned the prototype, PLAN.md, and SPEC.md with the two-slice Flet
    migration and removed stale shell vocabulary from the current contract.
  Impact: Preserved live preview, framing, fullscreen, and typed camera
    controls on the Flet baseline so the second rewrite slice can finish
    shell parity and later feature work.
  Files:
  CHANGELOG.md
  PLAN.md
  README.md
  SPEC.md
  devcovenant/registry/registry.yaml
  licenses/THIRD_PARTY_LICENSES.md
  licenses/ttkbootstrap-1.20.2.txt
  pyproject.toml
  requirements.lock
  tests/test_app.py
  tests/test_ui.py
  webcam_micro/__init__.py
  webcam_micro/app.py
  webcam_micro/licenses/THIRD_PARTY_LICENSES.md
  webcam_micro/licenses/ttkbootstrap-1.20.2.txt
  webcam_micro/runtime-requirements.lock
  webcam_micro/ui.py

- 2026-04-04:
  Change: Implemented live fit/fill/crop preview framing and a detached
    fullscreen toolbar workflow for the Stage 5 shell.
  Why: Aligned the preview workspace with PLAN item 5 and the microscope
    fullscreen and framing contract already documented in SPEC.md.
  Impact: Added live framing switches, safe fullscreen exit controls, and
    tested detached-toolbar behavior without pulling capture work ahead of
    Item 6.
  Files:
  CHANGELOG.md
  PLAN.md
  README.md
  tests/test_app.py
  tests/test_ui.py
  webcam_micro/app.py
  webcam_micro/ui.py

- 2026-04-04:
  Change: Removed stray duplicate ` 2` directories left under `devcovenant`
    after earlier repo updates.
  Why: Cleaned duplicate-named directory debris before it could confuse
    future profile, docs, license, or registry reads.
  Impact: The repo tree no longer contains the extra `devcovenant/* 2`
    directories, so future work resolves only the intended live paths.
  Files:
  CHANGELOG.md

- 2026-04-04:
  Change: Upgraded the repo to the rebuilt DevCovenant core, restored the
    repo-owned `userproject` dependency surface after `upgrade`, and
    regenerated the root dependency inventory from the current managed
    environment.
  Why: Aligned the upgraded builtin profile stack with the repo's custom
    `userproject` ownership and kept the root workspace surface aware of
    `webcam_micro/runtime-requirements.lock`.
  Impact: Restored the governed root lock and license report to the updated
    `click==8.3.2` state while keeping the package-runtime dependency surface
    represented in the active policy block.
  Files:
  AGENTS.md
  CHANGELOG.md
  licenses/THIRD_PARTY_LICENSES.md
  licenses/click-8.3.1.txt
  licenses/click-8.3.2.txt
  requirements.lock

- 2026-04-04:
  Change: Migrated the repo-owned custom profile from `webcam-micro` to
    `userproject`, added a governance-gated `Build` job plus manual
    `publish.yml`, and dropped Python `3.10` support across the repo-owned
    package and workflow surfaces.
  Why: Kept repo-specific ownership on the copy-ready `userproject` profile,
    aligned release automation with validated CI artifacts, and moved the
    package baseline to a modern Python floor for 2026.
  Impact: The repo now uses a custom `userproject` profile, `CI` builds and
    uploads validated distributions after `Governance`, manual publish pulls
    those exact artifacts by CI run id, and the supported floor is now Python
    `3.11+`.
  Files:
  .github/workflows/ci.yml
  .github/workflows/publish.yml
  AGENTS.md
  CHANGELOG.md
  PLAN.md
  README.md
  devcovenant/config.yaml
  devcovenant/custom/profiles/github/assets/ci.yml
  devcovenant/custom/profiles/github/github.yaml
  devcovenant/custom/profiles/python/python.yaml
  devcovenant/custom/profiles/python/python_translator.py
  devcovenant/custom/profiles/userproject/assets/publish.yml
  devcovenant/custom/profiles/userproject/userproject.yaml
  devcovenant/custom/profiles/webcam-micro/webcam-micro.yaml
  devcovenant/registry/registry.yaml
  licenses/THIRD_PARTY_LICENSES.md
  pyproject.toml
  requirements.lock
  tests/test_app.py
  tests/test_bootstrap.py
  tests/test_release_workflows.py
  tests/devcovenant/custom/profiles/python/test_python_translator.py
  webcam_micro/runtime-requirements.lock

- 2026-04-04:
  Change: Removed accidental ` 2` and ` 3` duplicate files and folders
    from the repo tree after comparing them with their unsuffixed
    counterparts.
  Why: Cleaned Finder-style duplicate-path debris and kept the live newer
    or real copy instead of leaving empty or older shadow paths around the
    repository.
  Impact: The repo tree no longer contains stray numbered duplicates under
    `devcovenant` or the managed environment, which reduces confusion and
    avoids future accidental edits against junk copies.
  Files:
  CHANGELOG.md

- 2026-04-04:
  Change: Lowered the DevCovenant blocking threshold to `warning`,
    and excluded generated package license text from line-length checks.
  Why: Made warnings block by policy while solving the existing warning
    surface at the source instead of rewriting generated third-party license
    files by hand, and cleared stale mirrored custom-policy debris before
    reopening the gate session.
  Impact: DevCovenant now fails on warnings, the generated package license
    bundle no longer emits line-length noise, and the repo can enforce
    warning-level blocking cleanly.
  Files:
  CHANGELOG.md
  devcovenant/config.yaml
  devcovenant/custom/profiles/webcam-micro/webcam-micro.yaml
  devcovenant/registry/registry.yaml

- 2026-04-03:
  Change: Completed Item 4 with a typed camera-control surface, a real
    macOS AVFoundation control bridge through `rubicon-objc`, and
    guvcview-style numeric widgets in the separate controls window.
  Why: Exposed real backend controls through a trustworthy UI and aligned the
    prototype with the governed slider-plus-spinbox behavior for numeric
    settings.
  Impact: Added backend-driven numeric, boolean, enum, read-only, and action
    controls in the controls window, cleared invalid typed numeric values to
    blank, and exposed the macOS runtime to real camera control APIs where
    available.
  Files:
  CHANGELOG.md
  PLAN.md
  README.md
  pyproject.toml
  tests/test_app.py
  tests/test_camera.py
  tests/test_ui.py
  webcam_micro/__init__.py
  webcam_micro/app.py
  webcam_micro/camera.py
  webcam_micro/licenses/THIRD_PARTY_LICENSES.md
  webcam_micro/licenses/rubicon-objc-0.5.3.txt
  webcam_micro/runtime-requirements.lock
  webcam_micro/ui.py

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
