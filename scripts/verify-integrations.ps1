$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
# Verify EXACT pinned tag + action contracts before downloading/compiling upstream.
$actions=@(
 @{owner='vhick'; repo='Portable-Package-Builder'; tag='v1.0.0'; expectedInputs=@('source-dir','output-dir','engine','running-exe','timeout-seconds','package-revision','official-tool-url','official-tool-sha256'); expectedOutputs=@('installer-file','installer-sha256','app-id','app-version')},
 @{owner='vhick'; repo='portable-release-publisher'; tag='v1.1.1'; expectedInputs=@('files','tag','release-title','tag-prefix','keep-releases','prune','dry-run'); expectedOutputs=@()}
)
$checks=@()
foreach($action in $actions){
  $address="https://github.com/$($action.owner)/$($action.repo).git"
  $refs=@(& git ls-remote --tags $address "refs/tags/$($action.tag)" "refs/tags/$($action.tag)^{}")
  if($LASTEXITCODE -ne 0 -or $refs.Count -eq 0){throw "Pinned action tag missing: $address@$($action.tag)"}
  $peeled=@($refs | Where-Object {$_ -match '\^\{\}$'})
  $sha=if($peeled.Count){($peeled[0] -split '\s+')[0]}else{($refs[0] -split '\s+')[0]}
  if($sha -notmatch '^[0-9a-f]{40}$'){throw "Invalid resolved commit SHA for $address"}
  $url="https://raw.githubusercontent.com/$($action.owner)/$($action.repo)/$($action.tag)/action.yml"
  $body=(Invoke-WebRequest -Uri $url -Headers @{'User-Agent'='CaprinePortableBuilder/1.0'}).Content
  if($body -notmatch '(?m)^\s*using:\s*composite\s*$'){throw "Expected composite action: $url"}
  foreach($input in $action.expectedInputs){
    if($body -notmatch "(?m)^  $([regex]::Escape($input)):\s*$"){
       throw "Pinned action contract changed: required input $input missing in $url"
    }
  }
  foreach($output in $action.expectedOutputs){
    if($body -notmatch "(?m)^  $([regex]::Escape($output)):\s*$"){
      throw "Pinned action contract changed: required output $output missing in $url"
    }
  }
  $checks += [pscustomobject]@{ repository="$($action.owner)/$($action.repo)"; tag=$action.tag; resolved_commit=$sha; action_sha256=([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($body))).ToLowerInvariant()); inputs=$action.expectedInputs }
}
New-Item -ItemType Directory -Force (Join-Path (Get-Location) 'work') | Out-Null
$checks|ConvertTo-Json -Depth 6|Set-Content -LiteralPath './work/verified-integrations.json' -Encoding utf8
$checks|Format-Table repository,tag,resolved_commit|Out-Host
