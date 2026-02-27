#!/bin/bash
# Setup automated daily reports via cron

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPORT_SCRIPT="$SCRIPT_DIR/generate_daily_report.py"

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  AUTOMATED DAILY REPORT SETUP                             ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Check if report script exists
if [ ! -f "$REPORT_SCRIPT" ]; then
    echo "❌ Error: generate_daily_report.py not found!"
    exit 1
fi

echo "📋 This will set up automatic daily reports sent at 9:00 AM"
echo ""
echo "Options:"
echo "  1) Console only (saved to reports/)"
echo "  2) Console + Telegram notification (coming soon)"
echo "  3) Email report (requires setup)"
echo ""
read -p "Choose option (1-3): " choice

case $choice in
    1)
        CRON_CMD="0 9 * * * cd $SCRIPT_DIR && /usr/bin/python3 generate_daily_report.py --save >> $SCRIPT_DIR/logs/daily_reports.log 2>&1"
        ;;
    2)
        echo "⚠️  Telegram not yet configured. Setting up console reports."
        CRON_CMD="0 9 * * * cd $SCRIPT_DIR && /usr/bin/python3 generate_daily_report.py --save >> $SCRIPT_DIR/logs/daily_reports.log 2>&1"
        ;;
    3)
        echo "⚠️  Email not yet configured. Setting up console reports."
        CRON_CMD="0 9 * * * cd $SCRIPT_DIR && /usr/bin/python3 generate_daily_report.py --save >> $SCRIPT_DIR/logs/daily_reports.log 2>&1"
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "📝 Adding cron job..."
echo ""
echo "Command to be added:"
echo "  $CRON_CMD"
echo ""

# Check if cron entry already exists
if crontab -l 2>/dev/null | grep -q "generate_daily_report.py"; then
    echo "⚠️  Cron job already exists!"
    read -p "Replace it? (y/n): " replace
    if [ "$replace" != "y" ]; then
        echo "Cancelled."
        exit 0
    fi
    # Remove existing entry
    crontab -l 2>/dev/null | grep -v "generate_daily_report.py" | crontab -
fi

# Add new entry
(crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -

if [ $? -eq 0 ]; then
    echo "✅ Cron job added successfully!"
    echo ""
    echo "Daily reports will be generated at 9:00 AM and saved to:"
    echo "  $SCRIPT_DIR/reports/"
    echo ""
    echo "View current cron jobs:"
    echo "  crontab -l"
    echo ""
    echo "Test report now:"
    echo "  cd $SCRIPT_DIR && python3 generate_daily_report.py"
    echo ""
    echo "View saved reports:"
    echo "  ls -lh $SCRIPT_DIR/reports/"
else
    echo "❌ Failed to add cron job"
    exit 1
fi
