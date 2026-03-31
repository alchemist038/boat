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
    $rawResultsDir = Join-Path $SharedDataRoot ("raw\\results\\{0}" -f $DateCompact)
    $bronzeResultsCsv = Join-Path $SharedDataRoot ("bronze\\results\\{0}.csv" -f $DateCompact)
    if (Test-Path $rawResultsDir) {
        Remove-Item -LiteralPath $rawResultsDir -Recurse -Force
        Write-Step "cleared raw results cache for $DateCompact"
    }
    if (Test-Path $bronzeResultsCsv) {
        Remove-Item -LiteralPath $bronzeResultsCsv -Force
        Write-Step "cleared bronze results csv for $DateCompact"
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

$sharedDataRoot = "\\038INS\boat\data"
$sharedReportsRoot = "\\038INS\boat\reports\strategies"
$rawRoot = Join-Path $sharedDataRoot "raw"
$bronzeRoot = Join-Path $sharedDataRoot "bronze"
$dbPath = Join-Path $sharedDataRoot "silver\boat_race.duckdb"
$outputDir = Join-Path $sharedReportsRoot "racer_rank_live_$targetCompact"
$predictScript = "\\038INS\boat\workspace_codex\scripts\predict_racer_rank_live.py"

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
    }

    Write-Step "done output_dir=$outputDir"
}
finally {
    Stop-Transcript | Out-Null
}
