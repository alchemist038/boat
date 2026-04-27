param(
    [string]$RepoRoot = "",
    [switch]$CreateIfMissing
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

$sharedCollectScript = Join-Path $RepoRoot "workspace_codex\scripts\run_shared_recent_collect_daily.ps1"
$racerIndexScript = Join-Path $RepoRoot "workspace_codex\scripts\run_racer_rank_live_daily.ps1"

foreach ($path in @($sharedCollectScript, $racerIndexScript)) {
    if (-not (Test-Path $path)) {
        throw "Missing task target script: $path"
    }
}

function New-TaskActionForScript {
    param([string]$ScriptPath)
    return New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`""
}

function Ensure-Task {
    param(
        [string]$TaskName,
        [string]$ScriptPath,
        [datetime]$DefaultStartTime
    )
    $existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    $action = New-TaskActionForScript -ScriptPath $ScriptPath
    if ($null -ne $existing) {
        $existing.Actions = @($action)
        Set-ScheduledTask -InputObject $existing | Out-Null
        Write-Host "Updated task action: $TaskName -> $ScriptPath"
        return
    }
    if (-not $CreateIfMissing.IsPresent) {
        Write-Host "Task not found, skipped (use -CreateIfMissing): $TaskName"
        return
    }
    $trigger = New-ScheduledTaskTrigger -Daily -At $DefaultStartTime
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $action `
        -Trigger $trigger `
        -Description "Boat operational task registered from $RepoRoot" | Out-Null
    Write-Host "Created task: $TaskName -> $ScriptPath"
}

Ensure-Task -TaskName "BoatSharedRecentCollectDaily" -ScriptPath $sharedCollectScript -DefaultStartTime ([datetime]"2000-01-01 01:00:00")
Ensure-Task -TaskName "BoatRacerIndexLiveCsvDaily" -ScriptPath $racerIndexScript -DefaultStartTime ([datetime]"2000-01-01 03:00:00")
