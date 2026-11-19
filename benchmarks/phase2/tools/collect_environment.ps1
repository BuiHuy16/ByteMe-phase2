param(
    [Parameter(Mandatory = $true)][string]$Project,
    [Parameter(Mandatory = $true)][string]$EnvFile,
    [Parameter(Mandatory = $true)][string]$OutputDir,
    [Parameter(Mandatory = $true)][string]$K6Image
)

$ErrorActionPreference = 'Continue'
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$compose = @('compose','--env-file',$EnvFile,'-p',$Project,'-f','compose.yaml','-f','benchmarks/phase2/compose.benchmark.yaml')

$source = @()
$source += "captured_at_utc=$([DateTime]::UtcNow.ToString('o'))"
$source += "git_sha=$(& git rev-parse HEAD)"
$source += "git_branch=$(& git branch --show-current)"
$source += 'git_status_begin'
$source += (& git status --short)
$source += 'git_status_end'
$source += "executable_diff_exit=$(& git diff --quiet 510f6415b6af535ceec77213f0b0c7d5082123f7 -- src pom.xml compose.yaml Dockerfile .dockerignore .env.example scripts; $LASTEXITCODE)"
$source | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $OutputDir 'source.txt')

$docker = @()
$docker += (& docker version)
$docker += "context=$(& docker context show)"
$docker += (& docker info --format 'server={{.ServerVersion}} os={{.OperatingSystem}} arch={{.Architecture}} cpus={{.NCPU}} memory={{.MemTotal}}')
$docker += 'compose_version=' + (& docker compose version --short)
$docker += 'compose_services=' + ((& docker @compose config --services) -join ',')
$docker += 'compose_images=' + ((& docker @compose config --images) -join ',')
$docker | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $OutputDir 'docker.txt')

& docker @compose ps --format json | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $OutputDir 'compose-ps.jsonl')
$backend = (& docker ps --filter "label=com.docker.compose.project=$Project" --filter 'label=com.docker.compose.service=backend' -q)
$mysql = (& docker ps --filter "label=com.docker.compose.project=$Project" --filter 'label=com.docker.compose.service=mysql' -q)
@(
    "backend_container=$backend"
    "backend_image_id=$(& docker inspect $backend --format '{{.Image}}')"
    "backend_nano_cpus=$(& docker inspect $backend --format '{{.HostConfig.NanoCpus}}')"
    "backend_memory_limit=$(& docker inspect $backend --format '{{.HostConfig.Memory}}')"
    "mysql_container=$mysql"
    "mysql_image_id=$(& docker inspect $mysql --format '{{.Image}}')"
    "mysql_nano_cpus=$(& docker inspect $mysql --format '{{.HostConfig.NanoCpus}}')"
    "mysql_memory_limit=$(& docker inspect $mysql --format '{{.HostConfig.Memory}}')"
) | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $OutputDir 'container-lock.txt')

$sql = @'
SELECT VERSION() mysql_version, @@transaction_isolation transaction_isolation, @@autocommit autocommit, @@max_connections max_connections, @@innodb_buffer_pool_size innodb_buffer_pool_size, @@performance_schema performance_schema;
SHOW GLOBAL STATUS WHERE Variable_name IN ('Threads_connected','Threads_running','Connections','Aborted_connects','Innodb_row_lock_current_waits','Innodb_row_lock_time','Innodb_row_lock_waits');
'@
$sql | & docker @compose exec -T mysql sh -lc 'MYSQL_PWD="$MYSQL_PASSWORD" mysql --batch --raw -u"$MYSQL_USER" "$MYSQL_DATABASE"' | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $OutputDir 'mysql.txt')
$controlNames = @(
    'JAVA_TOOL_OPTIONS='
    'SPRING_DATASOURCE_HIKARI_MAXIMUM_POOL_SIZE='
    'SPRING_DATASOURCE_HIKARI_MINIMUM_IDLE='
    'SERVER_TOMCAT_THREADS_MAX='
    'SERVER_TOMCAT_THREADS_MIN_SPARE='
)
$controls = @(& docker inspect $backend --format '{{range .Config.Env}}{{println .}}{{end}}') |
    Where-Object { $line = $_; $controlNames | Where-Object { $line.StartsWith($_) } } |
    Sort-Object
$jvm = @(& docker @compose exec -T backend java -XshowSettings:vm -version 2>&1)
@($controls + $jvm) | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $OutputDir 'jvm-and-app-controls.txt')
& docker run --rm $K6Image version 2>&1 | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $OutputDir 'k6-version.txt')
& docker image inspect $K6Image --format 'id={{.Id}} digests={{json .RepoDigests}} size={{.Size}} created={{.Created}}' | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $OutputDir 'k6-image.txt')

Get-FileHash -Algorithm SHA256 benchmarks/phase2/profiles.json,benchmarks/phase2/compose.benchmark.yaml,benchmarks/phase2/prepare_dataset.py,benchmarks/phase2/workloads/w1_read.js,benchmarks/phase2/workloads/w2_write.js,benchmarks/phase2/workloads/w3_contention.py,benchmarks/phase2/tools/aggregate_runs.py,benchmarks/phase2/tools/collect_db_telemetry.ps1 |
    ForEach-Object { "$($_.Hash.ToLowerInvariant())  $($_.Path)" } |
    Set-Content -Encoding ASCII -LiteralPath (Join-Path $OutputDir 'workload-source-checksums.txt')
