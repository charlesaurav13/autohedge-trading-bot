#!/bin/bash
# Setup episode monitoring with cron

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
MONITOR_SCRIPT="$SCRIPT_DIR/episode_monitor.py"
VENV_PYTHON="$SCRIPT_DIR/venv/bin/python3"

echo "=========================================="
echo "Episode Monitor - Cron Setup"
echo "=========================================="
echo ""

# Check if monitor script exists
if [ ! -f "$MONITOR_SCRIPT" ]; then
    echo "❌ Error: episode_monitor.py not found"
    exit 1
fi

# Make script executable
chmod +x "$MONITOR_SCRIPT"

echo "Monitor script: $MONITOR_SCRIPT"
echo ""
echo "How often should the monitor check?"
echo ""
echo "Options:"
echo "  1) Every 2 hours (12 checks/day) - Recommended"
echo "  2) Every 4 hours (6 checks/day)"
echo "  3) Every 6 hours (4 checks/day)"
echo "  4) Custom interval"
echo ""
read -p "Choose option [1-4]: " choice

case $choice in
    1)
        CRON_SCHEDULE="0 */2 * * *"
        DESCRIPTION="every 2 hours"
        ;;
    2)
        CRON_SCHEDULE="0 */4 * * *"
        DESCRIPTION="every 4 hours"
        ;;
    3)
        CRON_SCHEDULE="0 */6 * * *"
        DESCRIPTION="every 6 hours"
        ;;
    4)
        echo ""
        echo "Enter cron schedule (e.g., '0 */2 * * *' for every 2 hours):"
        read -p "> " CRON_SCHEDULE
        DESCRIPTION="custom schedule"
        ;;
    *)
        echo "Invalid choice. Using default: every 2 hours"
        CRON_SCHEDULE="0 */2 * * *"
        DESCRIPTION="every 2 hours"
        ;;
esac

# Create log directory
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"

# Cron job command
CRON_CMD="cd $SCRIPT_DIR && $VENV_PYTHON $MONITOR_SCRIPT >> $LOG_DIR/monitor.log 2>&1"

echo ""
echo "=========================================="
echo "Cron Configuration"
echo "=========================================="
echo "Schedule:     $DESCRIPTION ($CRON_SCHEDULE)"
echo "Command:      $CRON_CMD"
echo "Log file:     $LOG_DIR/monitor.log"
echo ""

# Check if cron job already exists
EXISTING=$(crontab -l 2>/dev/null | grep -F "episode_monitor.py")

if [ -n "$EXISTING" ]; then
    echo "⚠️  Found existing monitor cron job:"
    echo "   $EXISTING"
    echo ""
    read -p "Replace existing job? [y/N]: " replace
    if [[ ! $replace =~ ^[Yy]$ ]]; then
        echo "Setup cancelled"
        exit 0
    fi
    
    # Remove existing job
    crontab -l 2>/dev/null | grep -v "episode_monitor.py" | crontab -
    echo "✓ Removed old job"
fi

# Add new cron job
(crontab -l 2>/dev/null; echo "$CRON_SCHEDULE $CRON_CMD") | crontab -

echo ""
echo "✅ Cron job installed successfully!"
echo ""
echo "=========================================="
echo "Quick Reference"
echo "=========================================="
echo ""
echo "View monitor logs:"
echo "  tail -f $LOG_DIR/monitor.log"
echo ""
echo "Run monitor manually:"
echo "  cd $SCRIPT_DIR"
echo "  source venv/bin/activate"
echo "  python episode_monitor.py"
echo ""
echo "View cron jobs:"
echo "  crontab -l"
echo ""
echo "Remove cron job:"
echo "  crontab -l | grep -v episode_monitor.py | crontab -"
echo ""
echo "=========================================="
echo ""
echo "🎯 Next alert at: $(date -v +2H '+%Y-%m-%d %H:00')"
echo ""
