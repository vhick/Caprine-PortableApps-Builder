# Build, pinned actions, reproducibility, validation

## Pinned shared action checks (source-inspected)

**Package Builder:** `vhick/Portable-Package-Builder@v1.0.0` (`0112c35...` release short commit). `action.yml` verified composite Windows action exposing source-dir, output-dir, engine, running-exe, timeout-seconds, package-revision, official-tool-url, official-tool-sha256, and outputs installer-file, installer-sha256, app-id, app-version. The selected engine is `custom-nsis`; `official` is never selected. Source receives complete `work/stage/CaprinePortable` only after independently validated ZIP. Real installer name is determined from `appinfo.ini` and package revision.

**Release Publisher:** `vhick/portable-release-publisher@v1.1.1` (`cb64f86...` release short commit). `action.yml` verified composite action with `files`, `tag`, `release-title`, `tag-prefix`, `keep-releases`, `prune`, `dry-run`. The publisher accepts only ZIP or `.paf.exe`, creates/releases `SHA256SUMS.txt`, uses calling `GITHUB_TOKEN`, rejects colliding manually owned releases, and can skip already matching assets. The workflow makes explicit dry run first. Keep 3 / prune false.

The source check `scripts/check_actions.py` rejects moved tags (compared against release commit prefixes) and changed interfaces. Full immutable SHA pins are recommended when re-audited and available; current workflow remains at the explicitly requested verified pinned action **tags** and rechecks their identity before use. This limits but does not eliminate tag-mutation time-of-check/time-of-use risk.

## Exact identity

`scripts/resolve.py` discovers stable release through GitHub API with pagination, excludes drafts/prereleases and nonnumeric tags, sorts version tuples numerically, resolves the specific tag's Git SHA, clones and checks out that exact commit, and verifies `package.json` version + presence/hash of package-lock. 404 release status is expected only in the dedicated calling-repo exact-release check; upstream discovery errors fail.

`scripts/identity.py` hashes builder scripts, launcher source, workflows and tests and makes a release tag with source version, source SHA8, npm lock SHA8, builder code SHA8 and `rN`. `builder_revision` is supplied in workflow_dispatch. Existing exact publisher-owned release => skip redundant build; unrelated release at that tag => hard fail.

## CI verification stages

| Stage | What it really checks | What it does not prove |
|---|---|---|
| Offline unit tests | exact fail-closed source adapters, fake PE parser, ZIP with empty directories | real Caprine runtime |
| Source resolution | stable published tagged upstream and exact commit | upstream signature trust beyond GitHub TLS |
| npm ci + tsc | locked dependency installation, TypeScript build | successful Messenger sign-in |
| electron-builder --dir | unpacked source-built x64 binary | host-data containment |
| dotnet publish | real Windows C# launcher PE | shell guard runtime behavior |
| Stage/ZIP validation | real PE headers/architecture, layout, icon, metadata, source identity, CRC | PortableApps Platform UI integration |
| Shared custom-nsis | separate installer PE/archive hash | installer actually installed and upgraded on GUI desktop |
| Publisher dry-run + publication | package selection, hashes, draft release verification | desktop compatibility/Windows notification behavior |

## Failure/rollback

If the shared installer fails: validated ZIP remains publishable, installer step shows failure, final job deliberately fails. If the ZIP itself fails validation: nothing is published. Keep original release assets and checksum file. Source build failures fail the whole job; no stale binaries are silently substituted. Source checkout remains inside the workflow run, never an upstream fork. `windows-latest` hosted runner, no manual setup, no PAT. No artifacts are uploaded merely for intermediate staging.

For a failed upgraded application, stop the app, preserve `Data`, restore last known-good `App`/launcher and its paired Data backup when schema changes make old versions incompatible. NEVER delete `Data/TraceGuard` when changing versions.

## Versioning and offline dependency sequence

Python Pillow 11.3.0 is installed **before** the Python fixture tests (the staging module imports Pillow). The package version is `upstream.major.minor.patch.revision-number`; release identity additionally incorporates builder code and commit/lock hashes. For an installer-only failure, the ZIP-only release has the original exact tag: a retry with different/updated installer requires a new `builder_revision`, since the shared publisher deliberately rejects changed assets under an existing tag.
