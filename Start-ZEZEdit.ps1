# =====================================================================
# ZEZEdit 2.0 - Windows Production PowerShell Launcher
# =====================================================================
[CmdletBinding()]
param(
    [switch]$NoBrowser,
    [switch]$ValidateOnly,
    [int]$Port = 8000,
    [string]$HostAddress = "127.0.0.1",
    [int]$TimeoutSeconds = 30
)

$ErrorActionPreference = "Stop"

# Ensure local requests do not perform WPAD proxy discovery
try {
    [System.Net.WebRequest]::DefaultWebProxy = [System.Net.GlobalProxySelection]::GetEmptyWebProxy()
} catch {}

# 1. Resolve Workspace Root from Script Location
$scriptDir = $PSScriptRoot
if (-not $scriptDir -and $MyInvocation.MyCommand.Path) {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
}
if (-not $scriptDir) {
    $scriptDir = (Get-Location).Path
}
$root = (Resolve-Path $scriptDir).Path

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "               ZEZEdit 2.0 - Windows Production Launcher             " -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[1/6] Workspace root: $root"

# 2. Validate Python Environment and Dependencies
$pythonExe = Join-Path $root "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        $pythonExe = $pythonCmd.Source
    } else {
        Write-Host "[ERROR] Python 3.11+ is required but not found in backend\.venv or PATH." -ForegroundColor Red
        Write-Host "        Please create the virtual environment in backend\.venv or install Python 3.11+." -ForegroundColor Yellow
        exit 1
    }
}

# Verify Python version >= 3.11
try {
    $verOut = & $pythonExe -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
    $verParts = $verOut.Trim().Split(".")
    $major = [int]$verParts[0]
    $minor = [int]$verParts[1]
    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 11)) {
        Write-Host "[ERROR] Python version $verOut is incompatible. ZEZEdit requires Python 3.11 or newer." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "[ERROR] Failed to execute Python executable: $pythonExe" -ForegroundColor Red
    exit 1
}

# Verify core dependencies
& $pythonExe -c "import fastapi, uvicorn, pydantic" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Core Python dependencies (fastapi, uvicorn, pydantic) are missing in: $pythonExe" -ForegroundColor Red
    Write-Host "        Please install backend dependencies: pip install -e backend" -ForegroundColor Yellow
    exit 1
}
Write-Host "[2/6] Using Python: $pythonExe (version $verOut)"

# 3. Environment Configuration (.env)
$envFile = Join-Path $root ".env"
$envExample = Join-Path $root ".env.example"
if (-not (Test-Path $envFile) -and (Test-Path $envExample)) {
    Copy-Item $envExample $envFile
    Write-Host "[3/6] Initialized .env from .env.example"
} elseif (Test-Path $envFile) {
    Write-Host "[3/6] Environment configuration verified (.env)"
} else {
    Write-Host "[3/6] No .env file found; running with built-in production defaults."
}

# 4. Check Media Binaries (FFmpeg & FFprobe)
$ffmpegCmd = Get-Command ffmpeg -ErrorAction SilentlyContinue
$ffprobeCmd = Get-Command ffprobe -ErrorAction SilentlyContinue
if ($ffmpegCmd -and $ffprobeCmd) {
    Write-Host "[4/6] Media binaries available: ffmpeg ($($ffmpegCmd.Source)), ffprobe ($($ffprobeCmd.Source))"
} else {
    Write-Warning "[4/6] FFmpeg or FFprobe was not found on PATH. Video export and analysis require FFmpeg."
}

# 5. Check Frontend Production Distribution
$distIndex = Join-Path $root "frontend\dist\index.html"
if (-not (Test-Path $distIndex)) {
    Write-Host "[5/6] Frontend production build missing. Attempting build via npm..." -ForegroundColor Yellow
    $npmCmd = Get-Command npm -ErrorAction SilentlyContinue
    if (-not $npmCmd) {
        Write-Host "[ERROR] Frontend production build is missing and 'npm' was not found on PATH." -ForegroundColor Red
        Write-Host "        Please install Node.js/npm and run 'npm run build' inside frontend\." -ForegroundColor Yellow
        exit 1
    }
    Push-Location (Join-Path $root "frontend")
    try {
        & npm run build
    } finally {
        Pop-Location
    }
    if (-not (Test-Path $distIndex)) {
        Write-Host "[ERROR] Frontend build failed; dist\index.html was not generated." -ForegroundColor Red
        exit 1
    }
    Write-Host "[5/6] Frontend production distribution successfully built."
} else {
    Write-Host "[5/6] Frontend production distribution verified in frontend\dist"
}

if ($ValidateOnly) {
    Write-Host ""
    Write-Host "[SUCCESS] Pre-flight validation passed. Environment is ready for production startup." -ForegroundColor Green
    exit 0
}

# 6. Check Port Ownership & Prevent Duplicate Instances
function Get-ZezEditHealth {
    param(
        [string]$Url,
        [int]$TimeoutSec = 5
    )
    try {
        $check = Invoke-RestMethod -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSec -ErrorAction Stop
        return $check
    } catch {
        return $null
    }
}

$healthUrl = "http://${HostAddress}:${Port}/health"
$conn = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Where-Object { ($_.RemotePort -eq 0 -or $_.State -eq 'Listen') -and $_.OwningProcess -gt 0 }

if ($conn) {
    $owningPid = $conn[0].OwningProcess
    $p = if ($owningPid) { Get-Process -Id $owningPid -ErrorAction SilentlyContinue } else { $null }
    $cim = if ($owningPid) { Get-CimInstance Win32_Process -Filter "ProcessId = $owningPid" -ErrorAction SilentlyContinue } else { $null }
    $cmd = if ($cim) { $cim.CommandLine } else { "" }

    # Check if existing listener belongs to this ZEZEdit installation
    $isZezEdit = ($cmd -like "*app.main:app*")

    # Also probe health endpoint to confirm responsiveness
    $probe = Get-ZezEditHealth -Url $healthUrl -TimeoutSec 5
    $isHealthy = ($probe -ne $null -and ($probe.status -in @("ready", "ready_with_optional_unavailable", "degraded")))

    if ($isZezEdit -and $isHealthy) {
        Write-Host ""
        Write-Host "=====================================================================" -ForegroundColor Green
        Write-Host "  ZEZEdit is already running and healthy on http://${HostAddress}:${Port}" -ForegroundColor Green
        Write-Host "  PID: $owningPid (No duplicate instance started)" -ForegroundColor Green
        Write-Host "=====================================================================" -ForegroundColor Green
        Write-Host ""
        if (-not $NoBrowser) {
            Start-Process "http://${HostAddress}:${Port}"
        }
        exit 0
    } else {
        $procDesc = if ($p) { "'$($p.ProcessName)' (PID: $owningPid)" } elseif ($owningPid) { "PID: $owningPid" } else { "another application" }
        Write-Host ""
        Write-Host "[ERROR] Port $Port is already in use by process $procDesc." -ForegroundColor Red
        if ($cmd) {
            Write-Host "        Command line: $cmd" -ForegroundColor Yellow
        }
        Write-Host "        ZEZEdit cannot bind to port $Port while another application occupies it." -ForegroundColor Yellow
        Write-Host "        Please stop the conflicting process or choose a different port." -ForegroundColor Yellow
        exit 1
    }
}

# 7. Check and Clean Stale Ownership Files
$tempDir = Join-Path $root "storage\temp"
$logsDir = Join-Path $root "storage\logs"
if (-not (Test-Path $tempDir)) { New-Item -ItemType Directory -Path $tempDir -Force | Out-Null }
if (-not (Test-Path $logsDir)) { New-Item -ItemType Directory -Path $logsDir -Force | Out-Null }

$pidFile = Join-Path $tempDir "zezedit.pid"
$procMetaFile = Join-Path $tempDir "zezedit_process.json"

if (Test-Path $procMetaFile) {
    try {
        $meta = Get-Content $procMetaFile -Raw | ConvertFrom-Json
        $oldPid = [int]$meta.pid
        $oldProc = Get-Process -Id $oldPid -ErrorAction SilentlyContinue
        if (-not $oldProc) {
            # Stale PID file from previous crashed session: safe to clean
            Remove-Item $procMetaFile -Force -ErrorAction SilentlyContinue
            Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
        }
    } catch {
        Remove-Item $procMetaFile -Force -ErrorAction SilentlyContinue
    }
}

# 8. Start FastAPI Production Server in Background (Detached from parent job object)
Write-Host "[6/6] Starting FastAPI production server on http://${HostAddress}:${Port}..."
$stdoutLog = Join-Path $logsDir "launcher_stdout.log"
$stderrLog = Join-Path $logsDir "launcher_stderr.log"
$backendDir = Join-Path $root "backend"

$cmdLine = "cmd.exe /c `"set PYTHONUTF8=1&& set PYTHONIOENCODING=utf-8&& `"$pythonExe`" -m uvicorn app.main:app --host $HostAddress --port $Port > `"$stdoutLog`" 2> `"$stderrLog`"`""
$createResult = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
    CommandLine = $cmdLine
    CurrentDirectory = $backendDir
}

if ($createResult.ReturnValue -ne 0 -or -not $createResult.ProcessId) {
    Write-Host "[ERROR] Failed to spawn FastAPI server process (Return code: $($createResult.ReturnValue))." -ForegroundColor Red
    exit 1
}

$spawnedPid = [int]$createResult.ProcessId

# Record Structured Process Ownership
Set-Content -Path $pidFile -Value $spawnedPid -Force
$ownerData = @{
    pid = $spawnedPid
    project_root = $root
    port = $Port
    host = $HostAddress
    start_time = (Get-Date -Format o)
    role = "production_server"
    python_exe = $pythonExe
    command_line = $cmdLine
}
$ownerData | ConvertTo-Json -Depth 4 | Set-Content -Path $procMetaFile -Force

Write-Host "Server process spawned (PID: $spawnedPid). Polling health check..."

# 9. Verify Readiness via Health Endpoint
$ready = $false
$failedStatus = $null

for ($i = 0; $i -lt $TimeoutSeconds; $i++) {
    Start-Sleep -Seconds 1

    # Check if process died prematurely
    $alive = Get-Process -Id $spawnedPid -ErrorAction SilentlyContinue
    if (-not $alive) {
        Write-Host ""
        Write-Host "[ERROR] ZEZEdit process (PID: $spawnedPid) exited prematurely." -ForegroundColor Red
        if (Test-Path $stderrLog) {
            Write-Host "--- Recent Error Output ---" -ForegroundColor Yellow
            Get-Content $stderrLog -Tail 20
            Write-Host "---------------------------" -ForegroundColor Yellow
        }
        exit 1
    }

    $check = Get-ZezEditHealth -Url $healthUrl -TimeoutSec 5
    if ($check) {
        if ($check.status -in @("ready", "ready_with_optional_unavailable", "degraded")) {
            $ready = $true
            break
        } elseif ($check.status -eq "failed") {
            $failedStatus = "Health check explicitly reported failed status."
            break
        }
    }
}

if ($failedStatus) {
    Write-Host ""
    Write-Host "[ERROR] $failedStatus" -ForegroundColor Red
    if (Test-Path $stderrLog) {
        Get-Content $stderrLog -Tail 15
    }
    exit 1
}

if ($ready) {
    Write-Host ""
    Write-Host "=====================================================================" -ForegroundColor Green
    Write-Host "  ZEZEdit 2.0 is READY in Windows production mode!                   " -ForegroundColor Green
    Write-Host "  Local Address: http://${HostAddress}:${Port}                       " -ForegroundColor Green
    Write-Host "  Process PID:   $spawnedPid                                         " -ForegroundColor Green
    Write-Host "  To stop:       Run Stop-ZEZEdit.bat or Stop-ZEZEdit.ps1            " -ForegroundColor Green
    Write-Host "=====================================================================" -ForegroundColor Green
    Write-Host ""
    if (-not $NoBrowser) {
        Write-Host "Opening default browser..."
        Start-Process "http://${HostAddress}:${Port}"
    }
    exit 0
} else {
    Write-Host ""
    Write-Host "[ERROR] Server did not become ready within $TimeoutSeconds seconds." -ForegroundColor Red
    if (Test-Path $stderrLog) {
        Write-Host "Recent error output:" -ForegroundColor Yellow
        Get-Content $stderrLog -Tail 15
    }
    exit 1
}
