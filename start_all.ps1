#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Start all ScheduleZero components in order

.DESCRIPTION
    This script starts the ScheduleZero server and test handler in the correct order,
    managing them as background jobs that can be monitored and stopped together.

.PARAMETER IncludeTests
    Also run the test suite after starting the components

.EXAMPLE
    .\start_all.ps1
    Start server and test handler

.EXAMPLE
    .\start_all.ps1 -IncludeTests
    Start components and run tests
#>

param(
    [switch]$IncludeTests
)

$ErrorActionPreference = "Stop"

# Store job information
$jobs = @()

function Stop-AllJobs {
    Write-Host "`nStopping all components..." -ForegroundColor Yellow
    
    foreach ($job in $jobs) {
        if ($job.State -eq 'Running') {
            Write-Host "  Stopping $($job.Name)..." -ForegroundColor Gray
            Stop-Job $job
            Remove-Job $job
        }
    }
    
    Write-Host "All components stopped." -ForegroundColor Green
}

# Register cleanup on Ctrl+C
Register-EngineEvent PowerShell.Exiting -Action {
    Stop-AllJobs
}

try {
    Write-Host "=== Starting ScheduleZero Components ===" -ForegroundColor Cyan
    Write-Host ""
    
    # 1. Start the server
    Write-Host "1. Starting ScheduleZero Server..." -ForegroundColor Green
    $serverJob = Start-Job -Name "ScheduleZero-Server" -ScriptBlock {
        Set-Location $using:PWD
        poetry run python -m schedule_zero.tornado_app_server
    }
    $jobs += $serverJob
    Write-Host "   Server starting (Job ID: $($serverJob.Id))" -ForegroundColor Gray
    
    # Wait for server to be ready
    Write-Host "   Waiting for server to start..." -ForegroundColor Gray
    $maxWait = 30
    $waited = 0
    $serverReady = $false
    
    while ($waited -lt $maxWait) {
        Start-Sleep -Seconds 1
        $waited++
        
        try {
            $response = Invoke-WebRequest -Uri "http://127.0.0.1:8888/api/health" -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                $serverReady = $true
                break
            }
        } catch {
            # Server not ready yet
        }
        
        # Check if job failed
        if ($serverJob.State -ne 'Running') {
            Write-Host "   ✗ Server job failed to start!" -ForegroundColor Red
            Receive-Job $serverJob
            throw "Server failed to start"
        }
    }
    
    if (-not $serverReady) {
        Write-Host "   ✗ Server did not respond within ${maxWait}s" -ForegroundColor Red
        throw "Server startup timeout"
    }
    
    Write-Host "   ✓ Server is ready!" -ForegroundColor Green
    Write-Host ""
    
    # 2. Start the test handler
    Write-Host "2. Starting Test Handler..." -ForegroundColor Green
    $handlerJob = Start-Job -Name "Test-Handler" -ScriptBlock {
        Set-Location $using:PWD
        poetry run python tests/test_handler.py
    }
    $jobs += $handlerJob
    Write-Host "   Test handler starting (Job ID: $($handlerJob.Id))" -ForegroundColor Gray
    
    # Wait for handler to register
    Write-Host "   Waiting for handler to register..." -ForegroundColor Gray
    $maxWait = 20
    $waited = 0
    $handlerRegistered = $false
    
    while ($waited -lt $maxWait) {
        Start-Sleep -Seconds 1
        $waited++
        
        try {
            $response = Invoke-RestMethod -Uri "http://127.0.0.1:8888/api/handlers" -TimeoutSec 2 -ErrorAction SilentlyContinue
            $handler = $response.handlers | Where-Object { $_.id -eq "test-handler-001" }
            if ($handler) {
                $handlerRegistered = $true
                break
            }
        } catch {
            # Not registered yet
        }
        
        # Check if job failed
        if ($handlerJob.State -ne 'Running') {
            Write-Host "   ✗ Handler job failed!" -ForegroundColor Red
            Receive-Job $handlerJob
            throw "Handler failed to start"
        }
    }
    
    if (-not $handlerRegistered) {
        Write-Host "   ⚠ Handler did not register within ${maxWait}s (may still be trying)" -ForegroundColor Yellow
    } else {
        Write-Host "   ✓ Handler registered successfully!" -ForegroundColor Green
    }
    Write-Host ""
    
    # Show status
    Write-Host "=== Status ===" -ForegroundColor Cyan
    Write-Host "Server:       http://127.0.0.1:8888" -ForegroundColor White
    Write-Host "zerorpc:      tcp://127.0.0.1:4242" -ForegroundColor White
    Write-Host "Test Handler: tcp://127.0.0.1:4244" -ForegroundColor White
    Write-Host ""
    
    # Run tests if requested
    if ($IncludeTests) {
        Write-Host "=== Running Tests ===" -ForegroundColor Cyan
        Write-Host ""
        poetry run pytest tests/test_scheduled_jobs.py -v
        $testExitCode = $LASTEXITCODE
        Write-Host ""
        
        if ($testExitCode -eq 0) {
            Write-Host "✓ All tests passed!" -ForegroundColor Green
        } else {
            Write-Host "✗ Some tests failed (exit code: $testExitCode)" -ForegroundColor Red
        }
        Write-Host ""
    }
    
    # Keep running and show logs
    Write-Host "=== Components Running ===" -ForegroundColor Cyan
    Write-Host "Press Ctrl+C to stop all components" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To view logs:" -ForegroundColor Gray
    Write-Host "  Server:  Receive-Job $($serverJob.Id)" -ForegroundColor Gray
    Write-Host "  Handler: Receive-Job $($handlerJob.Id)" -ForegroundColor Gray
    Write-Host ""
    
    # Monitor jobs
    while ($true) {
        Start-Sleep -Seconds 5
        
        # Check if any job failed
        foreach ($job in $jobs) {
            if ($job.State -eq 'Failed' -or $job.State -eq 'Stopped') {
                Write-Host "`n✗ $($job.Name) has stopped!" -ForegroundColor Red
                Receive-Job $job
                throw "$($job.Name) failed"
            }
        }
    }
    
} catch {
    Write-Host "`nError: $_" -ForegroundColor Red
    Stop-AllJobs
    exit 1
} finally {
    # Cleanup will happen via the registered event
}
