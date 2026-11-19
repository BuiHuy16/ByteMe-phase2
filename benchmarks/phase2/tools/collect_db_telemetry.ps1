param(
    [Parameter(Mandatory = $true)][string]$Project,
    [Parameter(Mandatory = $true)][string]$EnvFile,
    [Parameter(Mandatory = $true)][string]$OutputFile
)

$ErrorActionPreference = 'Stop'
$compose = @('compose','--env-file',$EnvFile,'-p',$Project,'-f','compose.yaml','-f','benchmarks/phase2/compose.benchmark.yaml')
$parent = Split-Path -Parent $OutputFile
if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }

$sql = @'
SELECT UTC_TIMESTAMP(6) captured_at_utc, VERSION() mysql_version, DATABASE() database_name;
SHOW GLOBAL STATUS WHERE Variable_name IN ('Threads_connected','Threads_running','Connections','Questions','Queries','Com_select','Com_insert','Com_update','Com_delete','Slow_queries','Created_tmp_disk_tables','Created_tmp_tables','Innodb_buffer_pool_read_requests','Innodb_buffer_pool_reads','Innodb_row_lock_current_waits','Innodb_row_lock_time','Innodb_row_lock_waits');
SELECT DIGEST, LEFT(DIGEST_TEXT,500) AS DIGEST_TEXT, COUNT_STAR, ROUND(SUM_TIMER_WAIT/1000000000,3) AS SUM_TIMER_WAIT_MS, SUM_ROWS_AFFECTED, SUM_ROWS_SENT, SUM_ROWS_EXAMINED, SUM_CREATED_TMP_DISK_TABLES, SUM_NO_INDEX_USED
FROM performance_schema.events_statements_summary_by_digest
WHERE SCHEMA_NAME = DATABASE() AND DIGEST IS NOT NULL
ORDER BY COUNT_STAR DESC, DIGEST
LIMIT 200;
'@

$sql | & docker @compose exec -T mysql sh -lc 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql --batch --raw -uroot "$MYSQL_DATABASE"' |
    Set-Content -Encoding UTF8 -LiteralPath $OutputFile
if ($LASTEXITCODE -ne 0) { throw "DB telemetry collection failed with exit $LASTEXITCODE" }
