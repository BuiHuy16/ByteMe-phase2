param(
    [string]$ExpectedApplicationSha = '510f6415b6af535ceec77213f0b0c7d5082123f7',
    [string]$OutputDir = 'kaggle/dataset-g24k'
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
Set-Location $repo
$baseline = '510f6415b6af535ceec77213f0b0c7d5082123f7'
$repositorySha = (& git rev-parse HEAD)
& git cat-file -e "$ExpectedApplicationSha^{commit}"
if ($LASTEXITCODE -ne 0) { throw "Expected application SHA does not resolve: $ExpectedApplicationSha" }
$executablePaths = @('src','pom.xml','compose.yaml','Dockerfile','.dockerignore','.env.example','scripts')
& git diff --quiet $ExpectedApplicationSha $repositorySha -- @executablePaths
if ($LASTEXITCODE -ne 0) { throw "Executable tree at repository HEAD differs from expected application SHA $ExpectedApplicationSha" }
& git diff --quiet -- @executablePaths
if ($LASTEXITCODE -ne 0) { throw 'Working tree has uncommitted executable changes' }
& git diff --cached --quiet -- @executablePaths
if ($LASTEXITCODE -ne 0) { throw 'Index has staged executable changes' }
$untrackedExecutable = @(& git ls-files --others -- @executablePaths)
if ($untrackedExecutable.Count -gt 0) { throw "Working tree has untracked executable files: $($untrackedExecutable -join ', ')" }
$applicationSha = $ExpectedApplicationSha
$output = [IO.Path]::GetFullPath((Join-Path $repo $OutputDir))
if (Test-Path -LiteralPath $output) { throw "Output already exists; refusing overwrite: $output" }

New-Item -ItemType Directory -Path $output | Out-Null
$buildDir = Join-Path $output 'build'
New-Item -ItemType Directory -Path $buildDir | Out-Null
$buildLog = Join-Path $buildDir 'maven-build.txt'
$javaVersion = (& cmd.exe /d /c "java -version 2>&1") -join "`n"
if ($LASTEXITCODE -ne 0) { throw 'Unable to capture Java version' }
$mavenVersion = (& cmd.exe /d /c ".\mvnw.cmd -version 2>&1") -join "`n"
if ($LASTEXITCODE -ne 0) { throw 'Unable to capture Maven Wrapper version' }
$buildStarted = [DateTime]::UtcNow.ToString('o')
& cmd.exe /d /c ".\mvnw.cmd -B -DskipTests clean package 2>&1" | Tee-Object -FilePath $buildLog | Out-Host
$buildExit = $LASTEXITCODE
$buildFinished = [DateTime]::UtcNow.ToString('o')
if ($buildExit -ne 0) { throw "Maven build failed with exit $buildExit; see $buildLog" }
$jar = (Resolve-Path -LiteralPath 'target/application.jar').Path
$jarInfo = Get-Item -LiteralPath $jar
$jarHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $jar).Hash.ToLowerInvariant()
$treeListing = (& git ls-tree -r $ExpectedApplicationSha -- @executablePaths) -join "`n"
$sha = [Security.Cryptography.SHA256]::Create()
try { $treeHash = ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($treeListing))).Replace('-','').ToLowerInvariant()) } finally { $sha.Dispose() }
$provenance = [ordered]@{
    schema_version = 1
    protocol_baseline_sha = $baseline
    repository_sha = $repositorySha
    application_sha = $applicationSha
    executable_tree_listing_sha256 = $treeHash
    executable_paths = $executablePaths
    staged_executable_changes = $false
    unstaged_executable_changes = $false
    untracked_executable_changes = @()
    build_command = '.\mvnw.cmd -B -DskipTests clean package'
    build_started_utc = $buildStarted
    build_finished_utc = $buildFinished
    build_exit_code = $buildExit
    java_version = $javaVersion
    maven_version = $mavenVersion
    jar_source_path = 'target/application.jar'
    jar_sha256 = $jarHash
    jar_bytes = $jarInfo.Length
}
$provenance | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $buildDir 'build-provenance.json')
Copy-Item -LiteralPath $jar -Destination (Join-Path $output 'application.jar')
Copy-Item -LiteralPath 'src/main/resources/db/schema.sql' -Destination (Join-Path $output 'schema.sql')
$kit = Join-Path $output 'benchmark-kit/benchmarks/phase2'
New-Item -ItemType Directory -Force -Path $kit | Out-Null
Copy-Item -LiteralPath 'benchmarks/phase2/profiles.json','benchmarks/phase2/prepare_dataset.py','benchmarks/phase2/README.md' -Destination $kit
Copy-Item -LiteralPath 'benchmarks/phase2/workloads' -Destination $kit -Recurse
Copy-Item -LiteralPath 'benchmarks/phase2/kaggle' -Destination $kit -Recurse
Get-ChildItem -LiteralPath $kit -Recurse -Directory -Filter '__pycache__' | ForEach-Object {
    if (-not $_.FullName.StartsWith($kit,[StringComparison]::OrdinalIgnoreCase)) { throw "Unsafe generated-file cleanup path: $($_.FullName)" }
    Remove-Item -LiteralPath $_.FullName -Recurse -Force
}
Get-ChildItem -LiteralPath $kit -Recurse -File -Filter '*.pyc' | Remove-Item -Force

$files = Get-ChildItem -LiteralPath $output -Recurse -File | Sort-Object FullName | ForEach-Object {
    [ordered]@{ path = $_.FullName.Substring($output.Length + 1).Replace('\','/'); sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash.ToLowerInvariant(); bytes = $_.Length }
}
$manifest = [ordered]@{ schema_version = 2; protocol_baseline_sha = $baseline; repository_sha = $repositorySha; application_sha = $applicationSha; application_jar_sha256 = $jarHash; build_provenance_path = 'build/build-provenance.json'; generated_at_utc = [DateTime]::UtcNow.ToString('o'); files = @($files) }
$manifest | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $output 'bundle-manifest.json')
Write-Output "Bundle ready: $output"
Write-Output "Verified application JAR SHA-256: $jarHash"
Write-Output 'Upload this directory as a private Kaggle Dataset together with exactly one portable archive for Java 21.0.13, MySQL 8.4.13 and k6 0.55.2.'
