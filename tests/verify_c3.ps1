# MeLi DataSec Challenge - Challenge 3 verification harness (NOT a graded deliverable).
# Spins up a throwaway MySQL 8 instance (temp datadir under %TEMP%, non-default port),
# loads tests/seed_and_check.sql (statement dataset + applicant_query.sql verbatim),
# prints the result, then shuts the instance down and removes the temp datadir.
# Expected output row:   Whitney Ferrero | 6
$ErrorActionPreference = "Stop"

# Locate the MySQL 8 binaries (winget default install path; override with $env:MYSQL_BIN).
$mysqlBin   = if ($env:MYSQL_BIN) { $env:MYSQL_BIN } else { "C:\Program Files\MySQL\MySQL Server 8.4\bin" }
$mysqld     = Join-Path $mysqlBin "mysqld.exe"
$mysql      = Join-Path $mysqlBin "mysql.exe"
$mysqladmin = Join-Path $mysqlBin "mysqladmin.exe"
if (-not (Test-Path $mysqld)) { throw "mysqld.exe not found at $mysqld (set `$env:MYSQL_BIN)" }

# Use a space-free, non-synced datadir: Start-Process -ArgumentList does not quote
# spaces, and the repo path contains one ("Technical Challenge").
$base = Join-Path $env:TEMP "meli_c3_mysql"
$data = Join-Path $base "data"
$errLog = Join-Path $base "mysqld.err.log"
$outLog = Join-Path $base "mysqld.out.log"
$port = 3309
$seed = Join-Path $PSScriptRoot "seed_and_check.sql"

if (Test-Path $base) { Remove-Item -Recurse -Force $base }
New-Item -ItemType Directory -Force -Path $data | Out-Null

$proc = $null
try {
    Write-Output "Initializing throwaway MySQL data dir at $data ..."
    & $mysqld --no-defaults --initialize-insecure "--datadir=$data" --console
    if ($LASTEXITCODE -ne 0) { throw "mysqld --initialize-insecure failed (exit $LASTEXITCODE)" }

    Write-Output "Starting mysqld on 127.0.0.1:$port ..."
    $proc = Start-Process -FilePath $mysqld `
        -ArgumentList @("--no-defaults", "--datadir=$data", "--port=$port", "--bind-address=127.0.0.1", "--console") `
        -RedirectStandardError $errLog -RedirectStandardOutput $outLog `
        -PassThru -WindowStyle Hidden

    # Readiness: poll the TCP port directly (no client noise).
    $ready = $false
    foreach ($i in 1..40) {
        Start-Sleep -Milliseconds 750
        $client = New-Object System.Net.Sockets.TcpClient
        try { $client.Connect("127.0.0.1", $port); $ready = $client.Connected }
        catch { $ready = $false }
        finally { $client.Close() }
        if ($ready) { break }
        if ($proc.HasExited) { break }
    }
    if (-not $ready) {
        Write-Output "--- mysqld error log ---"
        if (Test-Path $errLog) { Get-Content $errLog -Tail 40 }
        throw "MySQL did not become ready (process exited: $($proc.HasExited))"
    }

    Start-Sleep -Milliseconds 500
    Write-Output "MySQL ready - loading seed + running applicant_query.sql"
    Write-Output "----------------------------------------------------------------"
    Get-Content $seed -Raw | & $mysql --protocol=TCP --host=127.0.0.1 --port=$port --user=root --table
    Write-Output "----------------------------------------------------------------"
}
finally {
    if ($proc -and -not $proc.HasExited) {
        & $mysqladmin --protocol=TCP --host=127.0.0.1 --port=$port --user=root shutdown
        Start-Sleep -Seconds 2
        if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue }
    }
    if (Test-Path $base) { Remove-Item -Recurse -Force $base -ErrorAction SilentlyContinue }
}
