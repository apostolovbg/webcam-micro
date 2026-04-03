# Changelog
**Doc ID:** CHANGELOG
**Doc Type:** changelog
**Project Version:** Unversioned
**Project Stage:** prototype
**Maintenance Stance:** active
**Compatibility Policy:** unspecified
**Versioning Mode:** unversioned
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

## Unreleased

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
