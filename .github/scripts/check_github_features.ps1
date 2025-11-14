# GitHub Repository Feature Checker
# Checks if various GitHub features are enabled for ScheduleZero

param(
    [string]$Owner = "esotericbyte",
    [string]$Repo = "ScheduleZero"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  GitHub Features Check: $Owner/$Repo" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if GitHub CLI is installed
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "⚠️  GitHub CLI (gh) not installed" -ForegroundColor Yellow
    Write-Host "   Install from: https://cli.github.com/" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "📋 Manual check required - visit:" -ForegroundColor Yellow
    Write-Host "   https://github.com/$Owner/$Repo/settings" -ForegroundColor White
    exit 1
}

Write-Host "✅ GitHub CLI found" -ForegroundColor Green
Write-Host ""

# Function to check feature
function Check-Feature {
    param($Name, $Command, $SuccessPattern)
    
    Write-Host "Checking: $Name" -NoNewline
    try {
        $result = Invoke-Expression $Command 2>&1
        if ($result -match $SuccessPattern -or $result -like "*$SuccessPattern*") {
            Write-Host " ✅" -ForegroundColor Green
            return $true
        } else {
            Write-Host " ❌" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host " ⚠️  Error checking" -ForegroundColor Yellow
        return $false
    }
}

# Check repository visibility
Write-Host "📊 Repository Info:" -ForegroundColor Cyan
gh repo view $Owner/$Repo --json name,isPrivate,visibility | ConvertFrom-Json | Format-List
Write-Host ""

# Check various features
Write-Host "🔍 Feature Status:" -ForegroundColor Cyan
Write-Host "==================" -ForegroundColor Cyan

# Issues (always available)
$hasIssues = Check-Feature "Issues" "gh issue list -R $Owner/$Repo -L 1" ".*"
Write-Host "   Issues are always available (free)" -ForegroundColor Gray

# Discussions (FREE - just needs to be enabled)
Write-Host ""
Write-Host "Checking: Discussions" -NoNewline
try {
    $discussions = gh api repos/$Owner/$Repo/discussions -X GET 2>&1
    if ($discussions -notlike "*Not Found*" -and $discussions -notlike "*404*") {
        Write-Host " ✅ Enabled" -ForegroundColor Green
        $hasDiscussions = $true
    } else {
        Write-Host " ❌ Not enabled" -ForegroundColor Red
        Write-Host "   💡 Enable at: https://github.com/$Owner/$Repo/settings" -ForegroundColor Yellow
        Write-Host "      Settings → Features → Discussions checkbox" -ForegroundColor Yellow
        $hasDiscussions = $false
    }
} catch {
    Write-Host " ❌ Not enabled" -ForegroundColor Red
    $hasDiscussions = $false
}

# Wiki (FREE)
Write-Host "Checking: Wiki" -NoNewline
try {
    $wiki = gh api repos/$Owner/$Repo 2>&1 | ConvertFrom-Json
    if ($wiki.has_wiki) {
        Write-Host " ✅ Enabled" -ForegroundColor Green
    } else {
        Write-Host " ❌ Not enabled" -ForegroundColor Red
        Write-Host "   💡 Enable at: https://github.com/$Owner/$Repo/settings" -ForegroundColor Yellow
    }
} catch {
    Write-Host " ⚠️  Error checking" -ForegroundColor Yellow
}

# Projects (FREE for public repos)
Write-Host "Checking: Projects" -NoNewline
try {
    $projects = gh project list --owner $Owner 2>&1
    if ($projects -notlike "*No projects found*") {
        Write-Host " ✅ Available" -ForegroundColor Green
    } else {
        Write-Host " ℹ️  No projects yet (feature available)" -ForegroundColor Cyan
    }
} catch {
    Write-Host " ℹ️  Available (create at /projects)" -ForegroundColor Cyan
}

# Actions (FREE with limits)
Write-Host "Checking: GitHub Actions" -NoNewline
try {
    $workflows = gh workflow list -R $Owner/$Repo 2>&1
    if ($workflows -like "*no workflows*" -or $workflows -eq "") {
        Write-Host " ℹ️  No workflows yet (feature available)" -ForegroundColor Cyan
    } else {
        Write-Host " ✅ Workflows found" -ForegroundColor Green
    }
} catch {
    Write-Host " ℹ️  Available (add .github/workflows/)" -ForegroundColor Cyan
}

# Pages (FREE)
Write-Host "Checking: GitHub Pages" -NoNewline
try {
    $pages = gh api repos/$Owner/$Repo/pages 2>&1
    if ($pages -notlike "*Not Found*" -and $pages -notlike "*404*") {
        $pageInfo = $pages | ConvertFrom-Json
        Write-Host " ✅ Enabled ($($pageInfo.html_url))" -ForegroundColor Green
    } else {
        Write-Host " ❌ Not enabled" -ForegroundColor Red
        Write-Host "   💡 Enable at: https://github.com/$Owner/$Repo/settings/pages" -ForegroundColor Yellow
    }
} catch {
    Write-Host " ❌ Not enabled" -ForegroundColor Red
}

# Security features
Write-Host ""
Write-Host "🔒 Security Features:" -ForegroundColor Cyan
Write-Host "=====================" -ForegroundColor Cyan

Write-Host "Dependabot alerts       ✅ (Always available)" -ForegroundColor Green
Write-Host "Security advisories     ✅ (Always available)" -ForegroundColor Green
Write-Host "Code scanning (CodeQL)  ✅ (Free for public)" -ForegroundColor Green
Write-Host "Secret scanning         ✅ (Free for public)" -ForegroundColor Green

Write-Host ""
Write-Host "💡 Summary:" -ForegroundColor Cyan
Write-Host "===========" -ForegroundColor Cyan
Write-Host "✅ FREE features (just enable in settings):" -ForegroundColor Green
Write-Host "   • Discussions - Great for Q&A, announcements" -ForegroundColor White
Write-Host "   • Wiki - Additional documentation" -ForegroundColor White
Write-Host "   • Projects - Kanban boards, roadmap" -ForegroundColor White
Write-Host "   • GitHub Pages - Host demo/docs" -ForegroundColor White
Write-Host "   • Actions - CI/CD (2,000 min/month free)" -ForegroundColor White
Write-Host ""
Write-Host "🎯 Recommended next steps:" -ForegroundColor Cyan
if (-not $hasDiscussions) {
    Write-Host "   1. Enable Discussions for community Q&A" -ForegroundColor Yellow
}
Write-Host "   2. Set up GitHub Actions for CI/CD" -ForegroundColor Yellow
Write-Host "   3. Enable GitHub Pages for demo instance" -ForegroundColor Yellow
Write-Host "   4. Create Project board for roadmap" -ForegroundColor Yellow
Write-Host ""
Write-Host "🔗 Quick links:" -ForegroundColor Cyan
Write-Host "   Settings:    https://github.com/$Owner/$Repo/settings" -ForegroundColor White
Write-Host "   Actions:     https://github.com/$Owner/$Repo/actions" -ForegroundColor White
Write-Host "   Projects:    https://github.com/users/$Owner/projects" -ForegroundColor White
if ($hasDiscussions) {
    Write-Host "   Discussions: https://github.com/$Owner/$Repo/discussions" -ForegroundColor White
}
