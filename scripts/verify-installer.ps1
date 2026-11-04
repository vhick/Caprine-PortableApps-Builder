param([Parameter(Mandatory)][string]$Installer,[Parameter(Mandatory)][string]$Stage)
$ErrorActionPreference='Stop'
$installed=Join-Path (Get-Location).Path 'work/installer-test/CaprinePortable'
if(Test-Path $installed){throw 'Installer test directory already exists'}
$target=(Resolve-Path -LiteralPath $Installer).Path
if(-not ($target -like '*.paf.exe')){throw 'Shared packager must return its genuine .paf.exe filename'}
if(-not (Test-Path "$target.json")){throw 'Shared packager provenance report missing'}
$provenance=Get-Content -LiteralPath "$target.json" -Raw|ConvertFrom-Json
if($provenance.engine -notin @('custom-nsis','official')){throw 'Unknown shared-packager engine'}
if($provenance.file -ne $target){throw 'Shared packager output path disagrees with report'}
$actualHash=(Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant()
if($actualHash -ne $provenance.sha256){throw 'Installer SHA256 mismatch'}
# The pinned packager's custom-nsis engine is NSIS and supports /S /D=.
if($provenance.engine -ne 'custom-nsis') {
 Write-Host 'Official experimental engine: binary/provenance validated; unattended installation not proven.'
 exit 0
}
New-Item -ItemType Directory -Force (Split-Path $installed -Parent)|Out-Null
function InstallOnce {
 $p=Start-Process -FilePath $target -ArgumentList @('/S',"/D=$installed") -PassThru -Wait
 if($p.ExitCode -ne 0){throw "Shared installer silent smoke failed, exit $($p.ExitCode)"}
 if(-not (Test-Path (Join-Path $installed 'App/Caprine/Caprine.exe'))){throw 'Installed Caprine binary missing'}
 if(-not (Test-Path (Join-Path $installed 'CaprinePortable.exe'))){throw 'Installed launcher missing'}
}
InstallOnce
$persist=Join-Path $installed 'Data/TraceGuard/Recovered/Roaming/Caprine/empty/child'
New-Item -ItemType Directory -Force $persist | Out-Null
$marker=Join-Path $installed 'Data/TraceGuard/persist.txt'
Set-Content -LiteralPath $marker -Value 'DO NOT DESTROY DATA' -Encoding ascii
$obsolete=Join-Path $installed 'App/Caprine/_obsolete-binary-fixture.txt'
Set-Content -LiteralPath $obsolete -Value 'OLD APP VERSION' -Encoding ascii
InstallOnce
if(-not (Test-Path -LiteralPath $marker)){throw 'Installer damaged Data'}
if((Get-Content -LiteralPath $marker -Raw).Trim() -ne 'DO NOT DESTROY DATA'){throw 'Installer altered Data'}
if(-not (Test-Path -LiteralPath $persist -PathType Container)){throw 'Installer destroyed nested empty directory'}
if(Test-Path -LiteralPath $obsolete){throw 'Installer failed to replace obsolete App tree'}
if(Test-Path (Join-Path $installed '.__UPB_Backup')){throw 'Unfinished installer backup left after success'}
Write-Host "PASS: custom NSIS installation, upgrade cleanup, Data and empty directory preservation: $installed"
