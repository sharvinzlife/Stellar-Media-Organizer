# =============================================================================
# Media Organizer Pro - Cross-Platform Development Startup Script (Windows)
# =============================================================================

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $ScriptDir "backend"
$FrontendDir = Join-Path $ScriptDir "frontend"

$BackendJob = $null
$FrontendJob = $null

function Write-Header {
    Write-Host ""
    Write-Host "=============================================" -ForegroundColor Blue
    Write-Host "  🎬 Media Organizer Pro - Dev Server" -ForegroundColor Blue
    Write-Host "=============================================" -ForegroundColor Blue
    Write-Host ""
}

function Write-Success {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠️  $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor Red
}

function Write-Info {
    param([string]$Message)
    Write-Host "ℹ️  $Message" -ForegroundColor Cyan
}

function Test-Python {
    $pythonCmd = $null
    
    if (Get-Command "python" -ErrorAction SilentlyContinue) {
        $pythonCmd = "python"
    }
    elseif (Get-Command "python3" -ErrorAction SilentlyContinue) {
        $pythonCmd = "python3"
    }
    else {
        Write-Error "Python is not installed. Please install Python 3.8+."
        exit 1
    }
    
    $version = & $pythonCmd --version 2>&1
    Write-Success "Python found: $version"
    return $pythonCmd
}

function Test-Node {
    if (-not (Get-Command "node" -ErrorAction SilentlyContinue)) {
        Write-Error "Node.js is not installed. Please install Node.js 18+."
        exit 1
    }
    $version = node --version
    Write-Success "Node.js found: $version"
}

function Test-Npm {
    if (-not (Get-Command "npm" -ErrorAction SilentlyContinue)) {
        Write-Error "npm is not installed. Please install npm."
        exit 1
    }
    $version = npm --version
    Write-Success "npm found: $version"
}

function Setup-Backend {
    param([string]$PythonCmd)
    
    Write-Info "Setting up backend..."
    Set-Location $BackendDir
    
    # Create virtual environment if it doesn't exist
    $venvPath = Join-Path $BackendDir "venv"
    if (-not (Test-Path $venvPath)) {
        Write-Info "Creating Python virtual environment..."
        & $PythonCmd -m venv venv
    }
    
    # Activate virtual environment and install dependencies
    $activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
    if (Test-Path $activateScript) {
        & $activateScript
    }
    
    Write-Info "Installing backend dependencies..."
    & pip install -r requirements.txt --quiet
    
    Write-Success "Backend setup complete."
}

function Setup-Frontend {
    Write-Info "Setting up frontend..."
    Set-Location $FrontendDir
    
    # Install dependencies if node_modules doesn't exist
    $nodeModules = Join-Path $FrontendDir "node_modules"
    if (-not (Test-Path $nodeModules)) {
        Write-Info "Installing frontend dependencies..."
        npm install
    }
    
    Write-Success "Frontend setup complete."
}

function Start-Servers {
    param([string]$PythonCmd)
    
    Write-Info "Starting backend server..."
    $script:BackendJob = Start-Job -ScriptBlock {
        param($dir, $python)
        Set-Location $dir
        $venvPython = Join-Path $dir "venv\Scripts\python.exe"
        if (Test-Path $venvPython) {
            & $venvPython -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
        } else {
            & $python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
        }
    } -ArgumentList $BackendDir, $PythonCmd
    
    Write-Success "Backend started (Job ID: $($BackendJob.Id))"
    
    Start-Sleep -Seconds 2
    
    Write-Info "Starting frontend server..."
    $script:FrontendJob = Start-Job -ScriptBlock {
        param($dir)
        Set-Location $dir
        npm run dev
    } -ArgumentList $FrontendDir
    
    Write-Success "Frontend started (Job ID: $($FrontendJob.Id))"
}

function Stop-Servers {
    Write-Host ""
    Write-Info "Shutting down servers..."
    
    if ($script:BackendJob) {
        Stop-Job -Job $script:BackendJob -ErrorAction SilentlyContinue
        Remove-Job -Job $script:BackendJob -Force -ErrorAction SilentlyContinue
    }
    
    if ($script:FrontendJob) {
        Stop-Job -Job $script:FrontendJob -ErrorAction SilentlyContinue
        Remove-Job -Job $script:FrontendJob -Force -ErrorAction SilentlyContinue
    }
    
    # Also kill any remaining processes on the ports
    Get-Process -Name "node" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*uvicorn*" } | Stop-Process -Force -ErrorAction SilentlyContinue
    
    Write-Success "Servers stopped."
}

# Register cleanup on script exit
Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action { Stop-Servers } | Out-Null

# Main execution
try {
    Write-Header
    
    Write-Info "Checking prerequisites..."
    $pythonCmd = Test-Python
    Test-Node
    Test-Npm
    Write-Host ""
    
    Setup-Backend -PythonCmd $pythonCmd
    Setup-Frontend
    Write-Host ""
    
    Start-Servers -PythonCmd $pythonCmd
    
    Write-Host ""
    Write-Host "=============================================" -ForegroundColor Green
    Write-Host "  🚀 Servers are running!" -ForegroundColor Green
    Write-Host "=============================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Frontend:  " -NoNewline -ForegroundColor Cyan
    Write-Host "http://localhost:5173"
    Write-Host "  Backend:   " -NoNewline -ForegroundColor Cyan
    Write-Host "http://localhost:8000"
    Write-Host "  API Docs:  " -NoNewline -ForegroundColor Cyan
    Write-Host "http://localhost:8000/docs"
    Write-Host ""
    Write-Host "  Press Ctrl+C to stop all servers" -ForegroundColor Yellow
    Write-Host ""
    
    # Keep script running and show logs
    while ($true) {
        if ($BackendJob.State -eq "Failed") {
            Write-Error "Backend server crashed!"
            Receive-Job -Job $BackendJob
        }
        if ($FrontendJob.State -eq "Failed") {
            Write-Error "Frontend server crashed!"
            Receive-Job -Job $FrontendJob
        }
        Start-Sleep -Seconds 5
    }
}
catch {
    Write-Error $_.Exception.Message
}
finally {
    Stop-Servers
}
