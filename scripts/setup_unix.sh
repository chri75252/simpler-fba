#!/bin/bash
#
# Amazon FBA Agent System v3.5 - Unix/Linux/macOS Setup Script
# =============================================================
# 
# This bash script sets up the development environment on Unix-like systems
# including Git hooks, pre-commit framework, and Python dependencies.
#
# Usage:
#   ./scripts/setup_unix.sh
#   ./scripts/setup_unix.sh --skip-precommit
#   ./scripts/setup_unix.sh --skip-git-hooks
#
# Requirements:
#   - Bash 4.0 or later
#   - Python 3.12+ installed and in PATH
#   - Git installed and in PATH

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Colors for output
readonly COLOR_RESET='\033[0m'
readonly COLOR_RED='\033[31m'
readonly COLOR_GREEN='\033[32m'
readonly COLOR_YELLOW='\033[33m'
readonly COLOR_BLUE='\033[34m'
readonly COLOR_MAGENTA='\033[35m'
readonly COLOR_CYAN='\033[36m'

# Flags
SKIP_PRECOMMIT=false
SKIP_GIT_HOOKS=false
FORCE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-precommit)
            SKIP_PRECOMMIT=true
            shift
            ;;
        --skip-git-hooks)
            SKIP_GIT_HOOKS=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--skip-precommit] [--skip-git-hooks] [--force]"
            echo ""
            echo "Options:"
            echo "  --skip-precommit    Skip pre-commit framework installation"
            echo "  --skip-git-hooks    Skip Git hooks setup"
            echo "  --force            Force overwrite existing files"
            echo "  -h, --help         Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

function print_color() {
    local color="$1"
    local message="$2"
    echo -e "${color}${message}${COLOR_RESET}"
}

function print_error() {
    print_color "$COLOR_RED" "❌ $1" >&2
}

function print_success() {
    print_color "$COLOR_GREEN" "✅ $1"
}

function print_warning() {
    print_color "$COLOR_YELLOW" "⚠️ $1"
}

function print_info() {
    print_color "$COLOR_BLUE" "ℹ️ $1"
}

function print_step() {
    print_color "$COLOR_CYAN" "$1"
}

function command_exists() {
    command -v "$1" >/dev/null 2>&1
}

function check_python_version() {
    if ! command_exists python3; then
        if command_exists python; then
            local version
            version=$(python --version 2>&1 | awk '{print $2}')
            if [[ $version =~ ^3\.1[2-9] ]] || [[ $version =~ ^3\.[2-9][0-9] ]]; then
                echo "python"
                return 0
            fi
        fi
        return 1
    fi
    
    local version
    version=$(python3 --version 2>&1 | awk '{print $2}')
    if [[ $version =~ ^3\.1[2-9] ]] || [[ $version =~ ^3\.[2-9][0-9] ]]; then
        echo "python3"
        return 0
    fi
    
    return 1
}

function test_environment() {
    print_step "🔍 Checking system requirements..."
    
    local all_good=true
    
    # Check Python
    local python_cmd
    if python_cmd=$(check_python_version); then
        local version
        version=$($python_cmd --version 2>&1)
        print_success "Python $version found"
    else
        print_error "Python 3.12+ not found in PATH"
        print_warning "Please install Python 3.12+ and ensure it's accessible as 'python3' or 'python'"
        all_good=false
    fi
    
    # Check Git
    if command_exists git; then
        local git_version
        git_version=$(git --version)
        print_success "$git_version found"
    else
        print_error "Git not found in PATH"
        print_warning "Please install Git"
        all_good=false
    fi
    
    # Check if we're in a Git repository
    if [[ ! -d ".git" ]]; then
        print_error "Not in a Git repository"
        print_warning "Run 'git init' or clone the repository"
        all_good=false
    else
        print_success "Git repository detected"
    fi
    
    # Check pip
    if $python_cmd -m pip --version >/dev/null 2>&1; then
        print_success "pip found"
    else
        print_error "pip not available"
        print_warning "Please install pip for Python"
        all_good=false
    fi
    
    if [[ "$all_good" == "false" ]]; then
        return 1
    fi
    
    return 0
}

function install_python_dependencies() {
    print_step "📦 Installing Python dependencies..."
    
    local python_cmd
    if ! python_cmd=$(check_python_version); then
        print_error "Python not available"
        return 1
    fi
    
    # Core dependencies for the sync system
    local dependencies=(
        "python-dotenv"
        "requests"
        "black"
        "isort"
        "flake8"
    )
    
    for dep in "${dependencies[@]}"; do
        print_info "Installing $dep..."
        if ! $python_cmd -m pip install "$dep" --quiet; then
            print_error "Failed to install $dep"
            return 1
        fi
    done
    
    print_success "Python dependencies installed successfully"
    return 0
}

function install_precommit_framework() {
    print_step "📦 Installing pre-commit framework..."
    
    local python_cmd
    if ! python_cmd=$(check_python_version); then
        print_error "Python not available"
        return 1
    fi
    
    if ! $python_cmd -m pip install pre-commit; then
        print_error "Failed to install pre-commit framework"
        return 1
    fi
    
    print_success "Pre-commit framework installed successfully"
    return 0
}

function setup_git_hooks() {
    print_step "🔗 Setting up Git hooks..."
    
    # Ensure .git/hooks directory exists
    local hooks_dir=".git/hooks"
    mkdir -p "$hooks_dir"
    
    # Copy our custom pre-commit hook
    local source_hook=".githooks/pre-commit"
    local target_hook="$hooks_dir/pre-commit"
    
    if [[ -f "$source_hook" ]]; then
        if cp "$source_hook" "$target_hook"; then
            chmod +x "$target_hook"
            print_success "Custom pre-commit hook installed"
            
            # Test the hook
            print_info "Testing pre-commit hook..."
            if "$target_hook"; then
                print_success "Pre-commit hook test passed"
            else
                print_warning "Pre-commit hook test failed (this may be normal)"
            fi
            
            return 0
        else
            print_error "Failed to install Git hook"
            return 1
        fi
    else
        print_error "Source hook not found: $source_hook"
        return 1
    fi
}

function setup_precommit_hooks() {
    print_step "⚙️ Setting up pre-commit hooks..."
    
    # Install the pre-commit hooks
    if ! pre-commit install; then
        print_error "Failed to install pre-commit hooks"
        return 1
    fi
    
    print_success "Pre-commit hooks installed successfully"
    
    # Test pre-commit configuration
    print_info "Testing pre-commit configuration..."
    if pre-commit run --all-files; then
        print_success "All pre-commit hooks passed"
    else
        print_warning "Some pre-commit hooks failed (this is normal for first run)"
        print_info "Run 'pre-commit run --all-files' again after fixing issues"
    fi
    
    return 0
}

function test_sync_system() {
    print_step "🧪 Testing Claude Standards sync system..."
    
    local python_cmd
    if ! python_cmd=$(check_python_version); then
        print_error "Python not available"
        return 1
    fi
    
    # Test sync script
    if $python_cmd tools/sync_claude_standards.py --check-only; then
        print_success "Sync script is working"
    else
        print_warning "Sync script reports files need sync"
        print_info "Run: $python_cmd tools/sync_claude_standards.py"
    fi
    
    # Test opportunity detector
    if [[ -f "tools/sync_opportunity_detector.py" ]]; then
        if $python_cmd tools/sync_opportunity_detector.py --check; then
            print_success "Sync opportunity detector is working"
        else
            print_info "Sync opportunity detector reports sync needed"
        fi
    fi
    
    # Test security checker
    if [[ -f "tools/security_checks.py" ]]; then
        if $python_cmd tools/security_checks.py --check-api-keys; then
            print_success "Security checker passed"
        else
            print_warning "Security checker found issues"
        fi
    fi
    
    return 0
}

function create_env_file() {
    if [[ ! -f ".env" ]] && [[ -f ".env.example" ]]; then
        print_step "📄 Creating .env file from example..."
        cp ".env.example" ".env"
        print_success ".env file created from .env.example"
        print_warning "Please edit .env and add your API keys"
    elif [[ ! -f ".env" ]]; then
        print_info "No .env file found (this is normal if not using environment variables)"
    else
        print_success ".env file already exists"
    fi
}

function show_next_steps() {
    print_color "$COLOR_GREEN" ""
    print_color "$COLOR_GREEN" "🎉 Setup complete! Next steps:"
    print_color "$COLOR_GREEN" "────────────────────────────────────"
    
    local python_cmd
    python_cmd=$(check_python_version)
    
    print_color "$COLOR_BLUE" "1. 📋 Verify environment:"
    print_color "$COLOR_CYAN" "   $python_cmd tools/sync_claude_standards.py --check-only"
    
    print_color "$COLOR_BLUE" "2. 🔄 Run initial sync if needed:"
    print_color "$COLOR_CYAN" "   $python_cmd tools/sync_claude_standards.py"
    
    print_color "$COLOR_BLUE" "3. 🧪 Test pre-commit hooks:"
    print_color "$COLOR_CYAN" "   pre-commit run --all-files"
    
    print_color "$COLOR_BLUE" "4. 🔐 Configure environment:"
    print_color "$COLOR_CYAN" "   Edit .env and add your API keys"
    
    print_color "$COLOR_BLUE" "5. 📚 Read the documentation:"
    print_color "$COLOR_CYAN" "   docs/README.md"
    print_color "$COLOR_CYAN" "   CLAUDE_STANDARDS.md"
    
    print_color "$COLOR_MAGENTA" ""
    print_color "$COLOR_MAGENTA" "✨ Development environment is ready!"
}

function main() {
    print_color "$COLOR_MAGENTA" "🚀 Amazon FBA Agent System v3.5 - Unix Setup"
    print_color "$COLOR_MAGENTA" "$(printf '=%.0s' {1..50})"
    
    # Test environment first
    if ! test_environment; then
        print_error "Environment check failed. Please fix the issues above and try again."
        exit 1
    fi
    
    local success=true
    
    # Install Python dependencies
    if ! install_python_dependencies; then
        success=false
    fi
    
    # Install pre-commit framework
    if [[ "$SKIP_PRECOMMIT" == "false" ]] && [[ "$success" == "true" ]]; then
        if ! install_precommit_framework; then
            success=false
        fi
    fi
    
    # Setup Git hooks
    if [[ "$SKIP_GIT_HOOKS" == "false" ]] && [[ "$success" == "true" ]]; then
        if ! setup_git_hooks; then
            success=false
        fi
    fi
    
    # Setup pre-commit hooks
    if [[ "$SKIP_PRECOMMIT" == "false" ]] && [[ "$success" == "true" ]]; then
        if ! setup_precommit_hooks; then
            success=false
        fi
    fi
    
    # Create environment file
    if [[ "$success" == "true" ]]; then
        create_env_file
    fi
    
    # Test the sync system
    if [[ "$success" == "true" ]]; then
        test_sync_system || true  # Don't fail on test issues
    fi
    
    if [[ "$success" == "true" ]]; then
        show_next_steps
        exit 0
    else
        print_error "Setup completed with errors. Check the output above."
        exit 1
    fi
}

# Check if running with proper permissions
if [[ $EUID -eq 0 ]]; then
    print_warning "Running as root (this is usually unnecessary)"
fi

# Make sure script is executable
if [[ ! -x "$0" ]]; then
    print_warning "Script is not executable. Run: chmod +x $0"
fi

# Run main function
main "$@"