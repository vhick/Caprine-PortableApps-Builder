param([Parameter(Mandatory)][string]$SourceRelease)
$ErrorActionPreference='Stop'
if($SourceRelease -notmatch '^portable-v\d+\.\d+\.\d+-r[0-9]+-r[0-9]+$') {
 throw 'Provide an exact trusted builder release tag e.g. portable-v2.62.1-r1-r1'
}
$repo=(Get-Location).Path
$download=Join-Path $repo 'work/input'
New-Item -ItemType Directory -Force -Path $download|Out-Null
& gh release download $SourceRelease --repo $env:GITHUB_REPOSITORY --pattern '*.zip' --pattern 'SHA256SUMS.txt' --dir $download --clobber
if($LASTEXITCODE -ne 0){throw 'Could not retrieve trusted prior release ZIP/checksums'}
$zips=@(Get-ChildItem -LiteralPath $download -Filter '*.zip' -File)
if($zips.Count -ne 1){throw "Expected one verified ZIP, got $($zips.Count)"}
$checksums=Join-Path $download 'SHA256SUMS.txt'
if(-not (Test-Path $checksums)){throw 'Trusted release did not contain SHA256SUMS.txt'}
$line=@(Get-Content -LiteralPath $checksums|Where-Object {$_ -match ('^[0-9a-fA-F]{64}  '+[regex]::Escape($zips[0].Name)+'$')})
if($line.Count -ne 1){throw 'Checksum entry missing/ambiguous'}
$expected=$line[0].Substring(0,64).ToLowerInvariant()
$actual=(Get-FileHash -LiteralPath $zips[0].FullName -Algorithm SHA256).Hash.ToLowerInvariant()
if($expected -ne $actual){throw 'Prior published ZIP integrity mismatch'}
$restored=Join-Path $repo 'work/restored'
New-Item -ItemType Directory -Force $restored|Out-Null
& python -c 'import zipfile,sys; z=zipfile.ZipFile(sys.argv[1]); names=z.namelist(); assert z.testzip() is None; assert all(n.startswith("CaprinePortable/") and ".." not in n.split("/") for n in names); z.extractall(sys.argv[2])' $zips[0].FullName $restored
if($LASTEXITCODE -ne 0){throw 'Untrusted or corrupt package structure'}
$stage=Join-Path $restored 'CaprinePortable'
& "$repo/scripts/validate-stage.ps1" -Stage $stage
$ini=Join-Path $stage 'App/AppInfo/appinfo.ini'
$version=(Select-String -LiteralPath $ini -Pattern '^DisplayVersion=(\d+\.\d+\.\d+)$').Matches.Groups[1].Value
if(-not $version){throw 'Cannot determine upstream version from verified appinfo.ini'}
New-Item -ItemType Directory -Force (Join-Path $repo 'dist') | Out-Null
Copy-Item -LiteralPath $zips[0].FullName -Destination (Join-Path $repo 'dist')
if($env:GITHUB_OUTPUT) {"version=$version"|Add-Content -LiteralPath $env:GITHUB_OUTPUT -Encoding utf8}
Write-Host "Verified prior ZIP $($zips[0].Name); version $version"
