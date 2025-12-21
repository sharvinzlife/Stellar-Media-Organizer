@echo off
REM =============================================================================
REM Media Organizer Pro - Windows Launcher (no Docker)
REM =============================================================================

echo.
echo =============================================
echo   Media Organizer Pro (Local)
echo =============================================
echo.

where powershell >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo PowerShell is required but not found.
    echo Please install PowerShell or run start.ps1 directly.
    pause
    exit /b 1
)

powershell -ExecutionPolicy Bypass -File "%~dp0start.ps1"

pause


