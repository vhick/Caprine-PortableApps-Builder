# Caprine v2.62.1 upstream source audit — PORTABLEAPPS

Audit date: 2026-11-07. Evidence: publicly readable exact-tag source (links below). Latest non-prerelease version observed v2.62.1; GitHub release short commit `5403168`. Exact 40-character source SHA and npm lockfile digest are resolved by `scripts/resolve.py` during each build. No Windows runtime trace capture was performed in this analysis environment.

## Framework and build

- Source: TypeScript Electron app, npm with `package-lock.json`, Node >=22.12, `npm ci`, `npm run build` (`tsc`), `electron-builder --win --x64 --dir --publish never` for unpacked Windows files.
- Exact-tag `package.json`: Electron `43.8.6`, electron-builder `^26.18.0` and MIT license; upstream version `2.62.1` at the time of the audit. `build/icon.png` is bundled upstream artwork.
- `source/index.ts`: loads config at import time, calls `app.setAppUserModelId('com.sindresorhus.caprine')`, checks `electron-updater`, creates notifications with reply/click callbacks, manages tray and exit, saves chosen downloads in Windows Downloads.
- `source/config.ts`: `const store = new Store<StoreType>({schema})` at module initialization, so `app.setPath('userData')` must happen **before importing Caprine's index module**.
- `source/menu.ts`: original `Launch at Login` invokes `app.setLoginItemSettings` and `Automatic Updates` toggles `config.autoUpdate`; portable adapter hides both.
- Installer-only shell traces are managed by pinned shared Package Builder and must be tested separately from runtime notification traces.

## Mode-specific findings table

| Finding | Source evidence | Path/registration | Owner | NATIVE remedy | PORTABLEAPPS remedy | Data safety | Functionality tradeoff | Test | Label |
|---|---|---|---|---|---|---|---|---|---|
| electron-store initializes during module imports | `source/index.ts` imports `source/config.ts` | default `userData` (normally AppData) | Caprine/Electron | Not selected | early bootstrap sets `Data/Profile` before `require(index)` | isolated from installed profile | none intended | persistent settings after restart | SOURCE-INSPECTED |
| Chromium cookies/sessions/cache | Electron session runtime | `app.getPath('sessionData')` | Electron | Not selected | early `Data/Session` | no host profile harvest | possible Windows encryption portability limits | login/restart/drive move | SOURCE-INSPECTED; runtime NOT YET VERIFIED |
| Logs and crash reports | Electron app APIs | logs, crashDumps | Electron | Not selected | `Data/Logs`, `Data/CrashDumps` | no shared logs cleaned | none known | crash/restart/profile scan | STATIC-VALIDATED design |
| Updater checks and downloads | `source/index.ts` updater conditional | Electron update caches / install destination | Caprine/electron-updater | Not selected | bypass updater while portable; hide update menu | prevents unexpected binary overwrite | manual portable upgrade required | wait/updater menu | SOURCE-INSPECTED |
| Launch at Login entry | `source/menu.ts` | Windows per-user login integration | Caprine/Electron | Not selected | hide portable menu item, do not register | prevents unintended startup entry | automatic startup not provided | check HKCU Run/login settings | SOURCE-INSPECTED |
| AppUserModelId uses installed identity | `source/index.ts` | Windows shell AUMID | Caprine/Electron | Not selected | distinct `com.vhick.caprine.portable` and fixed toast GUID | avoids known name collision | manual toast click test | installed coexistence | SOURCE-INSPECTED; behavior NOT YET VERIFIED |
| Toast notifications may create Start Menu `.lnk` and CLSID | `source/index.ts` creates Electron Notification; Electron 43 behavior, prior runtime issue | `%APPDATA%/Microsoft/Windows/Start Menu/Programs/<Caprine*.lnk>`, HKCU Classes CLSID | Electron/Windows | Not selected | bounded exact-target ShellGuard, backups before removal, keep notifications | never remove preexisting matching name | may preserve unverified shell records | live toast + click + cleanup | SOURCE-INSPECTED + inferred shell path; NOT YET VERIFIED |
| Downloads intentionally written to Downloads | `source/index.ts` `app.getPath('downloads')` | user Downloads | Caprine/user action | Not selected | retain standard user-directed save location | never move/delete user downloads | saved files are not bundled in Data | download test | SOURCE-INSPECTED |
| Tray and relaunch | `source/index.ts`, `source/util.ts` | child processes and application single-instance state | Caprine/Electron | Not selected | root launcher waits on Windows job child set when assignable | skip shell cleanup when not verifiably shut down | launcher stays open while tray active | quit/close/relaunch/crash | SOURCE-INSPECTED + proposed behavior; NOT YET VERIFIED |
| OS credential encryption and Windows managed notification caches | Chromium/Windows | OS-protected keys/history | Windows | Not selected | do not manipulate Windows security or broad shell caches | protects operating system | machine/account move may require login | multi-account portability | DOCUMENTED LIMITATION |

**Scope:** No native-portable product was requested. The NATIVE column is deliberately “Not selected.” There is no native post-exit recovery mechanism anywhere in this kit.

## Source evidence links

- https://github.com/bankjaneo/caprine/releases/tag/v2.62.1
- https://raw.githubusercontent.com/bankjaneo/caprine/v2.62.1/package.json
- https://raw.githubusercontent.com/bankjaneo/caprine/v2.62.1/source/index.ts
- https://raw.githubusercontent.com/bankjaneo/caprine/v2.62.1/source/config.ts
- https://raw.githubusercontent.com/bankjaneo/caprine/v2.62.1/source/menu.ts
- https://raw.githubusercontent.com/bankjaneo/caprine/v2.62.1/source/util.ts
- https://raw.githubusercontent.com/bankjaneo/caprine/v2.62.1/license
- https://www.electronjs.org/docs/latest/api/app
- https://github.com/vhick/Portable-Package-Builder/blob/v1.0.0/action.yml
- https://github.com/vhick/portable-release-publisher/blob/v1.1.1/action.yml

Do not reuse v2.62.1 source assumptions after material upstream changes. `patch_caprine.py` fails if exact source anchors change.
