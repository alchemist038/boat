param(
    [string]$TargetDate = "",
    [int]$OverlapDays = 2,
    [switch]$SkipOdds3T
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] $Message"
}

function Resolve-TargetDate {
    param([string]$InputDate)
    if ([string]::IsNullOrWhiteSpace($InputDate)) {
        return (Get-Date).Date
    }
    return [datetime]::Parse($InputDate).Date
}

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

function Get-ResultsMaxRaceDate {
    param(
        [string]$PythonPath,
        [string]$DatabasePath
    )
    $script = @"
import duckdb
con = duckdb.connect(r'''$DatabasePath''', read_only=True)
row = con.execute('select cast(max(race_date) as varchar) from results').fetchone()
value = (row[0] or '').split(' ')[0] if row else ''
print(value)
"@
    $value = & $PythonPath -c $script
    if ($LASTEXITCODE -ne 0) {
        throw "failed to read max results race_date from $DatabasePath"
    }
    return [string]($value | Select-Object -Last 1)
}

function Clear-RefreshArtifacts {
    param(
        [string]$SharedRoot,
        [string[]]$DateCompacts,
        [bool]$IncludeOdds3T
    )
    foreach ($dateCompact in $DateCompacts) {
        $rawTables = @("results", "beforeinfo", "odds_2t")
        $bronzeTables = @("results", "beforeinfo_entries", "odds_2t")
        if ($IncludeOdds3T) {
            $rawTables += "odds_3t"
            $bronzeTables += "odds_3t"
        }

        foreach ($table in $rawTables) {
            $rawDir = Join-Path $SharedRoot ("raw\\{0}\\{1}" -f $table, $dateCompact)
            if (Test-Path $rawDir) {
                Remove-Item -LiteralPath $rawDir -Recurse -Force
                Write-Step "cleared raw $table cache for $dateCompact"
            }
        }
        foreach ($table in $bronzeTables) {
            $bronzeCsv = Join-Path $SharedRoot ("bronze\\{0}\\{1}.csv" -f $table, $dateCompact)
            if (Test-Path $bronzeCsv) {
                Remove-Item -LiteralPath $bronzeCsv -Force
                Write-Step "cleared bronze $table csv for $dateCompact"
            }
        }
    }
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
$canonicalRoot = Get-CanonicalRoot -RepoRoot $repoRoot
$sharedRoot = if (-not [string]::IsNullOrWhiteSpace($env:BOAT_DATA_ROOT)) {
    $env:BOAT_DATA_ROOT
} else {
    Join-Path $canonicalRoot "data"
}
$rawRoot = Join-Path $sharedRoot "raw"
$bronzeRoot = Join-Path $sharedRoot "bronze"
$dbPath = Join-Path $sharedRoot "silver\boat_race.duckdb"
$logRoot = Join-Path $repoRoot "live_trigger_cli\data\logs"
$logPath = Join-Path $logRoot "shared_recent_collect_daily.log"

if (-not (Test-Path $pythonExe)) {
    throw "Python not found: $pythonExe"
}

$target = Resolve-TargetDate -InputDate $TargetDate
$endDate = $target.AddDays(-1)
$nominalStartDate = $endDate.AddDays(-1 * [Math]::Max(1, $OverlapDays - 1))

New-Item -ItemType Directory -Force -Path $logRoot | Out-Null

Start-Transcript -Path $logPath -Append | Out-Null
try {
    $maxResultsDate = Get-ResultsMaxRaceDate -PythonPath $pythonExe -DatabasePath $dbPath
    $startDate = $nominalStartDate
    if (-not [string]::IsNullOrWhiteSpace($maxResultsDate)) {
        $catchUpStartDate = [datetime]::Parse($maxResultsDate).Date.AddDays(1)
        if ($catchUpStartDate -le $endDate -and $catchUpStartDate -lt $startDate) {
            $startDate = $catchUpStartDate
        }
    }
    $startCompact = $startDate.ToString("yyyyMMdd")
    $endCompact = $endDate.ToString("yyyyMMdd")
    $args = @(
        "-m", "boat_race_data", "collect-range",
        "--start-date", $startCompact,
        "--end-date", $endCompact,
        "--raw-root", $rawRoot,
        "--bronze-root", $bronzeRoot,
        "--db-path", $dbPath,
        "--sleep-seconds", "0.5",
        "--refresh-every-days", "0",
        "--resume-existing-days",
        "--skip-term-stats",
        "--skip-quality-report"
    )
    if ($SkipOdds3T) {
        $args += "--skip-odds-3t"
    }

    Write-Step "shared recent collect start target_date=$($target.ToString('yyyy-MM-dd')) window=$startCompact..$endCompact nominal_start=$($nominalStartDate.ToString('yyyyMMdd')) max_results=$maxResultsDate skip_odds3t=$($SkipOdds3T.IsPresent)"
    $datesToReset = @()
    $cursor = $startDate
    while ($cursor -le $endDate) {
        $datesToReset += $cursor.ToString("yyyyMMdd")
        $cursor = $cursor.AddDays(1)
    }
    Clear-RefreshArtifacts -SharedRoot $sharedRoot -DateCompacts $datesToReset -IncludeOdds3T:(-not $SkipOdds3T.IsPresent)
    Push-Location $repoRoot
    try {
        & $pythonExe @args
        $exitCode = $LASTEXITCODE
        Write-Step "shared recent collect exit_code=$exitCode"
        if ($exitCode -ne 0) {
            throw "shared recent collect failed with exit code $exitCode"
        }
    }
    finally {
        Pop-Location
    }
    Write-Step "shared recent collect completed"
}
finally {
    Stop-Transcript | Out-Null
}
