# Host safety, shell, trace and upgrade rules

The **profile** is redirected in-process by Electron's bootstrap before Caprine's config is imported. `Data/Profile`, `Data/Session`, `Data/Logs`, `Data/CrashDumps` reside within the extracted portable root. The regular Electron and app persistent state does not need an AppData post-exit scavenger; such a scavenger would be more dangerous to installed Caprine instances. Completely empty dirs within this tree are preserved by ZIP entries.

The compiled root launcher provides a **narrow ShellGuard** because native Windows toasts may create a new shell shortcut and portable-specific CLSID registration. Before launch, a manifest records whether the exact portable CLSID existed and SHA-256 of top-level Start Menu `.lnk` names `Caprine Portable.lnk`, `CaprinePortable.lnk` and `Caprine.lnk`. After the last verified owned job process exits, newly created shortcuts are recovered only if their resolved shortcut target equals the current internal `App/Caprine/Caprine.exe`, with no shortcut command-line arguments. A verified copy is kept at `Data/TraceGuard/Recovered/StartMenu/`; preexisting entries are untouched. Only a previously absent, exclusive portable CLSID with `LocalServer32` naming the exact internal executable may be exported to `Recovered/Registry/` before deletion. Unknown registry subkeys/values prevent deletion.

**Important:** The ShellGuard includes safe-deny branches, not a claim of complete trace elimination. If the launcher could not associate its process job, exits abnormally, or cannot prove ownership, it retains ambiguous host items, writes `Data/TraceGuard/shellguard.log`, and preserves its pending manifest. If a previous session remains unresolved and Caprine is running, it refuses to overwrite the pending manifest. No broad Windows Start Menu, registry, TEMP, AppData or ProgramData cleanup is ever attempted.

## Update procedure

1. In Caprine choose Quit/Exit. Do not mistake hiding the window in the tray for process exit.
2. Make two backups: entire `CaprinePortable/Data` and the older binaries `CaprinePortable/App` + root launcher + appinfo.ini.
3. Extract the new ZIP in a **separate temporary folder**. Check GitHub's `SHA256SUMS.txt`.
4. Copy new `App`, root `CaprinePortable.exe`, and `Other`, retaining the old root `Data` directory. Never overwrite `Data` with the ZIP's empty default directories. A safer method is to start from the new ZIP and move the existing `Data` into that newly extracted directory before first launch.
5. Run the launcher and confirm login state, windows, tray, notifications and `Data/TraceGuard` log. Do not run both copies against the same Data directory.
6. If behavior breaks, close the app, restore the old binaries and the paired Data backup if needed. Browser profile schemas may not support older versions after an upgrade; rollback without a matching Data backup is NOT assured.

## Relocation and coexistence

Always move the **whole** `CaprinePortable` directory when Caprine is closed. The launcher uses its own executable directory to find `App` and `Data`, not current working directory. Windows DPAPI-protected cookies may still require a fresh sign-in on another account/device. A stale native notification shortcut pointing at a previous drive will not be globally searched/removed; inspect `Data/TraceGuard` and Windows shortcuts manually if needed. No installed Caprine data is imported, overwritten or deleted. Pre-existing same-name Start Menu links are preserved even when their target is portable, because they may be user-created.

No automatic autostart, HKLM changes, drivers, services, scheduled tasks, bypass of Windows security, Windows-wide environment manipulation or full registry tree harvesting is included. Do not create an installed Caprine shortcut intentionally with this package identity.
