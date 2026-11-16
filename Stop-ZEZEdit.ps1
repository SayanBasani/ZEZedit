# =====================================================================
# ZEZEdit 2.0 - Windows Production PowerShell Stop Script
# =====================================================================
[CmdletBinding()]
param(
    [int]$GracefulTimeoutSeconds = 5
)

$ErrorActionPreference = "SilentlyContinue"

# 1. Resolve Workspace Root from Script Location
$scriptDir = $PSScriptRoot
if (-not $scriptDir -and $MyInvocation.MyCommand.Path) {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
}
if (-not $scriptDir) {
    $scriptDir = (Get-Location).Path
}
$root = (Resolve-Path $scriptDir).Path

$pidFile = Join-Path $root "storage\temp\zezedit.pid"
$procMetaFile = Join-Path $root "storage\temp\zezedit_process.json"

Write-Host "Stopping ZEZEdit 2.0..." -ForegroundColor Yellow

$stopped = $false
$targetPid = $null

# 2. Inspect Process Ownership Record
if (Test-Path $procMetaFile) {
    try {
        $meta = Get-Content $procMetaFile -Raw | ConvertFrom-Json
        $targetPid = [int]$meta.pid
    } catch {
        $targetPid = $null
    }
} elseif (Test-Path $pidFile) {
    $rawPid = Get-Content $pidFile -Raw
    $pidInt = 0
    if ([int]::TryParse($rawPid.Trim(), [ref]$pidInt)) {
        $targetPid = $pidInt
    }
}

if ($targetPid) {
    $proc = Get-Process -Id $targetPid -ErrorAction SilentlyContinue
    if ($proc) {
        # Check command line via CIM to guarantee it is ZEZEdit and avoid PID reuse
        $cim = Get-CimInstance Win32_Process -Filter "ProcessId = $targetPid" -ErrorAction SilentlyContinue
        $cmd = if ($cim) { $cim.CommandLine } else { "" }
        $path = if ($proc) { $proc.Path } else { "" }

        if ($cmd -like "*app.main:app*") {
            Write-Host "Requesting graceful shutdown for ZEZEdit server (PID: $targetPid)..."
            
            # Send graceful termination without /F
            & taskkill /PID $targetPid /T >$null 2>&1

            # Wait for graceful exit
            $cleanExit = $false
            for ($i = 0; $i -lt ($GracefulTimeoutSeconds * 2); $i++) {
                Start-Sleep -Milliseconds 500
                if (-not (Get-Process -Id $targetPid -ErrorAction SilentlyContinue)) {
                    $cleanExit = $true
                    break
                }
            }

            # Escalate to forceful kill only if refused
            if (-not $cleanExit) {
                Write-Host "Process did not exit within graceful window. Forcing termination..." -ForegroundColor Yellow
                Stop-Process -Id $targetPid -Force -ErrorAction SilentlyContinue
            }

            # Terminate any remaining child processes owned by this PID
            $children = Get-CimInstance Win32_Process -Filter "ParentProcessId = $targetPid" -ErrorAction SilentlyContinue
            foreach ($child in $children) {
                Stop-Process -Id $child.ProcessId -Force -ErrorAction SilentlyContinue
            }

            Write-Host "Successfully stopped ZEZEdit process (PID: $targetPid)" -ForegroundColor Green
            $stopped = $true
        } else {
            Write-Warning "PID $targetPid is running as '$($proc.ProcessName)' with command '$cmd', which does not belong to ZEZEdit (PID reuse detected). Preserving process."
        }
    } else {
        Write-Host "Recorded process (PID: $targetPid) was not running (stale record)." -ForegroundColor Yellow
    }
    Remove-Item -Path $pidFile -Force -ErrorAction SilentlyContinue
    Remove-Item -Path $procMetaFile -Force -ErrorAction SilentlyContinue
}

# 3. Fallback: Check Port 8000 Listener
if (-not $stopped) {
    $conn = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.OwningProcess -gt 0 }
    if ($conn) {
        $owningPid = $conn[0].OwningProcess
        $p = Get-Process -Id $owningPid -ErrorAction SilentlyContinue
        $cim = Get-CimInstance Win32_Process -Filter "ProcessId = $owningPid" -ErrorAction SilentlyContinue
        $cmd = if ($cim) { $cim.CommandLine } else { "" }
        $path = if ($p) { $p.Path } else { "" }

        if ($cmd -like "*app.main:app*") {
            Write-Host "Stopping ZEZEdit listener on port 8000 (PID: $owningPid)..."
            & taskkill /PID $owningPid /T >$null 2>&1
            Start-Sleep -Seconds 1
            if (Get-Process -Id $owningPid -ErrorAction SilentlyContinue) {
                Stop-Process -Id $owningPid -Force -ErrorAction SilentlyContinue
            }
            Write-Host "Stopped ZEZEdit listener on port 8000 (PID: $owningPid)" -ForegroundColor Green
            $stopped = $true
        } else {
            Write-Warning "Port 8000 is open by PID $owningPid ($($p.ProcessName)), but does not match ZEZEdit. Preserving process."
        }
    }
}

if (-not $stopped) {
    Write-Host "No active ZEZEdit instance was found." -ForegroundColor Cyan
} else {
    Write-Host "ZEZEdit has been cleanly stopped." -ForegroundColor Green
}
exit 0
