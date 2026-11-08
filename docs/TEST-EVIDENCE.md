# Verification evidence — 2026-11-07

## Verified in this Linux authoring environment

- SOURCE-INSPECTED: Caprine v2.62.1 upstream tagged source (GitHub raw source for package.json, TypeScript app entry/menu/config, builder configuration) and pinned shared action `action.yml` + their scripts. This does not mean every upstream dependency has been audited.
- STATIC-VALIDATED: Python bytecode compile for all scripts and tests.
- STATIC-VALIDATED: four offline unit tests passed on controlled source/PE fixtures: exact-anchor adapter, fail-closed upstream drift, PE structure/architecture rejects, ZIP extraction/CRC and retained fully empty directory trees, version and AppID consistency. **Fixtures are NOT actual compiled Caprine binaries.**
- STATIC-VALIDATED: Node.js parser accepted generated `portable-bootstrap.cjs` using `node --check`.
- STATIC-VALIDATED: GitHub Actions YAML parsed with PyYAML BaseLoader; manual `workflow_dispatch` and `windows-latest` job confirmed.

## Not tested here

- WINDOWS-COMPILED: NOT YET VERIFIED; no Windows runner or .NET SDK available in authoring environment.
- AUTOMATED-RUNTIME-TESTED: NOT YET VERIFIED; no interactive Windows Electron session.
- PortableApps root launcher launch / tray descendants: NOT YET VERIFIED.
- Profile containment, cross-drive re-login and installed-app coexistence: NOT YET VERIFIED.
- Native Windows toast notifications, click-to-open, shell shortcut and CLSID recovery after first/repeat/crash exits: NOT YET VERIFIED.
- Custom NSIS `.paf.exe` construction and real installs/upgrades/reinstalls: NOT YET VERIFIED.
- GitHub Releases publication via pinned publisher: NOT YET VERIFIED.

**Acceptance gate:** Treat this ZIP as an authored builder kit, not as a previously run or approved portable application. Run the Windows workflow and follow `docs/WINDOWS-ACCEPTANCE.md` before using a real account or claiming complete portability.
