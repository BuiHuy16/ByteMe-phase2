param(
    [string]$EvidenceDir = 'docs/phase2/evidence/g2.4/smoke',
    [string]$Project = 'byteme-g24-smoke',
    [string]$K6Image = 'grafana/k6:0.55.2'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
Set-Location $repo
if (-not ($Project.StartsWith('byteme-g24-') -or $Project.StartsWith('byteme-benchmark-'))) {
    throw "Unsafe project name: $Project"
}

$evidence = if ([IO.Path]::IsPathRooted($EvidenceDir)) { [IO.Path]::GetFullPath($EvidenceDir) } else { [IO.Path]::GetFullPath((Join-Path $repo $EvidenceDir)) }
$runtime = [IO.Path]::GetFullPath((Join-Path $repo '.local/phase2-benchmark'))
$expectedRuntime = [IO.Path]::GetFullPath((Join-Path $repo '.local/phase2-benchmark'))
if (Test-Path -LiteralPath $evidence) { throw "Evidence directory already exists; refusing overwrite: $evidence" }
if (Test-Path -LiteralPath $runtime) { throw "Runtime directory already exists; refusing overwrite: $runtime" }

function New-EphemeralSecret {
    $bytes = New-Object byte[] 24
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    return ([Convert]::ToBase64String($bytes) -replace '[^A-Za-z0-9]','') + '9a!'
}
function Assert-Native([string]$label) {
    if ($LASTEXITCODE -ne 0) { throw "$label failed with exit $LASTEXITCODE" }
}

$previousActorPassword = $env:BENCH_ACTOR_PASSWORD
if (-not $env:BENCH_ACTOR_PASSWORD) { $env:BENCH_ACTOR_PASSWORD = New-EphemeralSecret }
$envFile = Join-Path $runtime 'runtime.env'
$keys = Join-Path $runtime 'keys'
$actors = Join-Path $runtime 'actors.json'
$started = [DateTime]::UtcNow.ToString('o')
$errorMessage = $null
$initialChecksum = $null
$resetChecksum = $null
$compose = @('compose','--env-file',$envFile,'-p',$Project,'-f','compose.yaml','-f','benchmarks/phase2/compose.benchmark.yaml')

New-Item -ItemType Directory -Force -Path $evidence,$runtime,$keys | Out-Null
foreach ($dir in 'build','startup','dataset','environment','database','w1','w2','w3','logs','cleanup','exit-codes') {
    New-Item -ItemType Directory -Force -Path (Join-Path $evidence $dir) | Out-Null
}

try {
    $existing = @(& docker ps -a --filter "label=com.docker.compose.project=$Project" -q)
    if ($existing.Count -gt 0 -and $existing[0]) { throw "Project already has containers: $Project" }
    $listeners = Get-NetTCPConnection -State Listen -LocalPort 13308,18082 -ErrorAction SilentlyContinue
    if ($listeners) { throw 'Smoke ports 13308/18082 are already in use' }

    @(
        'DB_NAME=byteme_g24_smoke'
        'DB_USERNAME=byteme_g24_user'
        "DB_PASSWORD=$(New-EphemeralSecret)"
        "DB_ROOT_PASSWORD=$(New-EphemeralSecret)"
        'DB_PORT=13308'
        'SERVER_PORT=18082'
    ) | Set-Content -Encoding ASCII -LiteralPath $envFile

    & openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:3072 -out (Join-Path $keys 'private.pem') 2>&1 | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $evidence 'startup/key-generation.txt')
    Assert-Native 'RSA private key generation'
    & openssl pkey -in (Join-Path $keys 'private.pem') -pubout -out (Join-Path $keys 'public.pem') 2>&1 | Add-Content -Encoding UTF8 -LiteralPath (Join-Path $evidence 'startup/key-generation.txt')
    Assert-Native 'RSA public key generation'

    & docker pull $K6Image 2>&1 | Tee-Object -FilePath (Join-Path $evidence 'build/k6-pull.txt') | Out-Host
    Assert-Native 'k6 image pull'
    & docker @compose build backend 2>&1 | Tee-Object -FilePath (Join-Path $evidence 'build/backend-build.txt') | Out-Host
    Assert-Native 'backend build'
    & docker @compose up -d 2>&1 | Tee-Object -FilePath (Join-Path $evidence 'startup/compose-up.txt') | Out-Host
    Assert-Native 'compose up'

    $ready = $false
    $attempts = @()
    for ($i=1; $i -le 40; $i++) {
        $health = & curl.exe --noproxy '*' --silent --show-error --write-out '|%{http_code}' http://127.0.0.1:18082/actuator/health 2>&1
        $attempts += "$([DateTime]::UtcNow.ToString('o'))`t$i`t$health"
        if (($health -join '') -match '\|200$') { $ready = $true; break }
        Start-Sleep -Seconds 2
    }
    $attempts | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $evidence 'startup/readiness.txt')
    if (-not $ready) { throw 'backend readiness failed' }

    & python -X utf8 benchmarks/phase2/prepare_dataset.py --mode prepare --profile smoke --project $Project --env-file $envFile --base-url http://127.0.0.1:18082 --runtime-actors $actors --output (Join-Path $evidence 'dataset/initial.json') 2>&1 | Tee-Object -FilePath (Join-Path $evidence 'dataset/prepare-output.txt') | Out-Host
    Assert-Native 'dataset prepare'
    $initial = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $evidence 'dataset/initial.json') | ConvertFrom-Json
    $initialChecksum = $initial.overall_sha256

    & powershell -NoProfile -ExecutionPolicy Bypass -File benchmarks/phase2/tools/collect_environment.ps1 -Project $Project -EnvFile $envFile -OutputDir (Join-Path $evidence 'environment') -K6Image $K6Image
    Assert-Native 'environment collection'

    $workloads = (Resolve-Path 'benchmarks/phase2/workloads').Path
    $collector = (Resolve-Path 'benchmarks/phase2/tools/collect_resources.ps1').Path
    $dbCollector = (Resolve-Path 'benchmarks/phase2/tools/collect_db_telemetry.ps1').Path
    $network = "${Project}_default"

    & powershell -NoProfile -ExecutionPolicy Bypass -File $dbCollector -Project $Project -EnvFile $envFile -OutputFile (Join-Path $evidence 'database/before-w1.txt')
    Assert-Native 'DB telemetry before W1'

    $w1Dir = (Resolve-Path (Join-Path $evidence 'w1')).Path
    $w1Name = "$Project-k6-w1"
    $job1 = Start-Job -ScriptBlock { param($script,$project,$output,$extra); & $script -Project $project -DurationSeconds 12 -IntervalSeconds 1 -OutputFile $output -ExtraContainer $extra } -ArgumentList $collector,$Project,(Join-Path $w1Dir 'docker-stats.tsv'),$w1Name
    & docker run --rm --name $w1Name --network $network --cpus 1 --memory 512m --volume "${workloads}:/workloads:ro" --volume "${runtime}:/runtime:ro" --volume "${w1Dir}:/results" -e ACTORS_FILE=/runtime/actors.json -e BASE_URL=http://backend:8080 -e BENCH_MODE=smoke -e ORDER_PAGE_SIZE=20 -e SUMMARY_PATH=/results/summary.json $K6Image run --no-color --out json=/results/raw.json /workloads/w1_read.js 2>&1 | Tee-Object -FilePath (Join-Path $w1Dir 'console.txt') | Out-Host
    $w1Exit = $LASTEXITCODE
    $w1Exit | Set-Content -Encoding ASCII -LiteralPath (Join-Path $evidence 'exit-codes/w1.txt')
    Wait-Job $job1 | Out-Null; Receive-Job $job1 | Out-Null; Remove-Job $job1
    if ($w1Exit -ne 0) { throw "W1 smoke failed: $w1Exit" }
    & powershell -NoProfile -ExecutionPolicy Bypass -File $dbCollector -Project $Project -EnvFile $envFile -OutputFile (Join-Path $evidence 'database/after-w1.txt')
    Assert-Native 'DB telemetry after W1'

    $w2Dir = (Resolve-Path (Join-Path $evidence 'w2')).Path
    $w2Name = "$Project-k6-w2"
    $job2 = Start-Job -ScriptBlock { param($script,$project,$output,$extra); & $script -Project $project -DurationSeconds 15 -IntervalSeconds 1 -OutputFile $output -ExtraContainer $extra } -ArgumentList $collector,$Project,(Join-Path $w2Dir 'docker-stats.tsv'),$w2Name
    & docker run --rm --name $w2Name --network $network --cpus 1 --memory 512m --volume "${workloads}:/workloads:ro" --volume "${runtime}:/runtime:ro" --volume "${w2Dir}:/results" -e ACTORS_FILE=/runtime/actors.json -e BASE_URL=http://backend:8080 -e BENCH_MODE=smoke -e WRITE_VUS=2 -e SUMMARY_PATH=/results/summary.json $K6Image run --no-color --out json=/results/raw.json /workloads/w2_write.js 2>&1 | Tee-Object -FilePath (Join-Path $w2Dir 'console.txt') | Out-Host
    $w2Exit = $LASTEXITCODE
    $w2Exit | Set-Content -Encoding ASCII -LiteralPath (Join-Path $evidence 'exit-codes/w2.txt')
    Wait-Job $job2 | Out-Null; Receive-Job $job2 | Out-Null; Remove-Job $job2
    if ($w2Exit -ne 0) { throw "W2 smoke failed: $w2Exit" }
    & powershell -NoProfile -ExecutionPolicy Bypass -File $dbCollector -Project $Project -EnvFile $envFile -OutputFile (Join-Path $evidence 'database/after-w2.txt')
    Assert-Native 'DB telemetry after W2'

    $w3Dir = (Resolve-Path (Join-Path $evidence 'w3')).Path
    $job3 = Start-Job -ScriptBlock { param($script,$project,$output); & $script -Project $project -DurationSeconds 15 -IntervalSeconds 1 -OutputFile $output } -ArgumentList $collector,$Project,(Join-Path $w3Dir 'docker-stats.tsv')
    & python -X utf8 benchmarks/phase2/workloads/w3_contention.py --project $Project --env-file $envFile --base-url http://127.0.0.1:18082 --actors $actors --rounds 2 --output (Join-Path $evidence 'w3/result.json') 2>&1 | Tee-Object -FilePath (Join-Path $evidence 'w3/console.txt') | Out-Host
    $w3Exit = $LASTEXITCODE
    $w3Exit | Set-Content -Encoding ASCII -LiteralPath (Join-Path $evidence 'exit-codes/w3.txt')
    Wait-Job $job3 | Out-Null; Receive-Job $job3 | Out-Null; Remove-Job $job3
    if ($w3Exit -ne 0) { throw "W3 smoke failed: $w3Exit" }
    & powershell -NoProfile -ExecutionPolicy Bypass -File $dbCollector -Project $Project -EnvFile $envFile -OutputFile (Join-Path $evidence 'database/after-w3.txt')
    Assert-Native 'DB telemetry after W3'

    & python -X utf8 benchmarks/phase2/prepare_dataset.py --mode snapshot --profile smoke --project $Project --env-file $envFile --base-url http://127.0.0.1:18082 --runtime-actors $actors --output (Join-Path $evidence 'dataset/post-workloads.json') 2>&1 | Tee-Object -FilePath (Join-Path $evidence 'dataset/post-workloads-output.txt') | Out-Host

    & python -X utf8 benchmarks/phase2/prepare_dataset.py --mode prepare --profile smoke --project $Project --env-file $envFile --base-url http://127.0.0.1:18082 --runtime-actors $actors --output (Join-Path $evidence 'dataset/after-reset.json') 2>&1 | Tee-Object -FilePath (Join-Path $evidence 'dataset/reset-output.txt') | Out-Host
    Assert-Native 'dataset reset'
    $afterReset = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $evidence 'dataset/after-reset.json') | ConvertFrom-Json
    $resetChecksum = $afterReset.overall_sha256
    if ($initialChecksum -ne $resetChecksum) { throw "dataset checksum mismatch after reset: $initialChecksum != $resetChecksum" }

    & docker @compose logs --no-color backend 2>&1 | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $evidence 'logs/backend.log')
    & docker @compose logs --no-color mysql 2>&1 | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $evidence 'logs/mysql.log')
}
catch {
    $errorMessage = $_.Exception.Message
}
finally {
    try {
        if (Test-Path -LiteralPath $envFile) {
            & docker @compose ps --format json 2>&1 | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $evidence 'cleanup/resources-before.jsonl')
            & docker @compose down -v --remove-orphans 2>&1 | Tee-Object -FilePath (Join-Path $evidence 'cleanup/compose-down.txt') | Out-Host
            $downExit = $LASTEXITCODE
            $downExit | Set-Content -Encoding ASCII -LiteralPath (Join-Path $evidence 'exit-codes/cleanup.txt')
            & docker image rm "$Project-backend:latest" 2>&1 | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $evidence 'cleanup/backend-image-removal.txt')
        }
        $post = @()
        $post += "containers=$((& docker ps -a --filter "label=com.docker.compose.project=$Project" -q) -join ',')"
        $post += "networks=$((& docker network ls --filter "label=com.docker.compose.project=$Project" -q) -join ',')"
        $post += "volumes=$((& docker volume ls --filter "label=com.docker.compose.project=$Project" -q) -join ',')"
        $listen = Get-NetTCPConnection -State Listen -LocalPort 13308,18082 -ErrorAction SilentlyContinue
        $post += "listeners=$([bool]$listen)"
        $post += "backend_image_exists=$([bool](& docker image inspect "$Project-backend:latest" --format '{{.Id}}' 2>$null))"
        $post | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $evidence 'cleanup/post-cleanup.txt')
    } catch {
        if (-not $errorMessage) { $errorMessage = "cleanup: $($_.Exception.Message)" }
    }
    if (Test-Path -LiteralPath $runtime) {
        $resolvedRuntime = (Resolve-Path -LiteralPath $runtime).Path
        if (-not [StringComparer]::OrdinalIgnoreCase.Equals($resolvedRuntime,$expectedRuntime)) { throw "Unsafe runtime cleanup path: $resolvedRuntime" }
        Remove-Item -LiteralPath $resolvedRuntime -Recurse -Force
    }
    if ($null -eq $previousActorPassword) { Remove-Item Env:BENCH_ACTOR_PASSWORD -ErrorAction SilentlyContinue } else { $env:BENCH_ACTOR_PASSWORD = $previousActorPassword }
}

$result = [ordered]@{
    started_at_utc = $started
    finished_at_utc = [DateTime]::UtcNow.ToString('o')
    project = $Project
    k6_image = $K6Image
    official_benchmark = $false
    status = if ($errorMessage) { 'FAIL' } else { 'PASS' }
    error = $errorMessage
    initial_dataset_sha256 = $initialChecksum
    reset_dataset_sha256 = $resetChecksum
    reset_matches_initial = ($initialChecksum -and $initialChecksum -eq $resetChecksum)
}
$result | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $evidence 'smoke-result.json')
& powershell -NoProfile -ExecutionPolicy Bypass -File benchmarks/phase2/tools/new_manifest.ps1 -Root $evidence | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $evidence 'manifest-output.txt')
if ($errorMessage) { throw $errorMessage }
Write-Output ($result | ConvertTo-Json -Depth 5)
