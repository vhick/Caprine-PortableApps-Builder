param([string]$Version='', [switch]$ForceBuild, [string]$BuilderRevision='r5', [string]$PackageRevision='r5')
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
. (Join-Path $PSScriptRoot 'release-selection.ps1')
. (Join-Path $PSScriptRoot 'release-existence.ps1')
$headers=@{'User-Agent'='CaprinePortableBuilder/1.0';'Accept'='application/vnd.github+json';'X-GitHub-Api-Version'='2022-11-28'}
if($env:GH_TOKEN) { $headers['Authorization']="Bearer $env:GH_TOKEN" }
# DO NOT wrap the Invoke-RestMethod call in @(...): GitHub JSON arrays can be
# emitted as one object. The helper explicitly enumerates and filters them.
$rawReleases=Invoke-RestMethod -Uri 'https://api.github.com/repos/bankjaneo/caprine/releases?per_page=100' -Headers $headers -TimeoutSec 45 -MaximumRetryCount 2 -RetryIntervalSec 2
$selected=Select-CaprineStableRelease -ApiResponse $rawReleases -RequestedVersion $Version
$ver=[string]$selected.tag_name -replace '^v',''
$tag="portable-v$ver-$BuilderRevision-$PackageRevision"
$skip=$false
if(-not $ForceBuild) {
  # The previous gh release view check returned 1 for a perfectly normal missing
  # release. GitHub Actions' pwsh wrapper picked up the leftover LASTEXITCODE and
  # reported failure even though the resolver had successfully resolved Caprine.
  # HTTP 404 means "not published yet"; auth, network and API errors must fail.
  $repository=[string]$env:GITHUB_REPOSITORY
  if($repository -notmatch '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$') {
    throw 'GITHUB_REPOSITORY is missing or invalid; refusing to inspect another repository'
  }
  $uri="https://api.github.com/repos/$repository/releases/tags/$([uri]::EscapeDataString($tag))"
  $statusCode=0
  $release=Invoke-RestMethod -Uri $uri -Headers $headers -Method Get -TimeoutSec 45 `
      -SkipHttpErrorCheck -StatusCodeVariable statusCode -MaximumRetryCount 2 -RetryIntervalSec 2
  $skip=Test-CaprinePublishedRelease -HttpStatus ([int]$statusCode) -Response $release -ExpectedTag $tag
}
$dest=Join-Path $PWD 'work'
New-Item -ItemType Directory -Force -Path $dest|Out-Null
# target_commitish may be the branch name, not the release's actual commit.
# The verified commit SHA is recorded in Other/Source/build-info.json after git clone.
[pscustomobject]@{tag=$selected.tag_name;version=$ver;release_target_commitish=$selected.target_commitish;release_tag=$tag;skip=$skip;resolved_utc=[DateTime]::UtcNow.ToString('o')}|
  ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $dest 'resolved.json') -Encoding utf8
if($env:GITHUB_OUTPUT){
  @("upstream_tag=$($selected.tag_name)","version=$ver","release_tag=$tag","skip=$($skip.ToString().ToLowerInvariant())") |
    Add-Content -LiteralPath $env:GITHUB_OUTPUT -Encoding utf8
}
Write-Host "Stable Caprine: $($selected.tag_name); release tag: $tag; skip: $skip"
