# Media Organizer Pro - Local (no Docker) Start Script (Windows)
# Starts: GPU service (8888) + Backend API (8000) + Frontend (5173)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

Write-Host ""
Write-Host "🎬 Media Organizer Pro (Local)" -ForegroundColor Cyan
Write-Host "==============================" -ForegroundColor Cyan
Write-Host ""

$RunDir = Join-Path $ProjectRoot ".run"
$PidFile = Join-Path $RunDir "pids"
$GpuLog = Join-Path $RunDir "gpu.log"
$ApiLog = Join-Path $RunDir "api.log"
$FrontendLog = Join-Path $RunDir "frontend.log"

New-Item -ItemType Directory -Force -Path $RunDir | Out-Null

function Stop-Previous {
    if (-not (Test-Path $PidFile)) {
        return
    }

    Write-Host "Stopping previous run..." -ForegroundColor Yellow

    foreach ($line in Get-Content $PidFile) {
        if ($line -match "^[A-Z_]+PID=(\d+)$") {
            $pid = [int]$Matches[1]
            try {
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            }
            catch {
                # ignore
            }
        }
    }

    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
}

function Get-PythonSpec {
    if (Get-Command "py" -ErrorAction SilentlyContinue) {
        try {
            & py -3 --version *> $null
            if ($LASTEXITCODE -eq 0) {
                return @{ Command = "py"; Args = @("-3") }
            }
        }
        catch {
            # ignore
        }
    }

    if (Get-Command "python" -ErrorAction SilentlyContinue) {
        return @{ Command = "python"; Args = @() }
    }

    if (Get-Command "python3" -ErrorAction SilentlyContinue) {
        return @{ Command = "python3"; Args = @() }
    }

    throw "Python not found. Install Python 3.10+ and try again."
}

function Get-FrontendPm {
    if (Get-Command "pnpm" -ErrorAction SilentlyContinue) {
        return @{ Name = "pnpm"; Path = (Get-Command "pnpm").Source }
    }

    if (Get-Command "npm" -ErrorAction SilentlyContinue) {
        return @{ Name = "npm"; Path = (Get-Command "npm").Source }
    }

    throw "npm/pnpm not found. Install Node.js (includes npm) and try again."
}

function Ensure-PythonVenv {
    param(
        [Parameter(Mandatory = $true)][string]$PythonCommand,
        [Parameter(Mandatory = $true)][string[]]$PythonArgs
    )

    $venvDir = Join-Path $ProjectRoot ".venv"
    $venvPython = Join-Path $venvDir "Scripts\python.exe"
    $depsMarker = Join-Path $venvDir ".deps-installed"

    if (-not (Test-Path $venvPython)) {
        Write-Host "Creating Python venv (.venv)..." -ForegroundColor Cyan
        & $PythonCommand @PythonArgs -m venv $venvDir
    }

    if (-not (Test-Path $depsMarker)) {
        Write-Host "Installing Python dependencies..." -ForegroundColor Cyan
        & $venvPython -m pip install --upgrade pip *> $null
        & $venvPython -m pip install -r (Join-Path $ProjectRoot "requirements.txt")
        New-Item -ItemType File -Force -Path $depsMarker | Out-Null
    }

    return $venvPython
}

function Ensure-FrontendDeps {
    param(
        [Parameter(Mandatory = $true)][hashtable]$Pm
    )

    $frontendDir = Join-Path $ProjectRoot "webapp\frontend"
    $nodeModules = Join-Path $frontendDir "node_modules"

    if (-not (Test-Path $nodeModules)) {
        Write-Host "Installing frontend dependencies with $($Pm.Name)..." -ForegroundColor Cyan
        Push-Location $frontendDir
        try {
            if ($Pm.Name -eq "pnpm") {
                & $Pm.Path install
            }
            else {
                & $Pm.Path install
            }
        }
        finally {
            Pop-Location
        }
    }

    return $frontendDir
}

function Write-Pids {
    param(
        [Parameter(Mandatory = $true)][int]$GpuPid,
        [Parameter(Mandatory = $true)][int]$ApiPid,
        [Parameter(Mandatory = $true)][int]$FrontendPid
    )

    @"
GPU_PID=$GpuPid
API_PID=$ApiPid
FRONTEND_PID=$FrontendPid
"@ | Set-Content -Path $PidFile -Encoding ascii
}

function Stop-Started {
    param(
        [Parameter()][int]$GpuPid = 0,
        [Parameter()][int]$ApiPid = 0,
        [Parameter()][int]$FrontendPid = 0
    )

    Write-Host ""
    Write-Host "Stopping services..." -ForegroundColor Yellow

    foreach ($pid in @($FrontendPid, $ApiPid, $GpuPid)) {
        if ($pid -le 0) { continue }
        try {
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        }
        catch {
            # ignore
        }
    }

    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    Write-Host "Done!" -ForegroundColor Green
}

Stop-Previous

$pythonSpec = Get-PythonSpec
$venvPython = Ensure-PythonVenv -PythonCommand $pythonSpec.Command -PythonArgs $pythonSpec.Args
$pm = Get-FrontendPm
$frontendDir = Ensure-FrontendDeps -Pm $pm

# Reset logs
Set-Content -Path $GpuLog -Value "" -Encoding utf8
Set-Content -Path $ApiLog -Value "" -Encoding utf8
Set-Content -Path $FrontendLog -Value "" -Encoding utf8

Write-Host "Starting GPU Service (port 8888)..." -ForegroundColor Cyan
$gpuProc = Start-Process -FilePath $venvPython -ArgumentList @((Join-Path $ProjectRoot "gpu_converter_service.py")) -RedirectStandardOutput $GpuLog -RedirectStandardError $GpuLog -PassThru -NoNewWindow

Start-Sleep -Seconds 1

Write-Host "Starting Backend API (port 8000)..." -ForegroundColor Cyan
$apiProc = Start-Process -FilePath $venvPython -ArgumentList @((Join-Path $ProjectRoot "standalone_backend.py")) -RedirectStandardOutput $ApiLog -RedirectStandardError $ApiLog -PassThru -NoNewWindow

Start-Sleep -Seconds 1

Write-Host "Starting Frontend (port 5173)..." -ForegroundColor Cyan
$frontendProc = Start-Process -FilePath $pm.Path -ArgumentList @("run", "dev") -WorkingDirectory $frontendDir -RedirectStandardOutput $FrontendLog -RedirectStandardError $FrontendLog -PassThru -NoNewWindow

Write-Pids -GpuPid $gpuProc.Id -ApiPid $apiProc.Id -FrontendPid $frontendProc.Id

Write-Host ""
Write-Host "=============================================" -ForegroundColor Green
Write-Host "  🚀 All services started!" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Frontend:  http://localhost:5173"
Write-Host "  Backend:   http://localhost:8000"
Write-Host "  GPU:       http://localhost:8888"
Write-Host ""
Write-Host "  Logs:      $GpuLog | $ApiLog | $FrontendLog"
Write-Host ""
Write-Host "Press Ctrl+C to stop all services" -ForegroundColor Yellow
Write-Host ""

try {
    while ($true) {
        if ($gpuProc.HasExited) { throw "GPU service exited. See logs at $GpuLog" }
        if ($apiProc.HasExited) { throw "Backend API exited. See logs at $ApiLog" }
        if ($frontendProc.HasExited) { throw "Frontend exited. See logs at $FrontendLog" }

        Start-Sleep -Seconds 2
    }
}
catch {
    # Ctrl+C will often throw PipelineStoppedException; don't print noisy errors for that case.
    if ($_.Exception.GetType().Name -ne "PipelineStoppedException") {
        Write-Host $_.Exception.Message -ForegroundColor Red
    }
}
finally {
    Stop-Started -GpuPid $gpuProc.Id -ApiPid $apiProc.Id -FrontendPid $frontendProc.Id
}


