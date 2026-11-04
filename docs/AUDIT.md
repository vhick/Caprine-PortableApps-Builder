# Caprine storage / build audit and evidence ledger (2026-11-04)

## Evidence from selected fork

| Evidence | Observation | Builder action |
| --- | --- | --- |
| `package.json` (bankjaneo/caprine, `facebook-migrate` branch) | TypeScript build via `tsc`, npm lockfile, Electron 43 Windows runtime, `electron-builder` packaging, MIT license, Node >=22.12, Windows x64 targets | `npm ci` on Node24; `npm run build`; `electron-builder --win --x64 --dir --publish never`; verify version tag and MIT before packaging |
| `source/config.ts` | `const store = new Store<StoreType>({schema})` and many preferences; Electron Store by default uses app `userData` | Add early `portable-paths.ts` before config-store module initializes |
| `source/index.ts` | `autoUpdater.checkForUpdatesAndNotify()` when saved `autoUpdate` true and production; `app.requestSingleInstanceLock()`; app-on-ready; `app.getPath('userData')` custom.css | Early profile redirect + disable update condition under `CAPRINE_PORTABLE_DATA`; guard concurrent portable launcher |
| `source/index.ts` | `app.getPath('downloads')` for saved blobs, native notifications, app quit/relaunch and tray behavior | Do not capture user downloads; wait for all same-binary Caprine processes to exit after a tray Quit |
| `source/menu.ts` | “Automatic Updates” toggle menu item and `app.relaunch()` menu actions | Hide update toggle for portable execution; gracefully wait out relaunch transition |
| `source/tray.ts` | User can hide window and keep the application alive | Wait until all Caprine.exe processes from this precise packaged binary have exited |
| `build/icon.png` | Authentic Caprine Windows package icon source referenced by electron-builder | Pillow generates `.ico` and 16/32/75/128 PNG variants, and same ICO embedded in AOT launcher |
| `build/after-pack.js` | Only macOS code-signing activity; returns on Windows | No macOS-specific changes required |
| `package.json` Windows `win.target` | Default upstream creates conventional NSIS installers, not unpacked release | Override via `--dir`; let shared Portable Package Builder make the PortableApps-style installer |
| `license` (repo) / `package.json` | MIT app license, author listing credits Sindre Sorhus and maintained fork bankjaneo | Preserve upstream license in independent portable package, document attribution |

Sources:
- https://github.com/bankjaneo/caprine
- https://raw.githubusercontent.com/bankjaneo/caprine/facebook-migrate/package.json
- https://raw.githubusercontent.com/bankjaneo/caprine/facebook-migrate/source/index.ts
- https://raw.githubusercontent.com/bankjaneo/caprine/facebook-migrate/source/config.ts
- https://raw.githubusercontent.com/bankjaneo/caprine/facebook-migrate/source/menu.ts
- https://raw.githubusercontent.com/bankjaneo/caprine/facebook-migrate/source/tray.ts
- https://raw.githubusercontent.com/vhick/Portable-Package-Builder/v1.0.0/action.yml
- https://raw.githubusercontent.com/vhick/Portable-Package-Builder/v1.0.0/scripts/common.ps1
- https://raw.githubusercontent.com/vhick/Portable-Package-Builder/v1.0.0/nsis/community-installer.nsi
- https://raw.githubusercontent.com/vhick/portable-release-publisher/v1.1.1/action.yml
- https://raw.githubusercontent.com/vhick/portable-release-publisher/v1.1.1/scripts/publish.py

## Scoped storage findings (Windows)

| Path/key | Ownership / confidence | Handling | Residual limitation |
| --- | --- | --- | --- |
| `%APPDATA%\Caprine` | Electron's default app `userData` on Windows; high confidence | Redirect `userData`; monitor only this narrowly named fallback if it did not exist before launch | Existing host-installed Caprine folder left untouched; cannot attribute new files inside it |
| `%LOCALAPPDATA%\Caprine` | Possible app-specific storage (conservative fallback, not confirmed created by this source) | Monitor if absent at session start; copy whole new app-only tree including empty dirs | Existing host path protected; no claim all new host directories are discovered |
| `%APPDATA%\Caprine\config.json` | Conventional electron-store default file under userData | Redirect via `app.setPath('userData')` before store import; actual config path depends on version and app name | Unexpected future upstream storage change causes portability validation review |
| `<PortableRoot>\Data\Profile` | Dedicated portable profile (source-level patch) | Electron userData, sessionData, logs, Chromium user-data-dir, login state and cached content | Credentials/cookies may be tied to OS account / Windows encryption |
| `<PortableRoot>\Data\TraceGuard` | Dedicated managed journal | Manifest, recovered folders, conflicts, errors and selftest logs | Locks and crashes may leave host data until next safe recovery |
| User's Downloads folder | Explicit application content requested by user | Never silently capture or delete | Downloads intentionally outside Data |
| Windows Registry `HKCU`/`HKLM` | No Caprine-specific keys confirmed from reviewed entry/config/build source | None modified by launcher; no system-wide cleanup | Windows/Electron notifications, associations, recent-use records may persist |
| `%PROGRAMDATA%`, `%TEMP%`, Windows notifications database | Shared system locations | No wholesale relocation/deletion | Not truly zero-trace, and unrecognized paths require a later evidence-led scope review |
| Auto-update downloads | `electron-updater` on conventional Windows build | Disabled for portable execution at source level | Do not use conventional upstream updater within portable package |
| Services, drivers, scheduled tasks | No Caprine-owned service/driver/task found in reviewed application source | None created | OS integration and Chromium subprocesses still exist during runtime |

## Assurance boundary

Static/source inspection and contract verification are evidence of intended behavior, not proof that a compiled Windows app works. Before user acceptance, verify Windows Actions logs: upstream TypeScript build; Electron `--dir` output; NativeAOT launcher test; TraceGuard fixture; ZIP test; NSIS install/upgrade fixture; publisher dry-run and actual release. Manually test the Messenger UI on a desktop; API changes outside this repository may affect behavior.

A `.paf.exe` built with `custom-nsis` is **an independently generated NSIS installer** named for PortableApps-style packaging. It is not the official PortableApps.com Installer and has not been submitted for certification. The pinned shared packager's current NSIS script protects `Data`, but it intentionally replaces `App` and `Other`. Avoid personal files in managed binary folders; older profiles may not support rollback without backup.
