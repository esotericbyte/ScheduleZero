#!/usr/bin/env pwsh
# Start ScheduleZero Server with PID Management

param(
    [string]$Deployment = "default"
)

$ErrorActionPreference = "Stop"

# Paths
$RootDir = Split-Path -Parent $PSScriptRoot
$PidDir = Join-Path $RootDir "deployments\$Deployment\pids"
$ServerPidFile = Join-Path $PidDir "server.pid"

# Ensure PID directory exists
New-Item -ItemType Directory -Path $PidDir -Force | Out-Null

# Check if server is already running
if (Test-Path $ServerPidFile) {
    $OldPid = Get-Content $ServerPidFile -Raw
    $OldPid = $OldPid.Trim()
    
    try {
        $Process = Get-Process -Id $OldPid -ErrorAction Stop
        Write-Host "✓ Server already running (PID: $OldPid)" -ForegroundColor Green
        Write-Host "  Web: http://127.0.0.1:8888"
        Write-Host "  ZMQ: tcp://127.0.0.1:4242"
        exit 0
    }
    catch {
        # Process not running, clean up stale PID file
        Remove-Item $ServerPidFile -Force
        Write-Host "⚠ Cleaned up stale PID file" -ForegroundColor Yellow
    }
}

# Set deployment environment variable
$env:SCHEDULEZERO_DEPLOYMENT = $Deployment

Write-Host "➜ Starting ScheduleZero Server (Deployment: $Deployment)" -ForegroundColor Cyan

# Start server in background
$Job = Start-Job -ScriptBlock {
    param($RootDir, $Deployment)
    Set-Location $RootDir
    $env:SCHEDULEZERO_DEPLOYMENT = $Deployment
    poetry run python -m schedule_zero.tornado_app_server
} -ArgumentList $RootDir, $Deployment

# Wait for job to start and get the actual Python process PID
Start-Sleep -Seconds 2

# Find the Python process (child of the job)
$PythonProcess = Get-Process python -ErrorAction SilentlyContinue | 
    Where-Object { $_.CommandLine -like "*tornado_app_server*" } |
    Select-Object -First 1

if ($PythonProcess) {
    $Pid = $PythonProcess.Id
    $Pid | Out-File -FilePath $ServerPidFile -NoNewline
    Write-Host "✓ Server started (PID: $Pid)" -ForegroundColor Green
    Write-Host "  Web: http://127.0.0.1:8888" -ForegroundColor Gray
    Write-Host "  ZMQ: tcp://127.0.0.1:4242" -ForegroundColor Gray
    Write-Host "  PID file: $ServerPidFile" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Stop with: .\scripts\stop-server.ps1 -Deployment $Deployment" -ForegroundColor Yellow
}
else {
    Write-Host "✗ Failed to start server" -ForegroundColor Red
    Remove-Job -Job $Job -Force
    exit 1
}
