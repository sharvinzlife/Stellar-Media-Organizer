@echo off
REM =============================================================================
REM Media Organizer Pro - Windows Batch Launcher
REM =============================================================================

echo.
echo =============================================
echo   Media Organizer Pro - Dev Server
echo =============================================
echo.

REM Check if PowerShell is available
where powershell >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo PowerShell is required but not found.
    echo Please install PowerShell or run start_dev.ps1 directly.
    pause
    exit /b 1
)

REM Run the PowerShell script
powershell -ExecutionPolicy Bypass -File "%~dp0start_dev.ps1"

pause
