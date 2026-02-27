#!/bin/bash
# Quick daily report checker - run anytime

cd "$(dirname "$0")"

echo ""
echo "📊 Generating Daily Performance Report..."
echo ""

python3 generate_daily_report.py

echo ""
echo "Commands:"
echo "  Save to file:    python3 generate_daily_report.py --save"
echo "  Last 48 hours:   python3 generate_daily_report.py --hours 48"
echo "  View saved:      ls -lh reports/"
echo ""
