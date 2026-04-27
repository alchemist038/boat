param(
    [string]$TargetDate = "",
    [switch]$SkipCollect,
    [switch]$SkipPredict,
    [int]$MaxWaitMinutes = 30,
    [int]$PollSeconds = 300
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

function Wait-ForResultsDate {
    param(
        [string]$PythonPath,
        [string]$DatabasePath,
        [string]$RequiredDate,
        [int]$TimeoutMinutes,
        [int]$IntervalSeconds
    )
    $deadline = (Get-Date).AddMinutes($TimeoutMinutes)
    while ($true) {
        $maxDate = Get-ResultsMaxRaceDate -PythonPath $PythonPath -DatabasePath $DatabasePath
        Write-Step "results max race_date=$maxDate required=$RequiredDate"
        if ($maxDate -ge $RequiredDate) {
            return [pscustomobject]@{
                EffectiveDate = $maxDate
                UsedFallback = $false
                LagDays = 0
            }
        }
        if ((Get-Date) -ge $deadline) {
            if (-not [string]::IsNullOrWhiteSpace($maxDate)) {
                $required = [datetime]::Parse($RequiredDate).Date
                $effective = [datetime]::Parse($maxDate).Date
                $lagDays = [int]($required - $effective).TotalDays
                Write-Step "results fallback engaged: using cutoff_date=$maxDate lag=${lagDays}d required=$RequiredDate"
                return [pscustomobject]@{
                    EffectiveDate = $maxDate
                    UsedFallback = $true
                    LagDays = $lagDays
                }
            }
            throw "timed out waiting for results race_date >= $RequiredDate"
        }
        Start-Sleep -Seconds $IntervalSeconds
    }
}

function Clear-ResultsArtifacts {
    param(
        [string]$SharedDataRoot,
        [string]$DateCompact
    )
    foreach ($table in @("results", "beforeinfo", "odds_2t")) {
        $rawDir = Join-Path $SharedDataRoot ("raw\\{0}\\{1}" -f $table, $DateCompact)
        if (Test-Path $rawDir) {
            Remove-Item -LiteralPath $rawDir -Recurse -Force
            Write-Step "cleared raw $table cache for $DateCompact"
        }
    }
    foreach ($table in @("results", "beforeinfo_entries", "odds_2t")) {
        $bronzeCsv = Join-Path $SharedDataRoot ("bronze\\{0}\\{1}.csv" -f $table, $DateCompact)
        if (Test-Path $bronzeCsv) {
            Remove-Item -LiteralPath $bronzeCsv -Force
            Write-Step "cleared bronze $table csv for $DateCompact"
        }
    }
}

function Invoke-CollectDay {
    param(
        [string]$PythonPath,
        [string]$CliLauncherPath,
        [string]$DatabasePath,
        [string]$RawRoot,
        [string]$BronzeRoot,
        [string]$DateCompact
    )
    & $PythonPath $CliLauncherPath collect-day `
        --date $DateCompact `
        --db-path $DatabasePath `
        --raw-root $RawRoot `
        --bronze-root $BronzeRoot `
        --skip-term-stats `
        --skip-quality-report `
        --skip-odds-3t
    if ($LASTEXITCODE -ne 0) {
        throw "collect-day failed with exit code $LASTEXITCODE for date $DateCompact"
    }
}

function Sync-LocalRacerRankOutput {
    param(
        [string]$SourceDir,
        [string]$DestinationDir
    )
    if (-not (Test-Path $SourceDir)) {
        throw "racer-index output not found: $SourceDir"
    }
    $resolvedSource = [System.IO.Path]::GetFullPath($SourceDir)
    $resolvedDestination = [System.IO.Path]::GetFullPath($DestinationDir)
    if ($resolvedSource -eq $resolvedDestination) {
        Write-Step "local fallback mirror skipped because source and destination are identical: $resolvedDestination"
        return
    }
    $destinationParent = Split-Path -Parent $DestinationDir
    New-Item -ItemType Directory -Path $destinationParent -Force | Out-Null
    if (Test-Path $DestinationDir) {
        Remove-Item -LiteralPath $DestinationDir -Recurse -Force
    }
    Copy-Item -LiteralPath $SourceDir -Destination $DestinationDir -Recurse -Force
    Write-Step "mirrored racer-index output to local fallback: $DestinationDir"
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$pythonPath = Join-Path $repoRoot ".venv\Scripts\python.exe"
$cliLauncherPath = Join-Path $repoRoot "workspace_codex\scripts\run_boat_race_cli.py"
if (-not (Test-Path $pythonPath)) {
    throw "Python not found: $pythonPath"
}
if (-not (Test-Path $cliLauncherPath)) {
    throw "CLI launcher not found: $cliLauncherPath"
}

$target = Resolve-TargetDate -InputDate $TargetDate
$targetIso = $target.ToString("yyyy-MM-dd")
$targetCompact = $target.ToString("yyyyMMdd")
$cutoffDate = $target.AddDays(-1)
$cutoffIso = $cutoffDate.ToString("yyyy-MM-dd")
$cutoffCompact = $cutoffDate.ToString("yyyyMMdd")
$cutoffMonthStart = Get-Date -Year $cutoffDate.Year -Month $cutoffDate.Month -Day 1
$tuneStartIso = $cutoffMonthStart.ToString("yyyy-MM-dd")
$profileStartIso = $cutoffMonthStart.AddMonths(-13).ToString("yyyy-MM-dd")

$canonicalRoot = Get-CanonicalRoot -RepoRoot $repoRoot
$sharedDataRoot = if (-not [string]::IsNullOrWhiteSpace($env:BOAT_DATA_ROOT)) {
    $env:BOAT_DATA_ROOT
} else {
    Join-Path $canonicalRoot "data"
}
$sharedReportsRoot = if (-not [string]::IsNullOrWhiteSpace($env:BOAT_REPORTS_ROOT)) {
    $env:BOAT_REPORTS_ROOT
} else {
    Join-Path $canonicalRoot "reports\strategies"
}
$localReportsRoot = Join-Path $repoRoot "reports\strategies"
$rawRoot = Join-Path $sharedDataRoot "raw"
$bronzeRoot = Join-Path $sharedDataRoot "bronze"
$dbPath = Join-Path $sharedDataRoot "silver\boat_race.duckdb"
$outputDir = Join-Path $sharedReportsRoot "racer_rank_live_$targetCompact"
$localOutputDir = Join-Path $localReportsRoot "racer_rank_live_$targetCompact"
$predictScript = if (-not [string]::IsNullOrWhiteSpace($env:BOAT_PREDICT_SCRIPT_PATH)) {
    $env:BOAT_PREDICT_SCRIPT_PATH
} else {
    Join-Path $canonicalRoot "workspace_codex\scripts\predict_racer_rank_live.py"
}
if (-not (Test-Path $predictScript)) {
    throw "predict script not found: $predictScript"
}

$logDir = Join-Path $repoRoot "live_trigger_cli\data\logs"
$logPath = Join-Path $logDir "racer_rank_live_daily.log"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null

$env:PYTHONPATH = Join-Path $repoRoot "src"

Start-Transcript -Path $logPath -Append | Out-Null
try {
    Write-Step "target_date=$targetIso cutoff_date=$cutoffIso tune_start=$tuneStartIso profile_start=$profileStartIso"

    if (-not $SkipCollect) {
        $initialResultsMaxDate = Get-ResultsMaxRaceDate -PythonPath $pythonPath -DatabasePath $dbPath
        if ($initialResultsMaxDate -lt $cutoffIso) {
            Write-Step "prior-day results missing in shared DB; backfill collect-day started for $cutoffCompact"
            Clear-ResultsArtifacts -SharedDataRoot $sharedDataRoot -DateCompact $cutoffCompact
            Invoke-CollectDay `
                -PythonPath $pythonPath `
                -CliLauncherPath $cliLauncherPath `
                -DatabasePath $dbPath `
                -RawRoot $rawRoot `
                -BronzeRoot $bronzeRoot `
                -DateCompact $cutoffCompact
            Write-Step "prior-day results backfill completed for $cutoffCompact"
        }
    }

    $resultsState = Wait-ForResultsDate `
        -PythonPath $pythonPath `
        -DatabasePath $dbPath `
        -RequiredDate $cutoffIso `
        -TimeoutMinutes $MaxWaitMinutes `
        -IntervalSeconds $PollSeconds
    $effectiveCutoffIso = [string]$resultsState.EffectiveDate
    if ($resultsState.UsedFallback) {
        Write-Step "continuing with stale cutoff_date=$effectiveCutoffIso lag_days=$($resultsState.LagDays)"
    } else {
        Write-Step "results ready: cutoff_date=$effectiveCutoffIso"
    }

    if (-not $SkipCollect) {
        Write-Step "collect-day started"
        Invoke-CollectDay `
            -PythonPath $pythonPath `
            -CliLauncherPath $cliLauncherPath `
            -DatabasePath $dbPath `
            -RawRoot $rawRoot `
            -BronzeRoot $bronzeRoot `
            -DateCompact $targetCompact
        Write-Step "collect-day completed"
    }

    if (-not $SkipPredict) {
        Write-Step "predict_racer_rank_live started"
        & $pythonPath $predictScript `
            --db-path $dbPath `
            --raw-root $rawRoot `
            --cutoff-date $effectiveCutoffIso `
            --target-date $targetIso `
            --profile-start $profileStartIso `
            --tune-start $tuneStartIso `
            --output-dir $outputDir
        if ($LASTEXITCODE -ne 0) {
            throw "predict_racer_rank_live failed with exit code $LASTEXITCODE"
        }
        Write-Step "predict_racer_rank_live completed"
        Sync-LocalRacerRankOutput -SourceDir $outputDir -DestinationDir $localOutputDir
    }

    Write-Step "done output_dir=$outputDir"
}
finally {
    Stop-Transcript | Out-Null
}
