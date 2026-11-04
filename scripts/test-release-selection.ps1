# Exercises the REAL PowerShell release selector without network access.
# Runs on GitHub's Windows runner before npm and .NET are installed.
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'release-selection.ps1')

$releases = @(
    [pscustomobject]@{tag_name='v2.62.0';prerelease=$false;draft=$false;target_commitish='stable-a'}
    [pscustomobject]@{tag_name='v2.62.1';prerelease=$false;draft=$false;target_commitish='stable-b'}
    [pscustomobject]@{tag_name='v2.63.0-beta.1';prerelease=$true;draft=$false;target_commitish='beta'}
    [pscustomobject]@{tag_name='v2.99.0';prerelease=$true;draft=$false;target_commitish='prerelease'}
    [pscustomobject]@{tag_name='v3.99.0';prerelease=$false;draft=$true;target_commitish='draft'}
    [pscustomobject]@{tag_name='2.61.22-arch-test';prerelease=$false;draft=$false;target_commitish='test'}
)
$selected=Select-CaprineStableRelease -ApiResponse $releases
if($selected.tag_name -ne 'v2.62.1') {throw "Latest stable regression: $($selected.tag_name)"}
$selected=Select-CaprineStableRelease -ApiResponse $releases -RequestedVersion '2.62.0'
if($selected.tag_name -ne 'v2.62.0') {throw "Explicit stable regression: $($selected.tag_name)"}
# Also test an extra wrapper layer, as REST API pipeline output can be nested.
$wrapped = ,$releases
$selected=Select-CaprineStableRelease -ApiResponse $wrapped
if($selected.tag_name -ne 'v2.62.1') {throw "Wrapped API array regression: $($selected.tag_name)"}
$failed=$false
try {Select-CaprineStableRelease -ApiResponse $releases -RequestedVersion '2.99.0' | Out-Null} catch {$failed=$true}
if(-not $failed){throw 'Prerelease was incorrectly accepted'}
$failed=$false
try {Select-CaprineStableRelease -ApiResponse $releases -RequestedVersion '2.62.4' | Out-Null} catch {$failed=$true}
if(-not $failed){throw 'Unknown stable release incorrectly accepted'}
$failed=$false
try {Select-CaprineStableRelease -ApiResponse @([pscustomobject]@{tag_name='v2.99.0';prerelease=$true;draft=$false}) | Out-Null} catch {$failed=$true}
if(-not $failed){throw 'All-prerelease response did not reject unsafe fallback'}
Write-Host 'PowerShell stable-release selector tests passed: latest, explicit, wrapped array, and failure cases.'
