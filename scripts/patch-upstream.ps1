param([Parameter(Mandatory)][string]$Source)
$ErrorActionPreference='Stop'
$source=(Resolve-Path -LiteralPath $Source).Path
$index=Join-Path $source 'source/index.ts'
$config=Join-Path $source 'source/config.ts'
$menu=Join-Path $source 'source/menu.ts'
foreach($p in @($index,$config,$menu)){if(-not (Test-Path -LiteralPath $p)){throw "Unexpected upstream structure: $p"}}
# Application patch runs before electron-store and before Electron's app ready event.
$bootstrap=@'
import path from 'node:path';
import process from 'node:process';
import {mkdirSync} from 'node:fs';
import {app} from 'electron';

// Source-level Electron storage redirection, not a temporary host junction.
// CAPRINE_PORTABLE_DATA is set by the compiled Windows launcher.
const portableProfile = process.env.CAPRINE_PORTABLE_DATA;
if (portableProfile) {
    if (!path.isAbsolute(portableProfile)) {
        throw new Error('Portable profile path must be absolute');
    }
    mkdirSync(portableProfile, {recursive: true});
    const logFolder = path.join(portableProfile, 'logs');
    mkdirSync(logFolder, {recursive: true});
    app.setPath('userData', portableProfile);
    app.setPath('sessionData', portableProfile);
    app.setAppLogsPath(logFolder);
    app.commandLine.appendSwitch('user-data-dir', portableProfile);
}
'@
Set-Content -LiteralPath (Join-Path $source 'source/portable-paths.ts') -Value $bootstrap -Encoding utf8
foreach($p in @($index,$config)) {
 $content=[IO.File]::ReadAllText($p)
 if($content -match "import './portable-paths';") {throw 'Already patched upstream source; do not double-patch'}
 [IO.File]::WriteAllText($p, "import './portable-paths';`n"+$content)
}
# Give the portable edition its own application/notification identity. Electron 43
# creates a Start Menu link and HKCU toast activator as soon as it registers
# interactive notifications; reusing the installed app identity could overwrite
# a conventional Caprine shortcut and CLSID registration.
$pkgFile=Join-Path $source 'package.json'
$pkg=Get-Content -LiteralPath $pkgFile -Raw -Encoding utf8 | ConvertFrom-Json
if($pkg.productName -ne 'Caprine' -or $pkg.build.appId -ne 'com.sindresorhus.caprine') {
    throw 'Unexpected Electron product identity: manual audit required before patching'
}
if($pkg.build.win.PSObject.Properties['executableName']) {
    throw 'Unexpected pre-existing executableName: review source before patching'
}
$pkg.productName='Caprine Portable'
$pkg.build.appId='com.sindresorhus.caprine.portable'
$pkg.build.win | Add-Member -NotePropertyName executableName -NotePropertyValue 'Caprine'
$pkg | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $pkgFile -Encoding utf8

$content=[IO.File]::ReadAllText($index)
$old="app.setAppUserModelId('com.sindresorhus.caprine');"
$new="app.setAppUserModelId(process.env.CAPRINE_PORTABLE_DATA ? 'com.sindresorhus.caprine.portable' : 'com.sindresorhus.caprine');"
if(-not $content.Contains($old)){throw 'Upstream AUMID initialization changed; review before packaging'}
$content=$content.Replace($old,$new)
[IO.File]::WriteAllText($index,$content)

$content=[IO.File]::ReadAllText($index)
$old="if (!is.development && config.get('autoUpdate')) {"
$new="if (!process.env.CAPRINE_PORTABLE_DATA && !is.development && config.get('autoUpdate')) {"
if(-not $content.Contains($old)){throw 'Auto-updater guard changed upstream; manual review required'}
$content=$content.Replace($old,$new)
[IO.File]::WriteAllText($index,$content)
$content=[IO.File]::ReadAllText($menu)
$old="label: 'Automatic Updates',"
if(-not $content.Contains($old)){throw 'Auto-updater menu changed upstream; manual review required'}
$content=$content.Replace($old,"label: 'Automatic Updates',`n            visible: !process.env.CAPRINE_PORTABLE_DATA,")
[IO.File]::WriteAllText($menu,$content)
Write-Host 'Portable Electron profile, session data, independent notification identity, and update guard applied.'
