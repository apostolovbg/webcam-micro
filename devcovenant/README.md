# devcovenant
**Doc ID:** README
**Doc Type:** repo-readme
**Project Version:** 1.0.1b1
**Last Updated:** 2026-04-05
**DevCovenant Version:** 1.0.1b1

<!-- DEVCOV:BEGIN -->

<!-- DEVCOV:END -->

![DevCovenant banner](https://raw.githubusercontent.com/apostolovbg/devcovenant/v1.0.1b1/devcovenant/docs/banner.png)

DevCovenant is a repository governance framework.
It keeps workflow rules, policy rules, generated files, and command logs in one
place so they stay in sync.

## Overview
Use DevCovenant when a repository needs more than linting and style checks.
It is built for repositories where the expensive mistakes are procedural:
people skip steps, docs drift away from behavior, generated files go stale, and
release work becomes hard to trust.

In practice, DevCovenant gives a repository four things:

1. A required workflow.

   The normal work slice is `gate --start`, edit, `gate --mid`, `run`,
   `gate --end`.

2. Executable policy rules.

   Policies are configured in project files, shown in `AGENTS.md`, and
   enforced by the CLI instead of living only as prose.

3. Managed documents and generated files.

   DevCovenant can keep selected docs, config sections, registry files,
   workflow files, and policy blocks aligned.

4. Command logs.

   Each command writes summaries and logs so you can inspect what happened
   instead of guessing.

## Why It Exists
Repositories usually fail in ordinary ways.
A team forgets a required run.
A generated file changes after the last verified run.
A policy says one thing while the code does another.
A changelog entry misses the files that actually changed.

DevCovenant makes those failures visible and repeatable to fix.
It does that by making the workflow explicit, storing the active rule set in
project files, and writing logs for each governed command.

## Custom Governance
Built-in policies and profiles are the shipped baseline, not the boundary.
DevCovenant is designed so a repository can define its own governance model
instead of waiting for the core project to add one built-in rule at a time.

A custom governance stack can combine:

- custom policies under `devcovenant/custom/policies/`
- custom profiles under `devcovenant/custom/profiles/`
- structured metadata overlays and overrides in `devcovenant/config.yaml`
- selector-role scopes for different file families inside one policy
- translators from language profiles for language-aware checks
- autofix helpers, runtime actions, and `devcovenant policy <policy-id> \
  <command>` routines
- workflow runs, CI fragments, managed docs, and managed-environment contracts

That means DevCovenant can govern much more than lint-style rules.
A repository can encode API contracts, release evidence, generated-file
ownership, environment layouts, dependency surfaces, documentation routes,
naming conventions, support/trust docs, or stack-specific safety routines as
first-class governed behavior.

The practical split is:

- policies define and enforce rules
- profiles package reusable governance for a repository shape
- translators provide language-aware facts
- config tunes the active stack with local overlays and overrides

Customization is override-based by design:
- a same-id custom policy fully shadows the builtin policy with that id
- a same-name custom profile fully shadows the builtin profile with that name
- when a custom entry shadows a builtin one, the builtin entry is ignored

For the deeper authoring model, go straight to
[policies.md](https://github.com/apostolovbg/devcovenant/blob/v1.0.1b1/devcovenant/docs/policies.md),
[profiles.md](https://github.com/apostolovbg/devcovenant/blob/v1.0.1b1/devcovenant/docs/profiles.md), and
[config.md](https://github.com/apostolovbg/devcovenant/blob/v1.0.1b1/devcovenant/docs/config.md).

## Quick Start
For most users, the right start is an isolated machine install with `pipx`,
followed by activation inside the repository you want to govern.

```bash
pipx install devcovenant
devcovenant --version
cd your-repo
devcovenant install
# review devcovenant/config.yaml
# set install.config_reviewed: true
devcovenant deploy
# prepare the environment declared by the active profile stack
# for the seeded defaults + python stack, one manual equivalent is:
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
# gate --start can also run the declared bootstrap commands
devcovenant gate --start
# make your edits
devcovenant gate --mid
devcovenant run
devcovenant gate --end
```

What those steps mean:

1. `pipx install devcovenant` installs the CLI on your machine in its own
   application environment.

2. `devcovenant install` adds DevCovenant to the target repository and writes
   `devcovenant/config.yaml`.

3. The config review is the human decision point.

   Start with `project-governance`, `developer_mode`, and `profiles.active`.
   The seeded `devcovenant/config.yaml` is supposed to keep explanatory
   comments for that first review, so use those comments as the first
   checklist.
   For most repositories, keep the standard stack with `devcovuser` active and
   add a custom profile on top when the repository needs its own rules,
   assets, or workflow additions.
   A good starting point is copying
   `devcovenant/builtin/profiles/userproject/` to
   `devcovenant/custom/profiles/userproject/` and editing only the
   repo-specific facts there.
   Keep inherited values inherited.
   Do not restate them in the copied profile.
   Here, "inherited" means values from other active profiles.
   When a custom and builtin profile share a profile name, the custom profile
   fully shadows it and the builtin profile with that name is ignored.
   Use direct overlays only for small local exceptions.

4. `deploy` writes the managed docs, generated files, and other DevCovenant
   outputs, including dependency artifacts owned by the active surfaces.
   Repo-owned custom policies and copied custom profiles stay in place during
   that lifecycle work; the install/deploy/upgrade flow should not prune
   `devcovenant/custom/**` content that belongs to the governed repository.

5. Prepare the environment declared by the active profile stack before the
   first gate cycle.

   If you keep the seeded `defaults` + `python` stack, `deploy` materializes
   the workspace dependency artifacts and one manual equivalent is creating
   `.venv` and installing `requirements.lock`.
   On Windows, use `.venv\\Scripts\\python.exe -m pip install -r \
   requirements.lock`.
   That seeded `.venv` flow is only one starting point.
   If the repository uses a system interpreter, bench-managed environment,
   container-managed environment, or another layout, declare that environment
   first through the profile stack or metadata overlays, then prepare it.
   DevCovenant must either run from that declared managed context already or
   be able to resolve the declared interpreter path or environment root.

6. The first full gate cycle proves the reviewed setup actually works.

Use a source checkout instead of `pipx` only when you are developing
DevCovenant itself or testing unreleased changes.
In that case, work from a full source checkout and use its managed environment.
If the console script is unavailable there, use `python3 -m devcovenant ...`.
On Windows, `py -m devcovenant ...` is the common equivalent form.

## Workflow
The standard repository workflow is:

```bash
devcovenant gate --start
# edit files and clear complaints while working
devcovenant gate --mid
devcovenant run
devcovenant gate --end
```

Use the commands this way:

- `check`

  Read-only audit.
  It inspects the repository and writes logs, but it does not open or close a
  gate session.

- `gate --start`

  Opens a work session and records the starting state for the slice.

- `gate --mid`

  Required pre-run check.
  It catches hook changes and DevCovenant-managed updates before `run`.

- `run`

  Runs the declared workflow steps in order and records the results.

- `gate --end`

  Runs the closing pre-commit pass and closes the session when the required
  evidence is fresh and passing.

When a command prints `Run logs: ...`, start with `summary.txt`.
If that is not enough, inspect `tail.txt`, then `stdout.log` and `stderr.log`.
For lifecycle commands such as `install`, `deploy`, `refresh`, `undeploy`,
`uninstall`, and `upgrade`, the summary artifacts can also include phase
timing details so you can see where time went before opening the full logs.

In `engine.tests_output_mode: normal`, the declared `tests` run keeps console
output short and leaves the full child output in the run logs.

## Commands
Most operators only need a small command set day to day:

```bash
devcovenant check
devcovenant gate --status
devcovenant gate --start
devcovenant gate --mid
devcovenant run
devcovenant gate --end
devcovenant asset SPEC.md
devcovenant refresh
devcovenant deploy
devcovenant clean --all
```

Other lifecycle commands such as `upgrade`, `undeploy`, and `uninstall` are
used less often, but they follow the same logging model.
`devcovenant asset FILE.ext [OUTPUTNAME.ext]` writes a Desktop copy of a
shipped asset or managed doc template. When the optional second argument is
omitted, DevCovenant keeps the asset's original filename on the Desktop.
`--overwrite` replaces an existing Desktop target.
Exact target-path matches win over basename matches, and an ambiguous basename
inside the winning profile must be rerun as an exact target path.
Use `devcovenant --help` to see the command list and
`devcovenant asset --help` for the asset-specific syntax.
`clean --all` removes disposable build, cache, log, and runtime-registry files;
its `registry` scope cleans only `devcovenant/registry/runtime/`, not the
tracked `devcovenant/registry/registry.yaml`.

Keep machine installation and repository lifecycle separate:

- use `pipx upgrade devcovenant` when you want a newer installed CLI

- use `devcovenant upgrade` inside a repository where DevCovenant is already
  installed and active

## Configuration Checkpoints
The most important first-review settings in `devcovenant/config.yaml` are:

1. `project-governance`

   Review the project name, stage, `compatibility_policy`, and
   `versioning_mode` first.

2. `developer_mode`

   `false` for a normal repository using DevCovenant.
   `true` only when the repository is being used to develop DevCovenant itself.

3. `profiles.active`

   For most repositories, keep `devcovuser` in the stack and layer a custom
   profile on top when the repository needs its own behavior.
   The copy-ready `userproject` bootstrap template under
   `devcovenant/builtin/profiles/userproject/` is the intended starting point
   for that custom layer.

4. `paths`

   Choose where DevCovenant keeps its registry and local state files.

5. `doc_assets`

   Choose which managed docs are enabled.

6. `workflow`

   Review the pre-commit command and any skip globs.

7. `policy_state`

   Decide which configurable policies are on or off.

8. `engine.*`

   Review output mode, autofix behavior, log retention, and similar CLI
   settings.

## What DevCovenant Manages
DevCovenant can manage several kinds of repository files.
That can include:

- selected documents
- generated config sections
- policy blocks in `AGENTS.md`
- tracked registry state
- runtime registry state
- generated workflow files
- generated `.gitignore` and pre-commit files

The preservation rule is simple:
missing docs can be created, very small placeholder docs can be replaced, and
otherwise DevCovenant should only touch managed headers and managed blocks.

## Docs Map
Use the shorter map below instead of treating the README as the whole manual.

- [installation.md](https://github.com/apostolovbg/devcovenant/blob/v1.0.1b1/devcovenant/docs/installation.md)

  Install, deploy, upgrade, clean, undeploy, uninstall, and first-time setup.

- [workflow.md](https://github.com/apostolovbg/devcovenant/blob/v1.0.1b1/devcovenant/docs/workflow.md)

  Gate sequence, command order, logs, and recovery.

- [config.md](https://github.com/apostolovbg/devcovenant/blob/v1.0.1b1/devcovenant/docs/config.md)

  How to read `devcovenant/config.yaml`, including project settings,
  profile stacks, workflow settings, policy activation, and metadata overlays
  and overrides.

- [profiles.md](https://github.com/apostolovbg/devcovenant/blob/v1.0.1b1/devcovenant/docs/profiles.md)

  Built-in profiles, custom profiles, translators, workflow runs, CI
  fragments, and reusable governance stacks.

- [policies.md](https://github.com/apostolovbg/devcovenant/blob/v1.0.1b1/devcovenant/docs/policies.md)

  Built-in and custom policy authoring, selector roles, runtime actions,
  autofixers, policy commands, and version-governance adapters.

- [refresh.md](https://github.com/apostolovbg/devcovenant/blob/v1.0.1b1/devcovenant/docs/refresh.md)

  What refresh rebuilds and which files it owns.

- [architecture.md](https://github.com/apostolovbg/devcovenant/blob/v1.0.1b1/devcovenant/docs/architecture.md)

  Internal structure and major code ownership boundaries.

- [registry.md](https://github.com/apostolovbg/devcovenant/blob/v1.0.1b1/devcovenant/docs/registry.md)

  Tracked registry, runtime registry, and gate state.

- [troubleshooting.md](https://github.com/apostolovbg/devcovenant/blob/v1.0.1b1/devcovenant/docs/troubleshooting.md)

  Fast recovery paths for common failures.

## License
DevCovenant is released under the MIT License.
See [LICENSE](https://github.com/apostolovbg/devcovenant/blob/v1.0.1b1/LICENSE) and
[licenses/THIRD_PARTY_LICENSES.md](https://github.com/apostolovbg/devcovenant/blob/v1.0.1b1/licenses/THIRD_PARTY_LICENSES.md).
The published package includes the same license and compliance files under
`devcovenant/licenses/`.
