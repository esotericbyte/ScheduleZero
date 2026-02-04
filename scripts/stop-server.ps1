#!/usr/bin/env pwsh
# Stop ScheduleZero Server using PID file

param(
    [string]$Deployment = "default",
    [switch]$Force = $false
)

$ErrorActionPreference = "Stop"

# Paths
$RootDir = Split-Path -Parent $PSScriptRoot
$PidDir = Join-Path $RootDir "deployments\$Deployment\pids"
$ServerPidFile = Join-Path $PidDir "server.pid"

# Check if PID file exists
if (-not (Test-Path $ServerPidFile)) {
    Write-Host "✓ Server not running (no PID file)" -ForegroundColor Gray
    exit 0
}

# Read PID
$Pid = Get-Content $ServerPidFile -Raw
$Pid = $Pid.Trim()

Write-Host "➜ Stopping ScheduleZero Server (Deployment: $Deployment, PID: $Pid)" -ForegroundColor Cyan

# Check if process exists
try {
    $Process = Get-Process -Id $Pid -ErrorAction Stop
    
    # Verify it's our Python process
    if ($Process.ProcessName -ne "python") {
        Write-Host "⚠ Warning: PID $Pid is not a Python process!" -ForegroundColor Yellow
        if (-not $Force) {
            Write-Host "Use -Force to stop anyway" -ForegroundColor Yellow
            exit 1
        }
    }
    
    # Ask for confirmation unless Force
    if (-not $Force) {
        Write-Host "Process: $($Process.ProcessName) (PID: $Pid)"
        $Confirm = Read-Host "Stop this process? (y/N)"
        if ($Confirm -ne "y") {
            Write-Host "Cancelled" -ForegroundColor Gray
            exit 0
        }
    }
    
    # Stop the process gracefully (SIGTERM equivalent)
    Stop-Process -Id $Pid -Force:$Force
    Start-Sleep -Seconds 1
    
    # Check if stopped
    try {
        Get-Process -Id $Pid -ErrorAction Stop | Out-Null
        Write-Host "⚠ Process still running, waiting..." -ForegroundColor Yellow
        Start-Sleep -Seconds 2
        Stop-Process -Id $Pid -Force
    }
    catch {
        # Process stopped
    }
    
    Write-Host "✓ Server stopped" -ForegroundColor Green
}
catch {
    Write-Host "✓ Process not running (cleaning up PID file)" -ForegroundColor Gray
}

# Clean up PID file
Remove-Item $ServerPidFile -Force
