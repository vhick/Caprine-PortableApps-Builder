# Offline, real PowerShell regression test for the GitHub release existence check.
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'release-existence.ps1')
$tag='portable-v2.62.1-r4-r4'
if (Test-CaprinePublishedRelease -HttpStatus 404 -Response @{message='Not Found'} -ExpectedTag $tag) {
    throw 'HTTP 404 must allow a new build rather than incorrectly skipping it.'
}
if (-not (Test-CaprinePublishedRelease -HttpStatus 200 -Response @{tag_name=$tag} -ExpectedTag $tag)) {
    throw 'Existing release was not recognized.'
}
foreach ($code in @(401,403,429,500)) {
    $raised=$false
    try { Test-CaprinePublishedRelease -HttpStatus $code -Response @{message='API error'} -ExpectedTag $tag | Out-Null }
    catch { $raised=$true }
    if (-not $raised) { throw "HTTP $code must stop the workflow, not silently trigger a rebuild." }
}
$raised=$false
try { Test-CaprinePublishedRelease -HttpStatus 200 -Response @{tag_name='different-tag'} -ExpectedTag $tag | Out-Null }
catch { $raised=$true }
if (-not $raised) { throw 'A mismatched returned release must not count as success.' }
Write-Host 'Release existence tests passed: 404 new build, 200 duplicate skip, API errors fail, mismatched tag fails.'
