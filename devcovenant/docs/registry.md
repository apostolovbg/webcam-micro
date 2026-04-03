# Registry
**Last Updated:** 2026-04-03
**Project Version:** 1.0.1b1

## Overview
DevCovenant uses `devcovenant/registry/` for generated state.
Some of that state is tracked in git.
Some of it is local working state that helps DevCovenant manage an open or
recent work slice.

The practical question is simple:
are you looking for the repository's saved DevCovenant setup, or are you
looking for local evidence about recent command runs?

Use the tracked registry for the saved setup.
Use the runtime registry for local working state.
Do not hand-edit generated registry files.

## Tracked Registry
`devcovenant/registry/registry.yaml` is the tracked registry.
It stores things such as:
1. the active policy settings DevCovenant resolved
2. project-governance state
3. the active profile inventory
4. managed-doc and generation state
5. the resolved workflow definition
6. tracked inventory information used for debugging and audits

Tracked-registry changes are normal when you change profiles, policy settings,
managed docs, workflow generation, packaging inputs, or other DevCovenant-owned
setup.
That is not noise by itself.
It is often the recorded result of a real repository change.
That project-governance state includes identity fields such as
`project_name`, `project_description`, `project_version`, and
`copyright_notice`, so registry diffs can be the expected result of changing
how managed docs and license text are rendered.

The tracked registry also records the resolved workflow definition.
That includes:
- the reserved anchors `start`, `mid`, and `end`
- the declared runs from active profiles
- the run order DevCovenant must enforce
- freshness and recording settings for those runs

If active profiles contribute workflow fragments or generated-file inputs, the
tracked registry records the resolved inputs that later render into generated
files such as `.gitignore`, `.pre-commit-config.yaml`, and
`.github/workflows/ci.yml` when a CI-owner profile is active.
That includes generated values such as `devcov_core_paths` and profile-owned
CI fragments, plus declared policy runtime actions and policy commands such as
`changelog-coverage reset-baseline`, so registry diffs often reflect real
scan-boundary, command-surface, or workflow input changes.
Policy script and descriptor changes also refresh the tracked hash for the
affected policy entry, so registry diffs can be the expected result of a
policy implementation change even when the generated workflow shape stays the
same.
The same applies to policy-resolved metadata such as
`dependency-management.surfaces`: when profile or config overlays change those
surface declarations, the tracked registry records the new resolved lock
paths, dependency selectors, artifact targets, and hash-target settings that
later drive lock refresh behavior.
The same rule applies to `version-sync`: the tracked registry records the
resolved version source file, role extractors, and role targets that define
which docs, changelog files, and package manifests must stay synchronized.
Those dependency selectors stay repo-relative and exact in the tracked
registry; DevCovenant does not silently widen a declared `requirements.in`
entry into a basename match for profile asset templates or other same-name
files elsewhere in the tree.
That includes non-hash surfaces too: the registry records the declared target
matrix and composed surface inputs that the shared target-aware resolver uses
in either lock mode.
Those tracked surface definitions also explain why dependency-report and
license-artifact refreshes can land next to a registry diff in the same slice:
the registry is recording the dependency surface contract that generated them.
The same tracked metadata can also capture stage-scoped managed-environment
bootstrap commands, so registry diffs are the expected result when the seeded
default stack changes how `gate --start` can prepare `.venv`.
The tracked registry can also hold policy-owned runtime state when that state
is deterministic and should travel with the repository.
For `dependency-management`, that includes per-surface input and output
fingerprints used to prove that a converged surface is still current before
DevCovenant rebuilds locks or license artifacts again.
The registry metadata also records a policy-registry input fingerprint so
startup commands can skip rebuilding the tracked policy section when the
descriptors, scripts, and effective config are unchanged.
That is why `devcovenant/registry/registry.yaml` can change when one declared
surface moves, when a repository-specific custom profile overrides
`root_workspace`, when a repository adds its own `package_runtime`, or when
DevCovenant's bundled `devcovenant_runtime` surface changes its bootstrap lock
behavior.
Tracked fingerprints must stay checkout-stable.
They should be derived from repo-relative identity plus content, not from
absolute machine-local checkout paths.
Installed operator roots such as `pipx` must not change those tracked values;
the same repo content should converge to the same tracked registry state from
source and installed command paths alike.
If evidence is inherently machine-local or session-local, it belongs under
`devcovenant/registry/runtime/` instead.
The same rule applies to rendered messages and diagnostics that talk about
tracked state: they should prefer repo-relative paths over absolute checkout
roots.

The tracked registry is also where the flat-core runtime meets generated
repository state.
Files such as `devcovenant/core/repository_paths.py`,
`devcovenant/core/tracked_registry.py`,
`devcovenant/core/workflow_support.py`, and
`devcovenant/core/gate_runtime.py` all read or write registry material, but
the rule stays the same:
tracked registry entries must describe repo-stable state, while open-session
and latest-run evidence belongs only under `devcovenant/registry/runtime/`.
That tracked state includes the packaged core inventory, so shipped files such
as `devcovenant/core/README.md` must stay aligned with the manifest recorded in
`devcovenant/registry/registry.yaml`.

## Runtime Registry
`devcovenant/registry/runtime/` stores local working state such as:
- `gate_status.json`
- `workflow_session.json`
- latest-run pointers
- session snapshot companions

This is about local command history, not the saved repository setup.
It is the part cleaned by `devcovenant clean --registry` and by the registry
portion of `devcovenant clean --all`.
The tracked registry in `devcovenant/registry/registry.yaml` is preserved.

## Gate Status And Workflow Session
`gate_status.json` records gate-stage state and the pre-commit evidence tied to
those stages.

`workflow_session.json` records the declared runs for the open session,
whether they passed, and whether the results are still fresh.

`devcovenant gate --status` reads both files so it can tell you where the work
slice stands.

The tracked counterpart to that local state is the workflow section named
`workflow_contract` in `devcovenant/registry/registry.yaml`.
That section says what the workflow should be.
The runtime registry says whether the open or last session satisfied it.

## Managed Docs And Maps
Tracked managed-doc entries record which descriptor won for each target
path and whether that doc is enabled.
They do not try to copy full rendered document bodies into the registry.

That tracked state also feeds generated files such as:
- `AGENTS.md`
- `PROFILE_MAP.md`
- `POLICY_MAP.md`

## Which Registry Should You Read?
Read `devcovenant/registry/registry.yaml` when you need to know:
- which profiles are active
- which workflow runs exist
- which managed docs are enabled
- which profile contributed a generated input
- which saved DevCovenant settings are in force

Read `devcovenant/registry/runtime/` when you need to know:
- whether a gate session is open
- whether `mid` or `end` has been satisfied
- whether workflow evidence is still fresh
- which run failed most recently
- which run-log folder belongs to the active slice

## Practical Rule
If the question is "what should the project be doing?", read the tracked
registry.
If the question is "what happened during this work slice?", read the runtime
registry and the run logs.
