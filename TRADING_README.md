# 🚀 Crypto Trading Bot - Setup & Usage

## System Configuration

**Capital:** $100 USDT  
**Position Size:** 30% per trade ($30)  
**Leverage:** 10x  
**Take Profit:** 10%  
**Stop Loss:** 5% (2:1 R:R ratio)  
**Max Trades/Day:** 3  
**Trading Pairs:** BTC/USDT, ETH/USDT, SOL/USDT  
**Check Interval:** 15 minutes  

## Risk Warning

⚠️ **HIGH RISK TRADING**  
- 10x leverage means amplified gains AND losses
- $30 position at 10x = $300 effective exposure
- 5% stop loss = $15 max loss per trade (15% of account)
- 3 bad trades in a row = -45% account drawdown

**This is extremely aggressive for a $100 account. Be prepared for volatility.**

## Installation

### 1. Install Dependencies

```bash
cd /Users/openclaw/.openclaw/workspace/AutoHedge
source venv/bin/activate
pip install -r requirements_trading.txt
```

### 2. Verify Binance API Connection

```bash
python test_binance_connection.py
```

Should show:
- ✓ System Status: normal
- ✓ Can Trade: True
- ✓ Futures enabled

### 3. Fund Your Futures Account

⚠️ **CRITICAL:** You must deposit **$100 USDT to your Binance Futures wallet** before starting the bot.

Current Futures balance: **$0.00 USDT**

Transfer USDT from Spot → Futures in Binance app.

## Usage

### Test Mode (Recommended First)

Run once to test the system without continuous loop:

```bash
python main_trading_loop.py --test
```

This will:
- Check account status
- Fetch news for all trading pairs
- Run AutoHedge analysis
- Show trading signals
- Execute trades if signals are strong enough
- Exit (no continuous loop)

### Check Status

```bash
python main_trading_loop.py --status
```

Shows:
- Account balance
- Open positions
- Daily trade count
- Current PnL

### Live Trading (Continuous)

⚠️ **ONLY RUN AFTER TESTING AND DEPOSITING FUNDS**

```bash
python main_trading_loop.py
```

Runs continuously:
- Checks every 15 minutes
- Monitors SL/TP on open positions
- Analyzes news + technical signals
- Opens new positions if signals align
- Max 3 trades per day

To stop: `Ctrl+C` (saves state gracefully)

## 5-Day Validation Plan

### Phase 1: Days 1-2 (Test & Observe)
- Run in test mode multiple times
- Observe signal quality
- Check if TP/SL levels make sense
- **DO NOT adjust parameters yet**

### Phase 2: Days 3-4 (Small Live Trades)
- Start with $50 capital (modify .env: CAPITAL_USDT=50)
- Reduce leverage to 5x (LEVERAGE=5)
- Run live but monitor closely
- Track win rate and PnL

### Phase 3: Day 5 (Full Parameters)
- If winning or break-even after days 3-4, scale to full $100
- Restore 10x leverage
- Continue monitoring

### Decision Point (End of Day 5)
- **If profitable or small loss (<10%):** Continue with adjustments
- **If large loss (>20%):** Stop, analyze, adjust parameters
- **If system errors:** Fix bugs, restart validation

## Files

- `main_trading_loop.py` - Main orchestrator
- `trading_bot.py` - Core trading engine (position management, SL/TP)
- `news_monitor.py` - Crypto news aggregation + sentiment analysis
- `autohedge/main.py` - Multi-agent technical analysis
- `.env` - Configuration (API keys, parameters)
- `bot_state.json` - Bot state (positions, trade count)
- `trading_bot_*.log` - Trading logs

## Monitoring

### Watch Logs in Real-Time

```bash
tail -f trading_bot_*.log
```

### Check Positions Manually

```bash
python -c "from trading_bot import TradingBot; import json; bot = TradingBot(); print(json.dumps(bot.get_status(), indent=2))"
```

### Emergency Stop

1. Press `Ctrl+C` in the terminal running the bot
2. Or: `pkill -f main_trading_loop.py`
3. Manually close positions in Binance if needed

## Configuration (.env)

Key parameters you can adjust:

```bash
# Capital and position sizing
CAPITAL_USDT=100
POSITION_SIZE_PCT=30

# Risk parameters
LEVERAGE=10
TAKE_PROFIT_PCT=10
STOP_LOSS_PCT=5

# Trading limits
MAX_TRADES_PER_DAY=3
CHECK_INTERVAL_MINUTES=15

# Signal thresholds
MIN_SIGNAL_STRENGTH=5.0
NEWS_CHECK_HOURS=6
```

## Safety Features

✓ **IP-restricted API key** - Only works from this machine  
✓ **Withdrawals disabled** - API key cannot withdraw funds  
✓ **Daily trade limit** - Max 3 trades/day prevents overtrading  
✓ **Position limits** - Max 1 position per asset  
✓ **Automatic SL/TP** - Every position has stop loss and take profit  
✓ **State persistence** - Bot remembers positions if restarted  

## What the Bot Does

1. **Every 15 minutes:**
   - Checks SL/TP on open positions (closes if triggered)
   - Fetches crypto news from CoinDesk, CoinTelegraph, Decrypt, Bitcoinist
   - Analyzes sentiment (bullish/bearish keywords)
   - Runs AutoHedge multi-agent analysis (Director, Quant, Risk, Execution agents)
   - Combines news + technical signals
   - Opens new position if signal strength ≥ 5/20 and no existing position

2. **Position Management:**
   - Opens market order with 10x leverage
   - Sets automatic SL at 5% loss
   - Sets automatic TP at 10% gain
   - Monitors every check cycle
   - Closes position when SL or TP hit

3. **Risk Controls:**
   - Max 3 trades per day (resets at midnight)
   - Only 1 position per asset
   - Position size locked at 30% of capital
   - No trades if balance too low

## Common Issues

### "Command not found: python"
Use `python3` instead of `python`

### "Binance API Error: Invalid API-key"
- Check .env file has correct keys
- Verify IP whitelist includes: 182.77.75.145
- Ensure API key has Futures trading enabled

### "Insufficient balance"
- Deposit USDT to Futures wallet (not Spot)
- Check with: `python main_trading_loop.py --status`

### "No trade signals"
- Normal if market is ranging or signals conflict
- Bot only trades when conditions align
- Check logs for signal scores

## Support

Questions? Issues?
- Check logs: `trading_bot_*.log`
- Review bot state: `bot_state.json`
- Test connection: `python test_binance_connection.py`

---

**Remember:** This is a high-risk automated trading system. Only risk capital you can afford to lose.
