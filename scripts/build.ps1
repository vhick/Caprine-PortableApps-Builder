param([Parameter(Mandatory)][string]$Tag,[Parameter(Mandatory)][string]$Version)
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
$repo=(Get-Location).Path
$up=Join-Path $repo '_upstream'
if(Test-Path $up){throw 'Upstream folder already exists; refusing to reuse a potentially modified checkout'}
& git clone --depth 1 --single-branch --branch $Tag https://github.com/bankjaneo/caprine.git $up
if($LASTEXITCODE -ne 0){throw 'Could not retrieve pinned stable tag'}
$commit=(& git -C $up rev-parse HEAD).Trim()
if($LASTEXITCODE -ne 0 -or $commit -notmatch '^[0-9a-f]{40}$'){throw 'Could not verify upstream commit SHA'}
$package=Get-Content -LiteralPath (Join-Path $up 'package.json') -Raw | ConvertFrom-Json
if($package.version -ne $Version){throw "Upstream version mismatch: $($package.version) vs $Version"}
if($package.license -ne 'MIT'){throw 'License changed upstream; review before redistributing'}
& "$repo/scripts/patch-upstream.ps1" -Source $up
& npm ci --prefix $up --no-audit --no-fund
if($LASTEXITCODE -ne 0){throw 'npm ci failed (lockfile must be intact)'}
Push-Location $up
try {
 & npm run build
 if($LASTEXITCODE -ne 0){throw 'TypeScript build failed'}
 # electron-builder --dir creates genuine Windows unpacked binaries without an installer.
 & npx --no-install electron-builder --win --x64 --dir --publish never
 if($LASTEXITCODE -ne 0){throw 'electron-builder Windows unpacked build failed'}
} finally {Pop-Location}
$unpacked=Join-Path $up 'dist/win-unpacked'
if(-not (Test-Path -LiteralPath (Join-Path $unpacked 'Caprine.exe'))){throw 'Caprine.exe missing in unpacked output'}
& python -m pip install --disable-pip-version-check --quiet 'Pillow==11.3.0'
if($LASTEXITCODE -ne 0){throw 'Pillow icon converter installation failed'}
$icon=Join-Path $up 'build/icon.png'
$stage=Join-Path $repo 'work/staging/CaprinePortable'
$app=Join-Path $stage 'App/Caprine'
New-Item -ItemType Directory -Force -Path $app | Out-Null
Copy-Item -Path (Join-Path $unpacked '*') -Destination $app -Recurse -Force -ErrorAction Stop
# Copy the complete electron-builder win-unpacked tree.
if(-not (Test-Path (Join-Path $app 'Caprine.exe'))){throw 'App copy produced no executable'}
& python "$repo/scripts/make-icons.py" --source $icon --out (Join-Path $stage 'App/AppInfo') --launcher (Join-Path $repo 'launcher/icon.ico')
if($LASTEXITCODE -ne 0){throw 'Authentic icon generation failed'}
& dotnet publish "$repo/launcher/CaprinePortable.csproj" -c Release -r win-x64 -p:PublishAot=true -o "$repo/work/launcher"
if($LASTEXITCODE -ne 0){throw 'NativeAOT launcher compile failed'}
$launcher=Join-Path $repo 'work/launcher/CaprinePortable.exe'
if(-not (Test-Path -LiteralPath $launcher)){throw 'Native launcher missing'}
Copy-Item -LiteralPath $launcher -Destination (Join-Path $stage 'CaprinePortable.exe')
New-Item -ItemType Directory -Force -Path (Join-Path $stage 'Data'), (Join-Path $stage 'Other/Source'), (Join-Path $stage 'App/DefaultData'), (Join-Path $stage 'App/AppInfo/Launcher') | Out-Null
# PackageVersion requires exactly four numeric fields in the shared packager.
$parts=$Version.Split('.')
if($parts.Count -ne 3){throw 'Expected upstream semantic version with 3 fields'}
$pkgVersion="$Version.0"
$ini=@"
[Format]
Type=PortableApps.comFormat
Version=3.8

[Details]
Name=Caprine Portable
AppID=CaprinePortable
Publisher=Caprine contributors (bankjaneo maintained fork)
Homepage=https://github.com/bankjaneo/caprine
Category=Internet
Description=Unofficial Facebook Messenger desktop application (independent portable package)
Language=Multilingual

[License]
Shareable=true
OpenSource=true
Freeware=true
CommercialUse=true

[Version]
PackageVersion=$pkgVersion
DisplayVersion=$Version

[Control]
Start=CaprinePortable.exe
Icons=1

[Associations]
"@
Set-Content -LiteralPath (Join-Path $stage 'App/AppInfo/appinfo.ini') -Value $ini -Encoding ascii
@'
[Launch]
ProgramExecutable=App\Caprine\Caprine.exe

; Informational compatibility metadata. The compiled launcher is used at root.
; Do not launch the upstream binary directly: it bypasses Data redirection.
'@ | Set-Content -LiteralPath (Join-Path $stage 'App/AppInfo/Launcher/CaprinePortable.ini') -Encoding ascii
@"
Caprine upstream source: https://github.com/bankjaneo/caprine
Stable source tag: $Tag
Source commit: $commit
Upstream software license: MIT (see upstream license)
Builder license: MIT; independent launcher / TraceGuard
Independent PortableApps-style packaging; not an official PortableApps.com-certified release.
For full upstream license and dependency notices, see official upstream repository.
"@|Set-Content -LiteralPath (Join-Path $stage 'Other/Source/UPSTREAM.txt') -Encoding utf8
Copy-Item -LiteralPath (Join-Path $up 'license') -Destination (Join-Path $stage 'Other/Source/CAPRINE-LICENSE.txt')
Copy-Item -LiteralPath (Join-Path $repo 'work/verified-integrations.json') -Destination (Join-Path $stage 'Other/Source/verified-integrations.json')
[pscustomobject]@{tag=$Tag;version=$Version;source_commit=$commit;package_version=$pkgVersion;builder_revision='r4';built_utc=[DateTime]::UtcNow.ToString('o')}|
  ConvertTo-Json | Set-Content -LiteralPath (Join-Path $stage 'Other/Source/build-info.json') -Encoding utf8
Write-Host "Staged $stage from commit $commit"
