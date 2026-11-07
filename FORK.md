# Pashque's Downtify fork

This fork preserves a customized Downtify installation and its regression tests.
The original project is https://github.com/henriquesebastiao/downtify.
Upstream attribution and the original license are preserved.

## Branches

- `main`: upstream baseline; kept separate from personal customizations.
- `pashque-custom`: customized application, based on upstream 3.7.0
  (`fbcb6179b0f358bb462f886fe52db05f2a5a1c0f`), matching our deployed
  naming-v69 application sources. This is not a rebase onto current upstream.

The customized branch includes storage/destination and exact-name handling,
source-edition and artist-credit safeguards, physical library availability,
player/collection UI changes, and backend/frontend regression tests.
These changes are a combined preservation snapshot, not an upstream-ready PR.

## Development and contributions

`origin` points to `pashque/downtify`; `upstream` points to the original project.
Fetch upstream with `git fetch upstream`. For a contribution, start a new branch
from `upstream/main` and isolate one improvement with its regression tests;
do not submit the entire customized snapshot as one pull request.
Follow `CONTRIBUTING.md` and the existing build/test commands.

The initial snapshot uses the sources of our naming-v69 deployment. Current
baseline checks recorded 3163 backend tests passed, 846 frontend tests passed
(one skipped), 15 documentation checks passed, and builds green. These results
are baseline evidence, not a claim of full-file integrity or deployment
verification. Upstream has advanced since the 3.7.0 base.

Linux download-template source values preserve valid punctuation, leading dots
and whitespace; `.hidden` remains `.hidden` in download paths. Slash and NUL are
removed, and standalone `.` and `..` components are protected against traversal.
The separate `_sanitize` helper trims whitespace and strips leading dots when used
for other filesystem names. Existing copies are accepted only after validation; conflicting known source IDs are
refused rather than destructively reused. A recorded source ID is evidence
about the file's indexed provenance, not proof that its audio is the requested
recording. Missing tag values remain unknown rather than being guessed. There
is no automatic migration of legacy filenames or indexes.

## Local checkout and private state

The maintained checkout is `/opt/data/projects/downtify/restore370`.
Its parent directory is an operations workspace, not the repository root.
Music, databases, settings, credentials, deployment archives, private repair
backups, and browser evidence must remain outside the published repository.
Built frontend assets and dependency directories are intentionally not tracked.
Creating this fork does not change the running Umbrel application.
