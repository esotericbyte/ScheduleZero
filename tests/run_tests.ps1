#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Run ScheduleZero integration tests

.DESCRIPTION
    This script helps run the ScheduleZero test suite by:
    1. Checking that the server is running
    2. Checking that the test handler is running
    3. Running pytest with appropriate options

.PARAMETER Watch
    Run tests in watch mode (re-run on file changes)

.PARAMETER Verbose
    Run tests with verbose output

.PARAMETER Test
    Run a specific test by name

.EXAMPLE
    .\run_tests.ps1
    Run all tests

.EXAMPLE
    .\run_tests.ps1 -Verbose
    Run all tests with verbose output

.EXAMPLE
    .\run_tests.ps1 -Test test_run_now_write_file
    Run a specific test
#>

param(
    [switch]$Watch,
    [switch]$Verbose,
    [string]$Test
)

# Check if server is running
Write-Host "Checking ScheduleZero server..." -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8888/api/health" -TimeoutSec 5 -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "✓ Server is running" -ForegroundColor Green
    }
} catch {
    Write-Host "✗ Server is not running on http://127.0.0.1:8888" -ForegroundColor Red
    Write-Host "  Please start the server first:" -ForegroundColor Yellow
    Write-Host "  poetry run python -m schedule_zero.tornado_app_server" -ForegroundColor Yellow
    exit 1
}

# Check if test handler is registered
Write-Host "Checking test handler registration..." -ForegroundColor Cyan
try {
    $response = Invoke-RestMethod -Uri "http://127.0.0.1:8888/api/handlers" -TimeoutSec 5
    $testHandler = $response.handlers | Where-Object { $_.id -eq "test-handler-001" }
    
    if ($testHandler) {
        Write-Host "✓ Test handler is registered" -ForegroundColor Green
        Write-Host "  Address: $($testHandler.address)" -ForegroundColor Gray
        Write-Host "  Methods: $($testHandler.methods -join ', ')" -ForegroundColor Gray
    } else {
        Write-Host "✗ Test handler is not registered" -ForegroundColor Red
        Write-Host "  Please start the test handler first:" -ForegroundColor Yellow
        Write-Host "  poetry run python tests/test_handler.py" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "✗ Failed to check handler registration" -ForegroundColor Red
    Write-Host "  Error: $_" -ForegroundColor Red
    exit 1
}

# Build pytest command
$pytestArgs = @("tests/test_scheduled_jobs.py")

if ($Verbose) {
    $pytestArgs += "-v"
    $pytestArgs += "-s"
}

if ($Test) {
    $pytestArgs += "-k"
    $pytestArgs += $Test
}

if ($Watch) {
    # Note: Requires pytest-watch to be installed
    Write-Host "`nRunning tests in watch mode..." -ForegroundColor Cyan
    Write-Host "Command: poetry run ptw $($pytestArgs -join ' ')" -ForegroundColor Gray
    poetry run ptw @pytestArgs
} else {
    Write-Host "`nRunning tests..." -ForegroundColor Cyan
    Write-Host "Command: poetry run pytest $($pytestArgs -join ' ')" -ForegroundColor Gray
    Write-Host ""
    
    poetry run pytest @pytestArgs
    
    $exitCode = $LASTEXITCODE
    
    Write-Host ""
    if ($exitCode -eq 0) {
        Write-Host "✓ All tests passed!" -ForegroundColor Green
    } else {
        Write-Host "✗ Some tests failed" -ForegroundColor Red
    }
    
    exit $exitCode
}
