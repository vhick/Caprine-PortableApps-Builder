## r5 — Electron 43 toast shell integration isolation (candidate; awaiting Windows build and manual testing)

- Traced user-reported `AppData\Roaming\Microsoft\Windows\Start Menu\Programs` shortcut to Electron 43's `EnsureShortcut()` in native notification activator code, not shared NSIS packager. Also identified HKCU ToastActivator CLSID/LocalServer32 registrations.
- Scoped portable identity to `Caprine Portable` and `com.sindresorhus.caprine.portable`, keeping Windows executable `Caprine.exe` via the supported electron-builder `executableName` option.
- Added compiled `ShellTraceGuard.cs` with durable `shell-session.json`, exact-name Start Menu shortcut capture (including SHA-256 verification), pre-existing host shortcut protection, registry CLSID ownership filters, and interrupted-run recovery.
- Added Windows native-executable `--shellguard-selftest` fixture for shortcut capture, a host-name conflict, registry cleanup, and crash recovery.
- Kept v1.0.0 package builder and v1.1.1 publisher unchanged; did not duplicate installer logic.
- Existing `Caprine.lnk` created under r4 is preserved intentionally; user must inspect target before manual cleanup.
- Local static tests only; Windows compilation/interactive toast scenario **not yet verified**.

# Caprine PortableApps Builder changes

## r4 — Missing Release Exit-Code Fix

- **Observed failure:** r3 passed eight static tests and the PowerShell release-selector regression, resolved stable Caprine v2.62.1 successfully, then exited with code 1 just after reporting `skip: False`.
- **Root cause:** `gh release view` legitimately returned status 1 because the release did not yet exist. The script continued normally but did not reset `$LASTEXITCODE`; GitHub Actions' built-in `pwsh` step appends a final `exit $LASTEXITCODE` check and marked the step failed.
- **Fix:** replace the native CLI existence probe with an authenticated REST API GET. HTTP 404 means release not yet published, HTTP 200 requires an exact matching tag, and HTTP 401/403/429/5xx rejects the operation. No external process exit code is left behind.
- **Tests:** added offline PowerShell status-code regression and a source-kit static regression; main workflow executes PowerShell tests before expensive compilation.
- **Revision:** main build now uses r4-r4 release tags; packaging-only defaults to r5, while preserving original source builder revision.
- **Unchanged:** application patch, launcher/TraceGuard, shared packager v1.0.0, publisher v1.1.1, ZIP/installer validation.
- **Not yet verified:** actual Windows Electron build, compiled NativeAOT launcher, interactive Messenger functionality, and installer generation/installation.

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
