# Caprine PortableApps Builder changes

## r2 — Windows UTF-8 Static Test Fix

- **Fix:** all Python static test `Path.read_text()` calls specify `encoding="utf-8"`, preventing `UnicodeDecodeError` on Windows machines using `cp1252`. The failure occurred in the `Fast builder source-kit tests` step *before* Caprine compilation.
- **Fix:** packaging-only derives the original builder revision from the verified source release tag, so a source built as r1 or r2 is repackaged using the same builder revision.
- **Default:** the optional packaging-only workflow suggests package revision r3 after the r2 main workflow creates a release with r2-r2.
- **Retained:** upstream build, Electron profile patch, compiled NativeAOT launcher, TraceGuard, shared package builder v1.0.0 and shared release publisher v1.1.1.
- **Not yet verified:** Electron/Windows compile, interactive Messenger login and shared installer execution; require a successful GitHub Actions run and manual acceptance.

## r1

- Initial builder-source kit.
