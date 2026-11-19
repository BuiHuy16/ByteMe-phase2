param(
    [Parameter(Mandatory = $true)][string]$Project,
    [Parameter(Mandatory = $true)][int]$DurationSeconds,
    [int]$IntervalSeconds = 1,
    [Parameter(Mandatory = $true)][string]$OutputFile,
    [string[]]$ExtraContainer = @()
)

$ErrorActionPreference = 'Continue'
$parent = Split-Path -Parent $OutputFile
New-Item -ItemType Directory -Force -Path $parent | Out-Null
"timestamp_utc`tcontainer`tcpu_percent`tmemory_usage`tmemory_percent`tnet_io`tblock_io`tpids" | Set-Content -Encoding UTF8 -LiteralPath $OutputFile
$deadline = [DateTime]::UtcNow.AddSeconds($DurationSeconds)
while ([DateTime]::UtcNow -lt $deadline) {
    $names = @(& docker ps --filter "label=com.docker.compose.project=$Project" --format '{{.Names}}') + $ExtraContainer
    $names = @($names | Where-Object { $_ -and (& docker inspect $_ --format '{{.State.Running}}' 2>$null) -eq 'true' } | Select-Object -Unique)
    if ($names.Count -gt 0) {
        $stamp = [DateTime]::UtcNow.ToString('o')
        $rows = & docker stats --no-stream --format '{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}|{{.MemPerc}}|{{.NetIO}}|{{.BlockIO}}|{{.PIDs}}' @names 2>$null
        foreach ($row in $rows) {
            "$stamp`t$($row.Replace('|',"`t"))" | Add-Content -Encoding UTF8 -LiteralPath $OutputFile
        }
    }
    Start-Sleep -Seconds $IntervalSeconds
}
