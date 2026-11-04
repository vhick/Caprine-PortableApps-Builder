# Caprine PortableApps Builder changes

## r3 — GitHub Release Array Enumeration Fix

- **Observed failure:** r2 passed 7/7 static tests and integration checks on Windows, then incorrectly reported no eligible stable GitHub release during source resolution.
- **Root cause:** `Invoke-RestMethod` can emit JSON arrays as one object, and the resolver wrapped its direct output in `@(...)`, so `Where-Object` could not filter individual release objects. Microsoft documents this behavior.
- **Fix:** explicitly enumerate the API response into individual release entries; reject draft, prerelease and non-X.Y.Z tags; sort versions numerically; retain explicit version selection.
- **Regression:** the main workflow runs a real PowerShell offline fixture with latest, explicit-version, array-wrapped, prerelease, draft, and missing-version tests before compilation.
- **Diagnostics:** print release counts, and distinguish GitHub release `target_commitish` from the commit SHA verified later with `git rev-parse HEAD`.
- **Unchanged:** upstream source patch, native launcher, TraceGuard, packaging and publisher pins, ZIP/install validation and data protection.
- **Not yet verified:** complete Windows compilation, interactive Caprine runtime and installer generation; these need the next Actions run.

## r2 — Windows UTF-8 Static Test Fix

- **Fix:** all Python static test `Path.read_text()` calls specify `encoding="utf-8"`, preventing `UnicodeDecodeError` on Windows machines using `cp1252`. The failure occurred in the `Fast builder source-kit tests` step *before* Caprine compilation.
- **Fix:** packaging-only derives the original builder revision from the verified source release tag, so a source built as r1 or r2 is repackaged using the same builder revision.
- **Default:** the optional packaging-only workflow suggests package revision r3 after the r2 main workflow creates a release with r2-r2.
- **Retained:** upstream build, Electron profile patch, compiled NativeAOT launcher, TraceGuard, shared package builder v1.0.0 and shared release publisher v1.1.1.
- **Not yet verified:** Electron/Windows compile, interactive Messenger login and shared installer execution; require a successful GitHub Actions run and manual acceptance.

## r1

- Initial builder-source kit.
