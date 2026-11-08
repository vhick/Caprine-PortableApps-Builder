# Manual acceptance checklist — NOT performed by headless GitHub Actions

Test on a real Windows 10/11 desktop, preferably a disposable test account or VM. Record Caprine upstream version, portable release tag, x64 Windows build, account type, initial host state and test results. **All below are NOT YET VERIFIED** until explicitly tested. Avoid deleting any files manually before taking snapshots.

## Basic use and profile

- [ ] Extract ZIP into a new path containing spaces and non-ASCII characters; run root `CaprinePortable.exe` from Explorer and an arbitrary current working directory.
- [ ] Confirm real Caprine window, Messenger login, sending/receiving messages, settings changes, tray hide, explicit Quit, relaunch and persistent session.
- [ ] Confirm Chrome/Electron profile directories are created only under `Data/Profile`, `Data/Session`, logs/crash dumps under `Data`. Compare user AppData/LocalAppData/LocalLow, ProgramData, TEMP, HKCU/HKLM, Start Menu before/during/after; classify Windows-managed or preexisting activity separately.
- [ ] Test `Data` with completely empty nested directories, nested nonempty folders, and profile entries. Check they survive copy, ZIP extraction, update and rollback.
- [ ] Test downloads: explicitly saved files should remain in user-chosen download destination and must not be deleted by portable cleanup.
- [ ] Close tray application using Quit/Exit; launcher must remain until full process-tree shutdown, not merely until main window hides. Check during `app.relaunch()` from mode changes.

## ShellGuard and Windows toasts

- [ ] With a prior *installed* Caprine present, create same-name preexisting Start Menu shortcut; record target/hash. Portable first run must preserve it.
- [ ] Trigger a genuine Windows toast and click to open Caprine; test reply if supported, ensure no notification loss due to portable AUMID/CLSID.
- [ ] Snapshot `%APPDATA%\Microsoft\Windows\Start Menu\Programs`, `HKCU\Software\Classes\CLSID\{E79A08F5-09E3-4F25-988A-7C0BB6096C60}`, and Windows-managed notification caches before, during and after.
- [ ] A newly produced exact-owned `.lnk` (if created) must be copied into `Data\TraceGuard\Recovered\StartMenu` and removed only after verified backup; pre-existing/ambiguous links must remain.
- [ ] New, exactly owned CLSID (if created) must have backed-up `.reg` under Data before selective cleanup. Existing/foreign/ambiguous registrations must remain.
- [ ] Test two launches, installed-app coexistence, tray close, full exit, notification activation and Explorer restart.
- [ ] Kill main process or root launcher deliberately in a **disposable VM**, then re-run after all app processes quit: inspect `pending-shellguard.json`, log and retained host state. Never clear an active process's shortcuts.
- [ ] Move portable folder/drive; ensure new launches use new `Data`, earlier host shortcuts untouched unless ownership safely proven.
- [ ] Test a link held open/locked and one altered between snapshot and recovery; originals must be retained when uncertain.
- [ ] Verify unrelated HKCU keys and Start Menu contents unchanged.

## Installer and updater

- [ ] Save the separately generated ZIP and installer SHA256; verify against publisher `SHA256SUMS.txt`.
- [ ] Execute installer in disposable Windows profile; verify destination, launcher, embedded app/resources, no installed Caprine data replaced.
- [ ] Reinstall and upgrade with a populated `Data`; verify settings/credentials and TraceGuard backups not removed.
- [ ] Attempt installation with app running; note exclusive-use behavior, do not assume NSIS silent switches work.
- [ ] Check no unexpected automatic Caprine update checks or Launch at Login Windows registration.
- [ ] Test portable ZIP upgrade with Data and rollback with matching Data backup.

## Test classification

Record each result as `MANUAL-WINDOWS-TESTED` only after you have personally observed it. `WINDOWS-COMPILED` requires real successful Windows GitHub Actions logs; `USER-CONFIRMED` requires actual user confirmation. A green headless CI is **not** evidence of notifications, COM, shell or runtime data containment.
