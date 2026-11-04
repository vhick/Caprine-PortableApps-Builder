# The only legitimate non-success result for a new release is HTTP 404.
# Do not rely on a previous native CLI invocation's LASTEXITCODE: the built-in
# GitHub Actions pwsh shell appends an exit check at the end of each step.
function Test-CaprinePublishedRelease {
    param(
        [Parameter(Mandatory)][int]$HttpStatus,
        [AllowNull()][object]$Response,
        [Parameter(Mandatory)][string]$ExpectedTag
    )
    if ($HttpStatus -eq 404) {
        Write-Host "Release $ExpectedTag does not exist yet; proceed with the build."
        return $false
    }
    if ($HttpStatus -ne 200) {
        throw "GitHub release lookup failed with HTTP $HttpStatus; not treating this as a missing release."
    }
    if ($null -eq $Response -or [string]$Response.tag_name -ne $ExpectedTag) {
        throw "GitHub returned HTTP 200 but the release tag did not match the requested tag ($ExpectedTag)."
    }
    Write-Host "Release $ExpectedTag already exists; skip rebuild unless forced."
    return $true
}
