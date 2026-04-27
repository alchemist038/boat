param(
    [string]$LogPath
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$logDir = Join-Path $repoRoot "reports\logs"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
if (-not $LogPath) {
    $LogPath = Join-Path $logDir "overnight_apply_odds_gap_recovery_20260326_${timestamp}.log"
}

New-Item -ItemType Directory -Force -Path $logDir | Out-Null
Start-Transcript -Path $logPath -Force | Out-Null

function Write-Log {
    param([string]$Message)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$ts] $Message"
}

function Copy-FileChecked {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Destination
    )
    if (-not (Test-Path -LiteralPath $Source)) {
        throw "Missing source file: $Source"
    }
    $destDir = Split-Path -Parent $Destination
    New-Item -ItemType Directory -Force -Path $destDir | Out-Null
    Copy-Item -LiteralPath $Source -Destination $Destination -Force
}

function Copy-DirectoryChecked {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Destination
    )
    if (-not (Test-Path -LiteralPath $Source)) {
        throw "Missing source directory: $Source"
    }
    if (Test-Path -LiteralPath $Destination) {
        Remove-Item -LiteralPath $Destination -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Destination) | Out-Null
    Copy-Item -LiteralPath $Source -Destination $Destination -Recurse -Force
}

function Get-DateRangeStrings {
    param(
        [Parameter(Mandatory = $true)][datetime]$Start,
        [Parameter(Mandatory = $true)][datetime]$End
    )
    $dates = @()
    $cursor = $Start
    while ($cursor -le $End) {
        $dates += $cursor.ToString("yyyyMMdd")
        $cursor = $cursor.AddDays(1)
    }
    return $dates
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

$canonicalRoot = Get-CanonicalRoot -RepoRoot $repoRoot
$sharedDataRoot = if (-not [string]::IsNullOrWhiteSpace($env:BOAT_DATA_ROOT)) {
    $env:BOAT_DATA_ROOT
} else {
    Join-Path $canonicalRoot "data"
}
$sharedBronze = Join-Path $sharedDataRoot "bronze"
$sharedRaw = Join-Path $sharedDataRoot "raw"
$sharedDb = Join-Path $sharedDataRoot "silver\boat_race.duckdb"
$backupRoot = Join-Path $sharedDataRoot "bronze_backup\odds_3t_20251225_20260228_before_gap_apply_20260326"

$boatA = "C:\CODEX_WORK\boat_a\data"
$boatB = "C:\CODEX_WORK\boat_b\data"

$summerDates = Get-DateRangeStrings -Start ([datetime]"2025-08-21") -End ([datetime]"2025-09-08")
$winterDates = Get-DateRangeStrings -Start ([datetime]"2025-12-25") -End ([datetime]"2026-02-28")

Write-Log "Starting overnight odds gap apply job"
Write-Log "Summer range count: $($summerDates.Count)"
Write-Log "Winter range count: $($winterDates.Count)"

Write-Log "Backing up existing shared winter 3t bronze files"
New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null
foreach ($date in $winterDates) {
    $sharedWinter3t = Join-Path $sharedBronze "odds_3t\$date.csv"
    if (Test-Path -LiteralPath $sharedWinter3t) {
        Copy-Item -LiteralPath $sharedWinter3t -Destination (Join-Path $backupRoot "$date.csv") -Force
    }
}

Write-Log "Copying summer 2t/3t bronze and raw from boat_a into shared roots"
foreach ($date in $summerDates) {
    Copy-FileChecked -Source (Join-Path $boatA "bronze\odds_2t\$date.csv") -Destination (Join-Path $sharedBronze "odds_2t\$date.csv")
    Copy-FileChecked -Source (Join-Path $boatA "bronze\odds_3t\$date.csv") -Destination (Join-Path $sharedBronze "odds_3t\$date.csv")
    Copy-DirectoryChecked -Source (Join-Path $boatA "raw\odds_2t\$date") -Destination (Join-Path $sharedRaw "odds_2t\$date")
    Copy-DirectoryChecked -Source (Join-Path $boatA "raw\odds_3t\$date") -Destination (Join-Path $sharedRaw "odds_3t\$date")
}

Write-Log "Replacing winter 3t bronze/raw from boat_b into shared roots"
foreach ($date in $winterDates) {
    Copy-FileChecked -Source (Join-Path $boatB "bronze\odds_3t\$date.csv") -Destination (Join-Path $sharedBronze "odds_3t\$date.csv")
    Copy-DirectoryChecked -Source (Join-Path $boatB "raw\odds_3t\$date") -Destination (Join-Path $sharedRaw "odds_3t\$date")
}

Write-Log "Running shared refresh-silver"
& (Join-Path $repoRoot ".venv\Scripts\python.exe") -m boat_race_data refresh-silver --db-path $sharedDb --bronze-root $sharedBronze --verbose

Write-Log "Verifying recovered counts in shared DuckDB"
@"
import duckdb
con = duckdb.connect(r'''$sharedDb''', read_only=True)
for table, start, end in [
    ("odds_2t", "2025-08-21", "2025-09-08"),
    ("odds_3t", "2025-08-21", "2025-09-08"),
    ("odds_2t", "2025-12-25", "2026-02-28"),
    ("odds_3t", "2025-12-25", "2026-02-28"),
]:
    count = con.execute(f"select count(*) from {table} where race_date between ? and ?", [start, end]).fetchone()[0]
    print(f"{table} {start}..{end}: {count}")
"@ | & (Join-Path $repoRoot ".venv\Scripts\python.exe") -

Write-Log "Overnight odds gap apply job completed successfully"
Write-Log "Log path: $logPath"

Stop-Transcript | Out-Null
