#!/bin/bash
# Monitor both trading bot and continuous learner

echo "═══════════════════════════════════════════════════════════"
echo "  TRADING + LEARNING SYSTEM STATUS"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Check trading bot
BOT_PID=$(ps aux | grep "[m]ain_trading_loop.py" | awk '{print $2}')
if [ -n "$BOT_PID" ]; then
    BOT_START=$(ps -p $BOT_PID -o lstart= 2>/dev/null)
    BOT_TIME=$(ps -p $BOT_PID -o etime= 2>/dev/null)
    echo "✅ Trading Bot: RUNNING"
    echo "   PID: $BOT_PID"
    echo "   Started: $BOT_START"
    echo "   Uptime: $BOT_TIME"
else
    echo "❌ Trading Bot: STOPPED"
fi

echo ""

# Check learner
LEARNER_PID=$(ps aux | grep "[c]ontinuous_learner.py" | awk '{print $2}')
if [ -n "$LEARNER_PID" ]; then
    LEARNER_START=$(ps -p $LEARNER_PID -o lstart= 2>/dev/null)
    LEARNER_TIME=$(ps -p $LEARNER_PID -o etime= 2>/dev/null)
    echo "✅ Continuous Learner: RUNNING"
    echo "   PID: $LEARNER_PID"
    echo "   Started: $LEARNER_START"
    echo "   Uptime: $LEARNER_TIME"
else
    echo "❌ Continuous Learner: STOPPED"
fi

echo ""
echo "───────────────────────────────────────────────────────────"
echo "  LEARNING STATS"
echo "───────────────────────────────────────────────────────────"

# Check learner state
if [ -f "models/learner_state.json" ]; then
    EPISODES=$(jq -r '.last_episode_count' models/learner_state.json 2>/dev/null)
    LAST_TRAIN=$(jq -r '.last_training_time' models/learner_state.json 2>/dev/null)
    TOTAL_TRAINS=$(jq -r '.total_trainings' models/learner_state.json 2>/dev/null)
    
    echo "Episodes processed: $EPISODES"
    echo "Total trainings: $TOTAL_TRAINS"
    echo "Last training: $LAST_TRAIN"
else
    echo "No training state found"
fi

echo ""

# Check models
if [ -f "models/continuous/latest.zip" ]; then
    MODEL_SIZE=$(ls -lh models/continuous/latest.zip | awk '{print $5}')
    MODEL_TIME=$(ls -l models/continuous/latest.zip | awk '{print $6, $7, $8}')
    echo "Latest model: $MODEL_SIZE (updated: $MODEL_TIME)"
else
    echo "No model trained yet"
fi

echo ""
echo "───────────────────────────────────────────────────────────"
echo "  TRADING STATS"
echo "───────────────────────────────────────────────────────────"

# Get recent log lines
if [ -f "bot_local_final.log" ]; then
    BALANCE=$(grep "Balance:" bot_local_final.log | tail -1 | grep -oE '\$[0-9.]+' | head -1)
    PNL=$(grep "PnL:" bot_local_final.log | tail -1 | grep -oE '[+-][0-9.]+%' | head -1)
    TRADES=$(grep "Daily Trades:" bot_local_final.log | tail -1 | grep -oE '[0-9]+/[0-9]+' | head -1)
    POSITIONS=$(grep "Open Positions:" bot_local_final.log | tail -1 | grep -oE '[0-9]+' | head -1)
    
    echo "Balance: ${BALANCE:-Unknown}"
    echo "PnL: ${PNL:-Unknown}"
    echo "Today's trades: ${TRADES:-Unknown}"
    echo "Open positions: ${POSITIONS:-Unknown}"
else
    echo "No trading log found"
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Commands:"
echo "  Watch learner: tail -f learner.log"
echo "  Watch bot: tail -f bot_local_final.log"
echo "  Stop learner: kill $LEARNER_PID"
echo "  Stop bot: kill $BOT_PID"
echo ""
echo "═══════════════════════════════════════════════════════════"
