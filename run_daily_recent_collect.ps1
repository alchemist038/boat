Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path $PSScriptRoot).Path
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
$logRoot = Join-Path $repoRoot "reports\logs"

function Get-CanonicalRoot {
    param([string]$RepoRoot = "")
    if (-not [string]::IsNullOrWhiteSpace($env:BOAT_CANONICAL_ROOT)) {
        return $env:BOAT_CANONICAL_ROOT
    }
    if (-not [string]::IsNullOrWhiteSpace($env:BOAT_DATA_ROOT)) {
        $dataRoot = $env:BOAT_DATA_ROOT
        if ((Split-Path -Leaf $dataRoot).ToLowerInvariant() -eq "data") {
            return (Split-Path -Parent $dataRoot)
        }
        return $dataRoot
    }
    if (-not [string]::IsNullOrWhiteSpace($RepoRoot)) {
        $repoDb = Join-Path $RepoRoot "data\silver\boat_race.duckdb"
        if (Test-Path $repoDb) {
            return $RepoRoot
        }
    }
    $localCanonicalRoot = "C:\boat"
    if (Test-Path (Join-Path $localCanonicalRoot "data\silver\boat_race.duckdb")) {
        return $localCanonicalRoot
    }
    if (-not [string]::IsNullOrWhiteSpace($RepoRoot)) {
        return $RepoRoot
    }
    return (Get-Location).Path
}

$canonicalRoot = Get-CanonicalRoot -RepoRoot $repoRoot
$sharedRoot = if (-not [string]::IsNullOrWhiteSpace($env:BOAT_DATA_ROOT)) {
    $env:BOAT_DATA_ROOT
} else {
    Join-Path $canonicalRoot "data"
}
$rawRoot = Join-Path $sharedRoot "raw"
$bronzeRoot = Join-Path $sharedRoot "bronze"
$dbPath = Join-Path $sharedRoot "silver\boat_race.duckdb"

$today = (Get-Date).Date
$startDate = $today.AddDays(-2).ToString("yyyyMMdd")
$endDate = $today.AddDays(-1).ToString("yyyyMMdd")
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"

New-Item -ItemType Directory -Force -Path $logRoot | Out-Null

$outLog = Join-Path $logRoot "boat_daily_recent_${startDate}_${endDate}_${stamp}.out.log"
$errLog = Join-Path $logRoot "boat_daily_recent_${startDate}_${endDate}_${stamp}.err.log"

$args = @(
    "-m", "boat_race_data", "collect-range",
    "--start-date", $startDate,
    "--end-date", $endDate,
    "--raw-root", $rawRoot,
    "--bronze-root", $bronzeRoot,
    "--db-path", $dbPath,
    "--sleep-seconds", "0.5",
    "--refresh-every-days", "0",
    "--resume-existing-days",
    "--skip-term-stats",
    "--skip-quality-report"
)

$quotedArgs = $args | ForEach-Object {
    if ($_ -match "\s") { '"' + $_ + '"' } else { $_ }
}

Add-Content -Path $outLog -Value ("[{0}] start recent collect {1}..{2}" -f (Get-Date -Format "s"), $startDate, $endDate)
Add-Content -Path $outLog -Value ("command: {0} {1}" -f $pythonExe, ($quotedArgs -join " "))

Push-Location $repoRoot
try {
    & $pythonExe @args 1>> $outLog 2>> $errLog
    $exitCode = $LASTEXITCODE
    Add-Content -Path $outLog -Value ("[{0}] exit_code={1}" -f (Get-Date -Format "s"), $exitCode)
    if ($exitCode -ne 0) {
        throw "boat daily recent collect failed with exit code $exitCode"
    }
}
finally {
    Pop-Location
}
