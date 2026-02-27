#!/bin/bash
# Paper Trading Bot Monitor

echo "🤖 Paper Trading Bot Status"
echo "=============================="

# Check if bot is running
if pgrep -f "python.*main_trading_loop.py" > /dev/null; then
    PID=$(pgrep -f "python.*main_trading_loop.py")
    echo "Status: ✅ RUNNING (PID: $PID)"
else
    echo "Status: ❌ NOT RUNNING"
    exit 1
fi

echo ""
echo "📊 Latest Activity:"
echo "-------------------"
tail -20 /Users/openclaw/.openclaw/workspace/AutoHedge/bot_output.log

echo ""
echo "📝 Paper Trading Logs:"
echo "----------------------"
if [ -f paper_trading_*.log ]; then
    tail -10 paper_trading_*.log 2>/dev/null | tail -10
else
    echo "No trades yet."
fi

echo ""
echo "Commands:"
echo "  • Watch live: tail -f bot_output.log"
echo "  • Stop bot: pkill -f 'python.*main_trading_loop.py'"
echo "  • Restart: ./start_bot.sh"
