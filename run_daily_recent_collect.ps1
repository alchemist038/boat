Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = "D:\boat"
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
$logRoot = Join-Path $repoRoot "reports\logs"

$sharedRoot = "\\038INS\boat\data"
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
