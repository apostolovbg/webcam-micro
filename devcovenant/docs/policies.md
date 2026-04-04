# Policies
**Last Updated:** 2026-04-04

**Project Version:** 1.0.1b1

## Overview
Policies are the named rule units in DevCovenant.
Each policy combines human-readable guidance, metadata, runtime checks, and,
when needed, explicit repair actions.

Use this page when you need to answer questions like these:
- should this behavior be a policy at all?
- should it only report problems, or should it also know how to repair them?
- should the action happen automatically, or only when a human asks for it?

Built-in engine checks such as workflow validation, integrity validation, and
structure validation are separate from repository-facing policies.
This page is about the policies a repository can enable, configure, and extend.

## What A Policy Contains
A normal policy directory contains:
- a descriptor YAML file
- a runtime check file
- optional autofix helpers
- optional assets or support files

The descriptor explains the rule and declares its metadata.
The runtime code enforces the rule.

## Custom Policies Are First-Class
Built-in policies are the shipped baseline and a library of reference patterns.
They are not the limit of what DevCovenant can govern.

A repository can define brand-new policy ids or replace builtin policies with
custom ones under `devcovenant/custom/policies/<policy-id>/`.
When a custom policy uses the same `id` as a builtin policy, the custom policy
fully shadows the builtin one, and the builtin policy with that id is
ignored.
Custom policies run through the same engine surface as builtin policies:
- the same metadata resolver
- the same check context
- the same autofix contract
- the same policy-command dispatcher
- the same translator runtime

That makes custom policy authoring the main governance-extension model.
If a repository needs endpoint contract checks, release-proof rules, deployment
preconditions, docs-map rules, generated-asset ownership, stack-specific
safety rules, or project-specific process gates, those belong in custom
policies instead of ad-hoc scripts or tribal prose.

## Metadata Is The Policy API
A policy descriptor can carry more than the common control keys such as
`id`, `severity`, `enabled`, and `auto_fix`.
Any additional YAML key becomes runtime option data after metadata resolution.

DevCovenant keeps metadata in shape:
- scalars stay scalars
- lists stay lists
- mappings stay mappings
- lists of mappings with stable `id` keys merge by `id`

Metadata then resolves through the normal precedence layers:
1. descriptor defaults
2. profile overlays
3. generated overlays
4. user overlays
5. generated overrides
6. user overrides

Policy code reads the effective result through `get_option(...)`.
That makes descriptor metadata and config overlays the real authoring API for
custom governance.
A policy can model thresholds, route groups, contract inventories,
environment commands, attestation requirements, exception lists, release
surfaces, ownership maps, or other structured rule data without inventing a
second parser.

## Turning Policies On And Tuning Them
`config.policy_state` decides which configurable policies are enabled.
Profiles and config overlays then shape how those enabled policies behave.

That gives a clear split:
- config turns a policy on or off
- profile metadata shapes how it behaves
- runtime code enforces the result

## Selector Roles And Multiple Scopes
Many policies need more than one file scope.
`selector_roles` is the standard way to declare those scope families.

For each selector role, DevCovenant can materialize:
- `<role>_globs`
- `<role>_files`
- `<role>_dirs`

`*_prefixes` and `*_suffixes` also normalize into selector globs, and roles
can be explicit in `selector_roles` or inferred from the selector keys a
policy uses.

That lets one policy define several path families without inventing custom
selection syntax.
Built-in examples include:
- `dependency` for dependency-management surfaces
- `user_facing`, `user_visible`, and `doc_quality` for documentation growth
- `watch` and `tests_watch` for change-sensitive scopes

Custom policies can declare their own roles the same way.
Examples might include `api_contract`, `release_docs`, `migration`,
`seed_data`, `schema`, or `generated_payload`.

## What Policies Can Actually Do
A policy runtime is not limited to reporting a string.
Through the standard contracts, a policy can:
- inspect the current repository snapshot and active gate-session change state
- read merged descriptor metadata plus config overrides
- share expensive analysis through run-scoped cache buckets on the check
  context
- consume translator-produced language facts instead of reparsing a language
  in every policy
- report violations with file, line, severity, and remediation details
- participate in autofix through `autofix/` helpers
- expose reusable runtime actions
- expose namespaced operator commands through declared command metadata

That range is why DevCovenant can express governance routines as well as
governance checks.
The rule can stay read-only, repairable, command-driven, or some combination
of those as long as the contract stays explicit.

## Checks, Autofix, And Commands
The boundary matters:
- checks inspect and report
- autofixers repair during autofix-enabled check flows
- explicit policy commands perform deliberate operator actions

Checks should not quietly edit files.
That keeps the CLI honest and makes side effects easier to understand.
One good example is `changelog-coverage`: it works from the active gate slice,
not from raw git history. When the top changelog version changes during an
open slice, it expects a new version section above the preserved previous top
section, and it expects the preserved pre-session top entry to stay first in
that older section instead of relabeling old entries. It tracks that
preserved entry by fingerprint, so the rule does not depend on bump wording
inside the entry text.
If you intentionally rebuild changelog history, run
`devcovenant policy changelog-coverage reset-baseline` during the open
session. That command relaxes only the preserved-old-entry requirement for the
active session. It does not relax the normal date, summary, or file-coverage
rules.

The package-facing builtin sync policies follow the same contract.
`package-doc-sync` can synchronize one or more configured `source=>target`
doc pairs, strip configured repo-only marker blocks, and rewrite repo-relative
public links for packaged docs.
`package-artifact-mirror` can keep configured file and directory mirrors
inside the shipped package synchronized from their canonical repository-root
sources.

`version-sync` is a good example of that split.
Its check path resolves the configured canonical version file and compares the
declared role targets against that value.
Its autofix path rewrites only those declared targets, such as
Project Version headers, changelog version headers, and declared package
manifest version fields.
It does not widen the scope to same-name files elsewhere in the tree.

## Translators And Language-Aware Policies
Policies do not need to embed a bespoke parser for every language they touch.
Language profiles own translator declarations, and policies can ask the shared
translator runtime for one normalized `LanguageUnit`.

A translator can provide:
- basic file identity
- identifier facts
- symbol-documentation facts
- risk facts
- test-name templates

That lets custom policies stay focused on governance logic instead of language
plumbing.
When a repository needs a new language or a lighter-weight fact path, add or
override the translator in a profile instead of duplicating parser logic
across several policies.

## Policy Runtime Actions
A policy can expose reusable runtime actions.
Those actions give policy commands and autofix flows a shared implementation
path instead of duplicating logic.

For example, dependency management can expose refresh actions that update:
- lock state
- dependency reports
- license files
- the full dependency-management output set

The managed-environment policy also exposes the selected execution
environment so other runtime code can use the same target interpreter.
It resolves one target environment, reuses it when it already matches, and
runs `managed_commands` only when the target environment is missing or invalid.
That target may be repo-local or external to the repository tree.
The seeded defaults use a local `.venv`, but repositories may instead declare
system, bench-managed, container-managed, or other tool-owned environments as
long as DevCovenant can run from that managed context or resolve the declared
interpreter path or environment root.
It does not guess hidden wrapper hops that the metadata never declared.
For Python-owned tools such as the pre-commit gate hook, execution uses
`python -m ...` through the selected interpreter instead of depending on a
console-script shim.
Command templates may use `{current_python}` / `{current_bin}` for the running
interpreter and `{managed_python}` / `{managed_bin}` / `{managed_root}` for the
selected target environment.
User-facing guidance renders those path tokens with display-safe paths, so
routine messages stay explicit without leaking machine-local absolute roots.

## Policy Commands
DevCovenant supports namespaced policy commands:

```bash
devcovenant policy <policy-id> <command>
```

That keeps policy-owned operations explicit and stops the CLI from turning into
an unrelated pile of top-level commands.
The parser and dispatcher live in
`devcovenant/core/policy_commands.py`,
`devcovenant/core/policy_runtime_actions.py`, and
`devcovenant/core/execution.py`, so policy commands run through the same
execution boundary as the rest of the CLI.

## Practical Extension Patterns
Custom policies are useful when a repository needs governance that is too
specific for a shared builtin but too important to leave in comments or shell
scripts.
Common patterns include:
- endpoint, route, or schema contract checks
- generated-spec and generated-file ownership rules
- release evidence and attestation completeness
- environment/bootstrap preconditions for custom stacks
- documentation-route and support-surface requirements
- naming, layering, or source-boundary rules that are unique to one product

The common thread is the same: if the rule depends on repository state,
structured metadata, and evidence recorded by governed commands, DevCovenant
can usually model it as a custom policy or a custom policy plus a profile.

## Dependency Management
Dependency management is one policy area, not a loose group of unrelated
scripts.
It owns dependency refresh, dependency inventory, and license/report sync
as one job.

For Python repositories, `requirements.lock` is meant to store normalized
resolution content, not environment-local pip control lines.
Refresh strips environment-specific directives from comparison and from the
written lock body so repositories keep package-source behavior in metadata and
config instead of baking it into the lock file.
Dependency-management metadata is surface-based.
It uses one typed metadata model:
- scalars stay scalars
- lists stay lists
- mappings stay mappings
- lists of mappings with stable `id` values merge by `id`

That means repositories should express one concept in one metadata shape.
Use the structured `surfaces` list only for dependency-surface declarations.
Unsupported continuation shortcuts and old flat surface keys are rejected
instead of being normalized silently.

Each surface owns:
- one `lock_file`
- its direct dependency inputs
- the dependency selectors that should trigger report/license refresh
- one `third_party_file`
- one `licenses_dir`
- optional hash-lock targets

When a direct dependency does not bundle upstream license files in installed
distribution metadata, repositories may declare
`license_source_overrides`.
Override entries are keyed by normalized package name through their `id`
field and are consulted only after installed metadata yields no license
texts.
The builtin override kind is `archive_url`, which resolves one templated
`url` and matching `member_globs` to collect license files from a tagged
source archive.
Templates may use `{package_name}`, `{normalized_name}`, and `{version}`.

That means the policy can own more than one dependency surface at once.
For example:
1. `root_workspace`
2. `package_runtime`
3. `devcovenant_runtime`

There is no special root-versus-auxiliary split anymore.
Repositories can declare additional surfaces the same way when they need them.
Exact file selectors are repo-relative exact paths, not basename matches.
Use globs or directory selectors when a surface intentionally owns a file
family instead of one declared manifest path.
Profile asset templates such as
`devcovenant/builtin/profiles/python/assets/requirements.in` are starter
assets, not live dependency inputs for lock refresh.

When one surface enables `generate_hashes`, `dependency-management refresh-all`
does not try to patch a host-local `pip-compile` result.
Instead it resolves the full configured target closure from that surface's
`hash_targets`, then writes one hash-locked result that covers those targets
or fails explicitly.
That keeps hash mode target-aware instead of GitHub-specific or
host-platform-specific.
When one managed surface consumes another managed surface's lock file,
DevCovenant still emits one flat lock for the consuming surface, but it
treats the inherited lock as an already-resolved provider surface instead of
re-solving that provider's entire package set inside the consuming surface's
target closure.
That lets `root_workspace`, `devcovenant_runtime`, and `package_runtime`
compose cleanly without forcing all three surfaces through one synthetic
union-resolution pass.
If inherited managed surfaces pin conflicting versions for the same target,
refresh fails explicitly because one flat composed lock cannot represent that
conflict safely.

The shipped defaults are:
1. `root_workspace`: hash mode
2. `package_runtime`: hash mode when enabled
3. `devcovenant_runtime`: hash mode

Most governed repositories only work directly with `root_workspace` and,
when they ship their own Python package, `package_runtime`.
`devcovenant_runtime` is DevCovenant's bundled bootstrap/runtime surface for
the package-maintained GitHub bootstrap path rather than a surface ordinary
adopters usually maintain themselves.

For the seeded Python stack, `root_workspace` starts from
`requirements.in`, and that seeded file includes the shipped
`devcovenant/runtime-requirements.lock`.
`dependency-management refresh-all` then writes the resolved
`requirements.lock` and the matching license artifacts for that surface.
If a repository also composes its own `package_runtime` into the root
workspace, the emitted `requirements.lock` still stays flat, but the
root-surface resolver treats that inherited package lock as an owned
provider surface instead of re-solving the package surface from scratch.
Resolved locks are policy-owned outputs, not starter profile assets.
For the builtin Python surfaces, the default target matrix covers supported
CPython 3.10 through 3.14 on Linux, Windows, and macOS.
Hash mode resolves against that same declared matrix and emits one
all-target result with hashes.
After a surface is converged, the policy stores tracked per-surface input and
output fingerprints.
That lets later no-change refreshes skip rebuilding the lock and the matching
license artifacts for that surface entirely.
When a surface really does need recompute, independent target closures resolve
in bounded parallel and then merge back in configured target order so the
emitted lock stays deterministic.
Tracked dependency fingerprints must stay checkout-stable.
They should come from repository-relative identities plus file content, not
from absolute local paths or machine-local runtime details.
That operator-stable identity rule also covers installed-command paths such as
`pipx`, so the same surface inputs produce the same tracked fingerprint whether
DevCovenant runs from a source checkout or from an installed operator.
Anything that only makes sense for one machine or one command run belongs
under `devcovenant/registry/runtime/**`, not in tracked registry state.

If a repository overrides one of those surfaces, do it in the profile or
config layer for that surface id instead of inventing a second metadata shape.

## Version-Governance Adapters
Version-governance adapters define how version schemes are parsed,
validated, normalized, and compared.
They are part of the supported extension model because repositories may need
stricter rules than plain string equality.
For the built-in `pep440` adapter, the format and canonical spelling still
follow PEP 440, while repository progression may reopen the same base version
with a `.devN` review line above an older final section.

## Custom Policies
Custom policies live under `devcovenant/custom/policies/<id>/` and use the
same descriptor-plus-runtime structure as built-in policies.
They may either introduce a new policy id or replace a builtin policy with the
same id.
They should keep the same boundary discipline:
- checks report
- autofixers fix
- commands run explicit operations

The directory can include:
- `<policy-id>.yaml`
- `<policy-id>.py`
- optional `autofix/*.py`
- optional assets or support files

Custom policy descriptors can define repository-specific metadata keys,
selector roles, runtime actions, and command declarations.
Those capabilities are what let a repository move from "one extra rule" to a
full governance subsystem with its own metadata, scopes, repair paths, and
operator routines.

Custom policies that inspect managed docs should expect the generated header
model for docs that opt into those headers.
Custom policies that sync package-facing docs should also keep release targets
truthful. If a packaged README rewrites repo-relative links or images, those
links should point at release-stable tagged URLs instead of a moving branch.

## Practical Rule
When policy behavior changes, update all of these together:
1. descriptor prose and metadata
2. runtime code
3. tests
4. user-facing docs when behavior changes

Keep descriptor prose, remediation messages, and policy docs aligned on
repository-relative terminology so generated outputs stay consistent.

That includes builtin dependency-maintenance behavior. The shared
`dependency-management` runtime now expands supported
`requirements.in` includes when it builds license inventories, not only
when it compiles locks, so surfaces that compose other lockfiles expose
the same dependency inventory their generated reports and license texts
already reflect. The same runtime also refreshes dependency surfaces in
provider-first order when one surface includes another surface's lock
file, so composed roots do not rebuild from stale lock inputs.

When several Python policies need the same file analysis, share that work.
Use run-scoped analysis attached to the active check context or ask a
translator for a lighter facts-only path when the full symbol model is not
needed.

That keeps policy docs readable instead of turning them into code that only the
runtime understands.
