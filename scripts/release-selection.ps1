# Pure selection helper; no network, filesystem or GitHub release modifications.
# GitHub's REST API returns a JSON array, and Invoke-RestMethod may emit that
# array as ONE pipeline object. Explicitly enumerate before filtering it.
function Get-CaprineStableReleases {
    param([Parameter(Mandatory)][object]$ApiResponse)

    $items = @($ApiResponse | Write-Output)
    if ($items.Count -eq 1 -and $items[0] -is [array]) {
        $items = @($items[0] | Write-Output)
    }

    $eligible = @(
        foreach ($release in $items) {
            if ($null -eq $release) { continue }
            $name = [string]$release.tag_name
            if ($release.draft -or $release.prerelease) { continue }
            if ($name -cnotmatch '^v?[0-9]+\.[0-9]+\.[0-9]+$') { continue }
            try { $numericVersion = [version]($name -replace '^v','') }
            catch { continue }
            [pscustomobject]@{
                Release = $release
                NumericVersion = $numericVersion
                NormalizedVersion = $numericVersion.ToString()
            }
        }
    )
    $sorted = @($eligible | Sort-Object -Property NumericVersion -Descending)
    Write-Host "Upstream release API: received $($items.Count) entries; eligible stable semantic-version releases: $($sorted.Count)"
    return $sorted
}

function Select-CaprineStableRelease {
    param([Parameter(Mandatory)][object]$ApiResponse,[string]$RequestedVersion='')
    $stable = @(Get-CaprineStableReleases -ApiResponse $ApiResponse)
    if ($stable.Count -eq 0) {
        throw 'GitHub API returned no eligible stable release. Ensure tags use vX.Y.Z, releases are published and not draft/prerelease. Never use main implicitly.'
    }
    if ($RequestedVersion) {
        if ($RequestedVersion -notmatch '^v?[0-9]+\.[0-9]+\.[0-9]+$') {
            throw 'Requested version must match X.Y.Z or vX.Y.Z'
        }
        $wanted = $RequestedVersion -replace '^v',''
        $match = @($stable | Where-Object { $_.NormalizedVersion -eq $wanted })
        if ($match.Count -eq 0) { throw "Version $RequestedVersion is not a published stable release in the latest 100 releases" }
        return $match[0].Release
    }
    return $stable[0].Release
}
