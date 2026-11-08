# Caprine PortableApps Builder — standalone r1

**Mode:** PORTABLEAPPS ONLY. The application is an on-demand Windows Electron client; a genuine PortableApps directory, a compiled root launcher, and a separate PortableApps-style installer are appropriate. This is **not** a native portable build and **not** official PortableApps.com certification.

**What this ZIP contains:** complete standalone builder source, executable GitHub Actions workflow, upstream release resolver, fail-closed source adapter, C# compiled launcher source, minimal native Windows ShellGuard implementation, staging/validation scripts, independent ZIP assembly, shared installer/publisher integration, controlled offline tests, documentation and attribution. It does **not** contain prebuilt Caprine binaries; CI builds from exact verified upstream tagged source after you push the kit.

**Upstream:** https://github.com/bankjaneo/caprine  
**Stable release observed during audit (2026-11-07):** v2.62.1, release commit begins `5403168`; Electron 43.8.6, TypeScript, electron-builder 26, MIT. The workflow resolves and checks the actual latest stable release on each dispatch, so do not hard-code the observed version. 

## Fast start: GitHub Desktop (no compiler on your PC)

1. On GitHub.com create an **empty new repository** such as `Caprine-PortableApps-Builder`, **not** a fork of Caprine. Choose Public or Private. Do not enable README, license or .gitignore while creating the repo.
2. Open GitHub Desktop → File → Clone Repository → URL, paste your new repository address and clone it to your preferred local folder.
3. Extract the **contents** of this builder kit ZIP directly into the cloned repository's root. The root must contain `.github/workflows/build-portableapps.yml`, `scripts/`, `launcher/` and `README.md`. Ensure Windows Explorer shows the `.github` folder; do not nest the kit folder one level deeper.
4. In GitHub Desktop check the changed files. Enter a summary such as `Add standalone Caprine PortableApps builder`, click **Commit to main**, then **Push origin**.
5. On GitHub.com open the builder repository → **Actions** → **Build and Release Caprine PortableApps** → **Run workflow**. Keep `upstream_version=latest`, `builder_revision=r1`. Manual dispatch only; there is no scheduled CI.
6. Inspect the job logs: **Resolve stable upstream**, **Apply source adapter**, **Build actual upstream**, **Build C# launcher**, **Validate ZIP**, **Generate installer**, **Publisher dry run**, **Publish**. Never infer runtime portability from green CI alone.
7. Under your builder repo's **Releases**, download the `CaprinePortable-...zip` and/or `CaprinePortable-vhick_...custom-nsis-r1.paf.exe`, plus `SHA256SUMS.txt`. Verify hashes before use. The shared publisher creates the checksums.
8. ZIP method: extract the whole `CaprinePortable` folder anywhere you can write, then double-click `CaprinePortable.exe`. Installer method: run `.paf.exe`, select a portable destination; this is a community PortableApps-style installer, not the official one. Refresh the PortableApps Menu if needed.
9. Close Caprine via its **Quit/Exit** menu and confirm the tray process exits before changing binaries. Back up `CaprinePortable/Data` before each upgrade.
10. Upgrade by replacing `App/` and the root launcher/metadata from a new ZIP while **retaining your existing Data directory**. For rollback, restore an earlier known-good application binary set and compatible Data backup. Do not copy an old ZIP's empty Data over your real profile.

## Supported build behavior

- Source mode: exact upstream stable GitHub release tag, verified by `git ls-remote`, detached checkout of commit SHA, matching `package.json` version. `package-lock.json` hash included in build identity. `npm ci` honors upstream locked dependency versions and registry-integrity checks.
- App source changes: `portable-bootstrap.cjs` executes before Caprine imports `electron-store`; it sets Electron `userData`, `sessionData`, `logs` and `crashDumps` under root `Data/`. It does not change shared APPDATA, LOCALAPPDATA or TEMP.
- Distinct identity: `com.vhick.caprine.portable` and stable toast GUID `{E79A08F5-09E3-4F25-988A-7C0BB6096C60}`. Notifications and click actions are kept active (requiring manual Windows validation).
- App updates disabled while portable: source adapter bypasses `electron-updater` in portable mode and hides the Automatic Updates and Launch at Login menu items. Upgrades are handled by the builder.
- Real launcher: C# .NET 8 WinExe, single-file, self-contained x64, compiled by GitHub-hosted Windows. Forwards CLI arguments and runs `App/Caprine/Caprine.exe` using the **launcher location**, with `CAPRINE_PORTABLE_DATA` environment set. Uses Windows Job Objects to wait for Electron child processes where possible.
- TraceGuard: **no general AppData scavenger**. Primary Caprine data is redirected before application initialization. A narrow launcher ShellGuard examines Windows Start Menu notification shortcuts with exact allowed names and recovers only *new* shortcuts whose resolved target equals the packaged `Caprine.exe`. Newly created exclusively owned CLSID registration can be backed up and selectively removed. Pre-existing state is never removed. If ownership or process lifetime cannot be verified, changes are preserved and logged.
- Windows-managed shell caches, notification database history, DPAPI-protected browser credentials, temporary OS files, explicitly saved user downloads and other external activity cannot be promised to disappear.
- Output: `CaprinePortable-<upstream>-x64-r1.zip`, `CaprinePortable-vhick_<PackageVersion>_custom-nsis-r1.paf.exe` (final exact installer filename is determined by pinned shared Package Builder). Publisher creates `SHA256SUMS.txt` in the GitHub Release.
- PackageVersion includes numeric revision as its fourth component (`2.62.1.1` for r1, `2.62.1.2` for r2) to satisfy PortableApps upgrade version ordering. The AppID uses a distinct unofficial-provider suffix `CaprinePortable-vhick` to avoid official-package identity collisions.
- Release tag includes upstream version, source commit prefix, lockfile hash prefix, builder source hash prefix and revision, e.g. `portable-v2.62.1-<commit8>-<lock8>-<builder8>-r1`. It is not based on the publisher's version.

## Required limitations and safety rules

- **Source and launcher build not verified in this environment.** The offline fixture tests are not a substitute for Windows compilation or launching Messenger. On Windows, validate sign-in, notifications, tray behavior, shell backups and the installer in a test account **before** relying on it.
- The upstream `autoUpdater` normally replaces installed apps. This portable build bypasses that feature; use manual GitHub Releases instead.
- The package is **x64 only**, not ARM64. A different target needs its own build, launcher runtime and verification.
- Native Windows toast registration may create Windows-managed traces even after the newly owned shortcut and registry records are recovered. ShellGuard intentionally does not touch global Windows notification databases, Jump Lists or another application's data.
- A process that escapes the job, a Windows user-created link indistinguishable from the same-name portable notification shortcut, or another process modifying the same registry entry can make cleanup ambiguous. In that case the launcher preserves host state and logs the reason. Do not run multiple copies of this package sharing Data.
- A moved folder cannot automatically repair shell links already left on the old path. The guard preserves ambiguous state rather than deleting it.
- Never use this kit to overwrite an installed Caprine profile. Existing installed Caprine data remains in its normal Windows profile.
- Windows account-bound browser encryption may require signing in again after moving between accounts/computers; never weaken OS credential encryption.
- This kit is not code signed. Do not bypass antivirus or Windows protection mechanisms. GitHub Actions success is not a signature or certification.
- Some resource downloads by `electron-builder`, `npm`, or Chocolatey originate from the tools' configured official ecosystems. GitHub Actions, Node/.NET, NSIS and package managers are fetched as build-time dependencies; the kit does not require local tooling.

## How to inspect the release

The publisher runs first with `dry-run: 'true'` and then `dry-run: 'false'` only after staging/ZIP validation. If the shared installer fails, the ZIP is still published, but the workflow ends **FAILED** so you notice it. `SHA256SUMS.txt` is auto-published by the verified shared Release Publisher. If the same exact managed release is already present, the workflow skips rebuilding. A conflicting/manual release with the same tag is a hard error.

Full details: `docs/AUDIT.md`, `docs/WINDOWS-ACCEPTANCE.md`, `docs/SAFETY-AND-UPGRADES.md`, `docs/BUILD-VERIFY.md`.
