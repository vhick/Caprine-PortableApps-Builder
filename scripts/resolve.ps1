param([string]$Version='', [switch]$ForceBuild, [string]$BuilderRevision='r2', [string]$PackageRevision='r2')
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
$headers=@{'User-Agent'='CaprinePortableBuilder/1.0';'Accept'='application/vnd.github+json'}
if($env:GH_TOKEN) { $headers['Authorization']="Bearer $env:GH_TOKEN" }
# Query genuine GitHub releases rather than assuming the latest commit is stable.
$releases=@(Invoke-RestMethod -Uri 'https://api.github.com/repos/bankjaneo/caprine/releases?per_page=100' -Headers $headers)
$stable=@($releases | Where-Object { -not $_.draft -and -not $_.prerelease -and $_.tag_name -match '^v?(\d+\.\d+\.\d+)$' } |
    Sort-Object -Property @{Expression={[version]($_.tag_name -replace '^v','')}} -Descending)
if($stable.Count -eq 0) { throw 'No eligible stable GitHub release. Refusing an unverified main-branch fallback.' }
if($Version) {
  if($Version -notmatch '^v?\d+\.\d+\.\d+$'){throw 'Version must be a stable semantic version X.Y.Z'}
  $want=$Version -replace '^v',''
  $selected=$stable | Where-Object {($_.tag_name -replace '^v','') -eq $want}|Select-Object -First 1
  if(-not $selected){throw "The chosen version $Version is not a verified stable release in the latest 100 releases"}
} else { $selected=$stable[0] }
$ver=$selected.tag_name -replace '^v',''
$tag="portable-v$ver-$BuilderRevision-$PackageRevision"
$skip=$false
if(-not $ForceBuild) {
  $exists = & gh release view $tag --json tagName --jq '.tagName' 2>$null
  if($LASTEXITCODE -eq 0 -and $exists -eq $tag) {$skip=$true}
}
$dest=Join-Path $PWD 'work'
New-Item -ItemType Directory -Force -Path $dest|Out-Null
[pscustomobject]@{tag=$selected.tag_name;version=$ver;commit=$selected.target_commitish;release_tag=$tag;skip=$skip;resolved_utc=[DateTime]::UtcNow.ToString('o')}|
  ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $dest 'resolved.json') -Encoding utf8
if($env:GITHUB_OUTPUT){
  @("upstream_tag=$($selected.tag_name)","version=$ver","release_tag=$tag","skip=$($skip.ToString().ToLowerInvariant())") |
    Add-Content -LiteralPath $env:GITHUB_OUTPUT -Encoding utf8
}
Write-Host "Stable Caprine: $($selected.tag_name); release tag: $tag; skip: $skip"
