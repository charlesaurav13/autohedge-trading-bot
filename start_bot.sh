#!/bin/bash
# Start Paper Trading Bot

cd /Users/openclaw/.openclaw/workspace/AutoHedge
source venv/bin/activate

# Kill existing bot if running
pkill -f "python.*main_trading_loop.py" 2>/dev/null

# Start new bot
nohup python main_trading_loop.py > bot_output.log 2>&1 &

PID=$!
echo "✅ Bot started with PID: $PID"
echo "📊 Monitor: ./monitor_bot.sh"
echo "📝 Watch logs: tail -f bot_output.log"
