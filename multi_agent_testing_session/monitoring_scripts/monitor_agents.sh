#!/bin/bash
# Amazon FBA Multi-Agent Monitoring Launcher
# Usage: ./monitor_agents.sh [agent_name] or ./monitor_agents.sh all

echo "🚀 Amazon FBA Multi-Agent Monitor"
echo "================================="

# Find the most recent log files
EXEC_LOG=$(ls -t logs/debug/run_custom_poundwholesale_*.log 2>/dev/null | head -1)
VERIFY_LOG=$(ls -t logs/debug/verify_agent_*.log 2>/dev/null | head -1)
TOGGLE_LOG=$(ls -t logs/debug/toggle_agent_*.log 2>/dev/null | head -1)
EXEC_REPORT_LOG=$(ls -t logs/debug/exec_agent_report_*.log 2>/dev/null | head -1)

echo "📁 Current log files:"
echo "  🚀 Main Execution: $EXEC_LOG"
echo "  ✅ Verification:   $VERIFY_LOG"
echo "  ⚙️  Toggle Testing: $TOGGLE_LOG"
echo "  📊 Exec Reports:   $EXEC_REPORT_LOG"
echo ""

# Function to start monitoring a specific agent
monitor_agent() {
    local agent=$1
    local logfile=$2
    
    if [[ -f "$logfile" ]]; then
        echo "🔍 Starting monitor for $agent..."
        echo "📄 Log file: $logfile"
        echo "⌨️  Press Ctrl+C to stop monitoring"
        echo "=====================================
        tail -f "$logfile"
    else
        echo "❌ Log file not found: $logfile"
    fi
}

# Parse command line arguments
case "${1:-help}" in
    "exec"|"execution")
        echo "🚀 Monitoring Main Execution Agent"
        monitor_agent "Execution Agent" "$EXEC_LOG"
        ;;
    "verify"|"verification")
        echo "✅ Monitoring Verification Agent"
        monitor_agent "Verification Agent" "$VERIFY_LOG"
        ;;
    "toggle"|"toggles")
        echo "⚙️ Monitoring Toggle Testing Agent"
        monitor_agent "Toggle Agent" "$TOGGLE_LOG"
        ;;
    "report"|"reports")
        echo "📊 Monitoring Exec Reports Agent"
        monitor_agent "Exec Reports Agent" "$EXEC_REPORT_LOG"
        ;;
    "all")
        echo "📺 Starting monitoring for all agents..."
        echo "Opening separate tail processes..."
        
        if [[ -f "$EXEC_LOG" ]]; then
            echo "🚀 Execution Agent: tail -f $EXEC_LOG"
        fi
        if [[ -f "$VERIFY_LOG" ]]; then
            echo "✅ Verification Agent: tail -f $VERIFY_LOG"
        fi
        if [[ -f "$TOGGLE_LOG" ]]; then
            echo "⚙️ Toggle Agent: tail -f $TOGGLE_LOG"
        fi
        if [[ -f "$EXEC_REPORT_LOG" ]]; then
            echo "📊 Exec Reports: tail -f $EXEC_REPORT_LOG"
        fi
        
        echo ""
        echo "🔧 Run these commands in separate terminals:"
        echo "tail -f $EXEC_LOG"
        echo "tail -f $VERIFY_LOG"
        echo "tail -f $TOGGLE_LOG"
        echo "tail -f $EXEC_REPORT_LOG"
        ;;
    "help"|*)
        echo "Usage: $0 [agent_name]"
        echo ""
        echo "Available agents:"
        echo "  exec       - Monitor main execution workflow"
        echo "  verify     - Monitor verification agent"
        echo "  toggle     - Monitor toggle testing agent"
        echo "  report     - Monitor execution reports"
        echo "  all        - Show commands for all agents"
        echo ""
        echo "Examples:"
        echo "  $0 exec      # Monitor main execution"
        echo "  $0 verify    # Monitor verification"
        echo "  $0 all       # Show all monitoring commands"
        ;;
esac