#!/bin/bash
# Setup episode monitoring with launchd (macOS native)

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
MONITOR_SCRIPT="$SCRIPT_DIR/episode_monitor.py"
VENV_PYTHON="$SCRIPT_DIR/venv/bin/python3"
LOG_DIR="$SCRIPT_DIR/logs"
PLIST_NAME="com.autohedge.episode-monitor"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"

echo "=========================================="
echo "Episode Monitor - LaunchD Setup (macOS)"
echo "=========================================="
echo ""

# Create log directory
mkdir -p "$LOG_DIR"

# Check if already installed
if [ -f "$PLIST_PATH" ]; then
    echo "⚠️  Monitor already installed"
    echo ""
    read -p "Reinstall? [y/N]: " reinstall
    if [[ ! $reinstall =~ ^[Yy]$ ]]; then
        echo "Setup cancelled"
        exit 0
    fi
    
    # Unload existing
    launchctl unload "$PLIST_PATH" 2>/dev/null
    rm "$PLIST_PATH"
    echo "✓ Removed old configuration"
fi

# Create LaunchAgent plist
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$PLIST_NAME</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>$VENV_PYTHON</string>
        <string>$MONITOR_SCRIPT</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>$SCRIPT_DIR</string>
    
    <key>StandardOutPath</key>
    <string>$LOG_DIR/monitor.log</string>
    
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/monitor_error.log</string>
    
    <key>StartInterval</key>
    <integer>7200</integer>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
EOF

echo "✓ Created LaunchAgent configuration"

# Load the agent
launchctl load "$PLIST_PATH"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Episode monitor installed successfully!"
    echo ""
    echo "=========================================="
    echo "Configuration"
    echo "=========================================="
    echo "Schedule:     Every 2 hours"
    echo "Log file:     $LOG_DIR/monitor.log"
    echo "Error log:    $LOG_DIR/monitor_error.log"
    echo "LaunchAgent:  $PLIST_PATH"
    echo ""
    echo "=========================================="
    echo "Quick Reference"
    echo "=========================================="
    echo ""
    echo "View monitor logs:"
    echo "  tail -f $LOG_DIR/monitor.log"
    echo ""
    echo "Run monitor now:"
    echo "  launchctl start $PLIST_NAME"
    echo ""
    echo "Stop monitoring:"
    echo "  launchctl unload $PLIST_PATH"
    echo ""
    echo "Restart monitoring:"
    echo "  launchctl unload $PLIST_PATH"
    echo "  launchctl load $PLIST_PATH"
    echo ""
    echo "Remove completely:"
    echo "  launchctl unload $PLIST_PATH"
    echo "  rm $PLIST_PATH"
    echo ""
    echo "=========================================="
    echo ""
    echo "🎯 First check will run now, then every 2 hours"
    echo ""
else
    echo ""
    echo "❌ Failed to load LaunchAgent"
    echo ""
    echo "Try manual setup:"
    echo "1. launchctl load $PLIST_PATH"
    echo "2. Check: launchctl list | grep episode-monitor"
    echo ""
fi
