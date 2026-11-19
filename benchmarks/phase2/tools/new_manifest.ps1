param(
    [Parameter(Mandatory = $true)][string]$Root,
    [string]$Name = 'SHA256SUMS.txt'
)

$ErrorActionPreference = 'Stop'
$resolved = (Resolve-Path -LiteralPath $Root).Path
$manifest = Join-Path $resolved $Name
$lines = Get-ChildItem -LiteralPath $resolved -Recurse -File |
    Where-Object { $_.FullName -ne $manifest } |
    Sort-Object FullName |
    ForEach-Object {
        $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash.ToLowerInvariant()
        $relative = $_.FullName.Substring($resolved.Length + 1).Replace('\','/')
        "$hash  $relative"
    }
$lines | Set-Content -Encoding ASCII -LiteralPath $manifest
"artifacts=$($lines.Count) manifest=$manifest"
