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

The initial snapshot uses the sources of our naming-v69 deployment. Historical
release validation recorded 3117 backend tests passed and 846 frontend tests
passed (one skipped); these are historical results, not newly executed tests
from publishing the fork. Upstream has advanced since the 3.7.0 base.

A fresh focused run while preserving this snapshot returned 55 passed and
8 failed across file naming, artist naming, folder storage, and partial M3U
tests. Six failures are stale expectations that the shared file-name sanitizer
preserves punctuation; the deployed shared sanitizer still uses upstream's
stricter rule. Two artist tests expect superseded backslash escaping and
legacy-file identity validation. These failures are recorded, not silently
fixed or removed during a repository-backup task. The full suites were not
rerun when publishing this snapshot.

## Local checkout and private state

The maintained checkout is `/opt/data/projects/downtify/restore370`.
Its parent directory is an operations workspace, not the repository root.
Music, databases, settings, credentials, deployment archives, private repair
backups, and browser evidence must remain outside the published repository.
Built frontend assets and dependency directories are intentionally not tracked.
Creating this fork does not change the running Umbrel application.
