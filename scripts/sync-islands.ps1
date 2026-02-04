#!/usr/bin/env pwsh
# Sync JavaScript Islands from schedulezero-islands to Python repo

param(
    [switch]$Build = $false,
    [switch]$Force = $false
)

$ErrorActionPreference = "Stop"

# Paths
$IslandsRepo = "..\schdulezero-islands"
$DistDir = Join-Path $IslandsRepo "dist"
$MicrositesDir = "src\schedule_zero\microsites"

# Color output helpers
function Write-Step($msg) { Write-Host "➜ $msg" -ForegroundColor Cyan }
function Write-Success($msg) { Write-Host "✓ $msg" -ForegroundColor Green }
function Write-Error($msg) { Write-Host "✗ $msg" -ForegroundColor Red }
function Write-Warning($msg) { Write-Host "⚠ $msg" -ForegroundColor Yellow }

# Check if islands repo exists
if (-not (Test-Path $IslandsRepo)) {
    Write-Error "Islands repo not found at: $IslandsRepo"
    Write-Host "Expected path: $(Resolve-Path '..')\\schedulezero-islands"
    exit 1
}

# Build if requested
if ($Build) {
    Write-Step "Building islands project..."
    Push-Location $IslandsRepo
    try {
        # Activate Node.js environment first
        if (Test-Path ".\activate_node.ps1") {
            . .\activate_node.ps1
        }
        pnpm run build
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Build failed"
            exit 1
        }
        Write-Success "Build completed"
    }
    finally {
        Pop-Location
    }
}

# Check if dist directory exists
if (-not (Test-Path $DistDir)) {
    Write-Error "Dist directory not found: $DistDir"
    Write-Host "Run with -Build flag to build the islands project first"
    exit 1
}

# Component mapping: dist files -> microsite destinations
$ComponentMap = @{
    # Vanilla components (shared across microsites)
    "vanilla/connection-status.min.js" = @(
        "$MicrositesDir\sz_dash\assets\js\components\vanilla"
        "$MicrositesDir\sz_schedules\assets\js\components\vanilla"
    )
    "vanilla/copy-button.min.js" = @(
        "$MicrositesDir\sz_dash\assets\js\components\vanilla"
        "$MicrositesDir\sz_schedules\assets\js\components\vanilla"
    )
    "vanilla/sz-flash.min.js" = @(
        "$MicrositesDir\sz_dash\assets\js\components\vanilla"
        "$MicrositesDir\sz_schedules\assets\js\components\vanilla"
    )
    
    # Vuetify components (shared across microsites)
    "vuetify/schedule-grid.min.js" = @(
        "$MicrositesDir\sz_dash\assets\js\components\vuetify"
        "$MicrositesDir\sz_schedules\assets\js\components\vuetify"
    )
    "vuetify/schedule-form.min.js" = @(
        "$MicrositesDir\sz_dash\assets\js\components\vuetify"
        "$MicrositesDir\sz_schedules\assets\js\components\vuetify"
    )
    "vuetify/handler-grid.min.js" = @(
        "$MicrositesDir\sz_dash\assets\js\components\vuetify"
        "$MicrositesDir\sz_schedules\assets\js\components\vuetify"
    )
    "vuetify/execution-log-grid.min.js" = @(
        "$MicrositesDir\sz_dash\assets\js\components\vuetify"
        "$MicrositesDir\sz_schedules\assets\js\components\vuetify"
    )
}

# Sync components
Write-Step "Syncing components..."
$CopiedCount = 0
$SkippedCount = 0
$ErrorCount = 0

foreach ($sourcePath in $ComponentMap.Keys) {
    $sourceFile = Join-Path $DistDir $sourcePath
    
    if (-not (Test-Path $sourceFile)) {
        Write-Warning "Source file not found: $sourcePath"
        $ErrorCount++
        continue
    }
    
    $destinations = $ComponentMap[$sourcePath]
    foreach ($destDir in $destinations) {
        # Create destination directory if needed
        if (-not (Test-Path $destDir)) {
            New-Item -ItemType Directory -Path $destDir -Force | Out-Null
        }
        
        $destFile = Join-Path $destDir (Split-Path $sourcePath -Leaf)
        
        # Check if copy is needed
        $needsCopy = $Force
        if (-not $needsCopy) {
            if (-not (Test-Path $destFile)) {
                $needsCopy = $true
            }
            else {
                $sourceTime = (Get-Item $sourceFile).LastWriteTime
                $destTime = (Get-Item $destFile).LastWriteTime
                $needsCopy = $sourceTime -gt $destTime
            }
        }
        
        if ($needsCopy) {
            try {
                Copy-Item $sourceFile $destFile -Force
                Write-Host "  ✓ $(Split-Path $sourcePath -Leaf) → $destDir" -ForegroundColor Gray
                $CopiedCount++
            }
            catch {
                Write-Error "Failed to copy $(Split-Path $sourcePath -Leaf): $_"
                $ErrorCount++
            }
        }
        else {
            $SkippedCount++
        }
    }
}

# Summary
Write-Host ""
Write-Success "Sync complete!"
Write-Host "  Copied: $CopiedCount files"
if ($SkippedCount -gt 0) {
    Write-Host "  Skipped: $SkippedCount files (already up-to-date)" -ForegroundColor Gray
}
if ($ErrorCount -gt 0) {
    Write-Warning "Errors: $ErrorCount files"
    exit 1
}
