# Amazon FBA Agent System v3.5 - Windows Setup Script
# ====================================================
# 
# This PowerShell script sets up the development environment on Windows
# including Git hooks, pre-commit framework, and Python dependencies.
#
# Usage:
#   .\scripts\setup_windows.ps1
#
# Requirements:
#   - PowerShell 5.1 or later
#   - Python 3.12 installed and in PATH
#   - Git installed and in PATH

param(
    [switch]$SkipPreCommit = $false,
    [switch]$SkipGitHooks = $false,
    [switch]$Force = $false
)

# Script configuration
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# Colors for output
$ColorReset = "`e[0m"
$ColorRed = "`e[31m"
$ColorGreen = "`e[32m"
$ColorYellow = "`e[33m"
$ColorBlue = "`e[34m"
$ColorMagenta = "`e[35m"
$ColorCyan = "`e[36m"

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = $ColorReset
    )
    Write-Host "${Color}${Message}${ColorReset}"
}

function Test-CommandExists {
    param([string]$Command)
    $null = Get-Command $Command -ErrorAction SilentlyContinue
    return $?
}

function Test-PythonVersion {
    try {
        $pythonVersion = python --version 2>&1
        if ($pythonVersion -match "Python (\d+)\.(\d+)") {
            $major = [int]$matches[1]
            $minor = [int]$matches[2]
            return ($major -eq 3 -and $minor -ge 12)
        }
        return $false
    }
    catch {
        return $false
    }
}

function Install-PreCommitFramework {
    Write-ColorOutput "📦 Installing pre-commit framework..." $ColorBlue
    
    try {
        python -m pip install pre-commit
        if ($LASTEXITCODE -ne 0) {
            throw "pip install failed"
        }
        
        Write-ColorOutput "✅ Pre-commit framework installed successfully" $ColorGreen
        return $true
    }
    catch {
        Write-ColorOutput "❌ Failed to install pre-commit framework: $_" $ColorRed
        return $false
    }
}

function Setup-GitHooks {
    Write-ColorOutput "🔗 Setting up Git hooks..." $ColorBlue
    
    # Ensure .git/hooks directory exists
    $hooksDir = ".git\hooks"
    if (-not (Test-Path $hooksDir)) {
        New-Item -ItemType Directory -Path $hooksDir -Force | Out-Null
    }
    
    # Copy our custom pre-commit hook
    $sourceHook = ".githooks\pre-commit"
    $targetHook = "$hooksDir\pre-commit"
    
    if (Test-Path $sourceHook) {
        try {
            Copy-Item $sourceHook $targetHook -Force
            
            # On Windows, we need to ensure the hook is executable
            # Git for Windows will handle the executable bit automatically
            
            Write-ColorOutput "✅ Custom pre-commit hook installed" $ColorGreen
            
            # Test the hook
            Write-ColorOutput "🧪 Testing pre-commit hook..." $ColorYellow
            $testResult = & bash $targetHook 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-ColorOutput "✅ Pre-commit hook test passed" $ColorGreen
            } else {
                Write-ColorOutput "⚠️ Pre-commit hook test failed (this may be normal): $testResult" $ColorYellow
            }
            
            return $true
        }
        catch {
            Write-ColorOutput "❌ Failed to install Git hook: $_" $ColorRed
            return $false
        }
    } else {
        Write-ColorOutput "❌ Source hook not found: $sourceHook" $ColorRed
        return $false
    }
}

function Setup-PreCommitHooks {
    Write-ColorOutput "⚙️ Setting up pre-commit hooks..." $ColorBlue
    
    try {
        # Install the pre-commit hooks
        pre-commit install
        if ($LASTEXITCODE -ne 0) {
            throw "pre-commit install failed"
        }
        
        Write-ColorOutput "✅ Pre-commit hooks installed successfully" $ColorGreen
        
        # Test pre-commit configuration
        Write-ColorOutput "🧪 Testing pre-commit configuration..." $ColorYellow
        pre-commit run --all-files
        $testExitCode = $LASTEXITCODE
        
        if ($testExitCode -eq 0) {
            Write-ColorOutput "✅ All pre-commit hooks passed" $ColorGreen
        } else {
            Write-ColorOutput "⚠️ Some pre-commit hooks failed (this is normal for first run)" $ColorYellow
            Write-ColorOutput "   Run 'pre-commit run --all-files' again after fixing issues" $ColorCyan
        }
        
        return $true
    }
    catch {
        Write-ColorOutput "❌ Failed to setup pre-commit hooks: $_" $ColorRed
        return $false
    }
}

function Test-Environment {
    Write-ColorOutput "🔍 Checking system requirements..." $ColorBlue
    
    $allGood = $true
    
    # Check Python
    if (-not (Test-CommandExists "python")) {
        Write-ColorOutput "❌ Python not found in PATH" $ColorRed
        Write-ColorOutput "   Please install Python 3.12+ and add to PATH" $ColorYellow
        $allGood = $false
    } elseif (-not (Test-PythonVersion)) {
        Write-ColorOutput "❌ Python 3.12+ required" $ColorRed
        Write-ColorOutput "   Current version: $(python --version)" $ColorYellow
        $allGood = $false
    } else {
        Write-ColorOutput "✅ Python $(python --version) found" $ColorGreen
    }
    
    # Check Git
    if (-not (Test-CommandExists "git")) {
        Write-ColorOutput "❌ Git not found in PATH" $ColorRed
        Write-ColorOutput "   Please install Git for Windows" $ColorYellow
        $allGood = $false
    } else {
        $gitVersion = git --version
        Write-ColorOutput "✅ $gitVersion found" $ColorGreen
    }
    
    # Check Bash (for Git hooks)
    if (-not (Test-CommandExists "bash")) {
        Write-ColorOutput "❌ Bash not found in PATH" $ColorRed
        Write-ColorOutput "   Git for Windows should include bash" $ColorYellow
        $allGood = $false
    } else {
        Write-ColorOutput "✅ Bash found (required for Git hooks)" $ColorGreen
    }
    
    # Check if we're in a Git repository
    if (-not (Test-Path ".git")) {
        Write-ColorOutput "❌ Not in a Git repository" $ColorRed
        Write-ColorOutput "   Run 'git init' or clone the repository" $ColorYellow
        $allGood = $false
    } else {
        Write-ColorOutput "✅ Git repository detected" $ColorGreen
    }
    
    # Check PowerShell execution policy
    $executionPolicy = Get-ExecutionPolicy
    if ($executionPolicy -eq "Restricted") {
        Write-ColorOutput "⚠️ PowerShell execution policy is Restricted" $ColorYellow
        Write-ColorOutput "   You may need to run: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" $ColorCyan
    } else {
        Write-ColorOutput "✅ PowerShell execution policy: $executionPolicy" $ColorGreen
    }
    
    return $allGood
}

function Install-PythonDependencies {
    Write-ColorOutput "📦 Installing Python dependencies..." $ColorBlue
    
    # Core dependencies for the sync system
    $dependencies = @(
        "python-dotenv",
        "requests",
        "black",
        "isort",
        "flake8"
    )
    
    try {
        foreach ($dep in $dependencies) {
            Write-ColorOutput "   Installing $dep..." $ColorCyan
            python -m pip install $dep --quiet
            if ($LASTEXITCODE -ne 0) {
                throw "Failed to install $dep"
            }
        }
        
        Write-ColorOutput "✅ Python dependencies installed successfully" $ColorGreen
        return $true
    }
    catch {
        Write-ColorOutput "❌ Failed to install Python dependencies: $_" $ColorRed
        return $false
    }
}

function Test-SyncSystem {
    Write-ColorOutput "🧪 Testing Claude Standards sync system..." $ColorBlue
    
    try {
        # Test sync script
        python tools\sync_claude_standards.py --check-only
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✅ Sync script is working" $ColorGreen
        } else {
            Write-ColorOutput "⚠️ Sync script reports files need sync" $ColorYellow
            Write-ColorOutput "   Run: python tools\sync_claude_standards.py" $ColorCyan
        }
        
        # Test opportunity detector
        if (Test-Path "tools\sync_opportunity_detector.py") {
            python tools\sync_opportunity_detector.py --check
            if ($LASTEXITCODE -eq 0) {
                Write-ColorOutput "✅ Sync opportunity detector is working" $ColorGreen
            } else {
                Write-ColorOutput "ℹ️ Sync opportunity detector reports sync needed" $ColorBlue
            }
        }
        
        # Test security checker
        if (Test-Path "tools\security_checks.py") {
            python tools\security_checks.py --check-api-keys
            if ($LASTEXITCODE -eq 0) {
                Write-ColorOutput "✅ Security checker passed" $ColorGreen
            } else {
                Write-ColorOutput "⚠️ Security checker found issues" $ColorYellow
            }
        }
        
        return $true
    }
    catch {
        Write-ColorOutput "❌ Sync system test failed: $_" $ColorRed
        return $false
    }
}

function Show-NextSteps {
    Write-ColorOutput "`n🎉 Setup complete! Next steps:" $ColorGreen
    Write-ColorOutput "────────────────────────────────────" $ColorGreen
    
    Write-ColorOutput "1. 📋 Verify environment:" $ColorBlue
    Write-ColorOutput "   python tools\sync_claude_standards.py --check-only" $ColorCyan
    
    Write-ColorOutput "2. 🔄 Run initial sync if needed:" $ColorBlue
    Write-ColorOutput "   python tools\sync_claude_standards.py" $ColorCyan
    
    Write-ColorOutput "3. 🧪 Test pre-commit hooks:" $ColorBlue
    Write-ColorOutput "   pre-commit run --all-files" $ColorCyan
    
    Write-ColorOutput "4. 🔐 Configure environment:" $ColorBlue
    Write-ColorOutput "   Copy .env.example to .env and add your API keys" $ColorCyan
    
    Write-ColorOutput "5. 📚 Read the documentation:" $ColorBlue
    Write-ColorOutput "   docs\README.md" $ColorCyan
    Write-ColorOutput "   CLAUDE_STANDARDS.md" $ColorCyan
    
    Write-ColorOutput "`n✨ Development environment is ready!" $ColorMagenta
}

# Main execution
function Main {
    Write-ColorOutput "🚀 Amazon FBA Agent System v3.5 - Windows Setup" $ColorMagenta
    Write-ColorOutput "=" * 50 $ColorMagenta
    
    # Test environment first
    if (-not (Test-Environment)) {
        Write-ColorOutput "`n❌ Environment check failed. Please fix the issues above and try again." $ColorRed
        exit 1
    }
    
    $success = $true
    
    # Install Python dependencies
    if (-not (Install-PythonDependencies)) {
        $success = $false
    }
    
    # Install pre-commit framework
    if (-not $SkipPreCommit -and $success) {
        if (-not (Install-PreCommitFramework)) {
            $success = $false
        }
    }
    
    # Setup Git hooks
    if (-not $SkipGitHooks -and $success) {
        if (-not (Setup-GitHooks)) {
            $success = $false
        }
    }
    
    # Setup pre-commit hooks
    if (-not $SkipPreCommit -and $success) {
        if (-not (Setup-PreCommitHooks)) {
            $success = $false
        }
    }
    
    # Test the sync system
    if ($success) {
        Test-SyncSystem | Out-Null
    }
    
    if ($success) {
        Show-NextSteps
        exit 0
    } else {
        Write-ColorOutput "`n❌ Setup completed with errors. Check the output above." $ColorRed
        exit 1
    }
}

# Check if running as administrator (optional warning)
if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-ColorOutput "ℹ️ Running without administrator privileges (this is usually fine)" $ColorBlue
}

# Run main function
Main