# Trading Bot - Complete System

**Status:** ✅ Ready for deployment  
**Location:** `/Users/openclaw/.openclaw/workspace/AutoHedge/`

---

## What I Built

### 1. **Core Trading Engine**
- Binance Futures integration (10x leverage)
- Automatic position management (SL/TP)
- Daily trade limits (3/day)
- State persistence
- Risk controls

### 2. **News Monitoring**
- Real-time crypto news from 4 major sources
- Sentiment analysis (bullish/bearish keywords)
- Asset-specific filtering (BTC, ETH, SOL)

### 3. **Technical Analysis**
- AutoHedge multi-agent system (DeepSeek AI)
- Director, Quant, Risk, Execution agents
- Technical indicators: RSI, MACD, Bollinger Bands, MAs
- Real-time market data

### 4. **Trading Loop**
- Combines news + technical signals
- Executes when signal strength ≥ 5/20
- Checks every 15 minutes
- Monitors SL/TP continuously

---

## Files Created

```
AutoHedge/
├── trading_bot.py              # Core trading engine
├── news_monitor.py             # News aggregation + sentiment
├── main_trading_loop.py        # Main orchestrator
├── test_binance_connection.py  # API connection test
├── requirements_trading.txt    # Dependencies
├── TRADING_README.md           # Full usage guide
├── DEPLOYMENT_SUMMARY.md       # Quick reference
├── .env                        # Configuration (API keys)
└── bot_state.json             # Bot state (auto-created)
```

---

## Configuration (.env)

```bash
# Binance API
BINANCE_API_KEY=Qtd74mPBIryKGRWDSv9z6Aom57sM4Xke4TcSmy3tk6bR59zBLTdC51IlY8w4NNWm
BINANCE_SECRET_KEY=7NSWa3ivgxC14dVejm2qPv5vTvlqLlmgFsRXTX35gbRebEZ468OCNLNhFREbk8mM

# DeepSeek API
DEEPSEEK_API_KEY=sk-df04b6a1198445fcad4e9bf03b880e19
DEEPSEEK_MODEL=deepseek-chat

# Trading Parameters
CAPITAL_USDT=100
POSITION_SIZE_PCT=30
LEVERAGE=10
TAKE_PROFIT_PCT=10
STOP_LOSS_PCT=5
MAX_TRADES_PER_DAY=3
TRADING_PAIRS=BTC/USDT,ETH/USDT,SOL/USDT
CHECK_INTERVAL_MINUTES=15
MIN_SIGNAL_STRENGTH=5.0
NEWS_CHECK_HOURS=6
```

---

## ⚠️ BEFORE STARTING

### 1. Deposit Funds
**Current Futures balance: $0.00 USDT**

Transfer $100 USDT from Spot → Futures in Binance.

### 2. Test First
```bash
cd /Users/openclaw/.openclaw/workspace/AutoHedge
source venv/bin/activate
python main_trading_loop.py --test
```

### 3. Monitor Logs
```bash
tail -f trading_bot_*.log
```

---

## Start Trading

```bash
cd /Users/openclaw/.openclaw/workspace/AutoHedge
source venv/bin/activate
python main_trading_loop.py
```

Stop with `Ctrl+C`.

---

## Commands

```bash
# Test mode (run once)
python main_trading_loop.py --test

# Check status
python main_trading_loop.py --status

# Test Binance connection
python test_binance_connection.py

# Watch logs
tail -f trading_bot_*.log

# Emergency stop
pkill -f main_trading_loop.py
```

---

## Risk Warning

**$100 capital | 30% positions | 10x leverage | 5% SL**

- Max loss per trade: $15 (15% of account)
- 3 bad trades: -45% account
- 3 good trades: +90% account

**This is extremely aggressive. Be prepared for volatility.**

---

## 5-Day Validation

1. **Days 1-2:** Test mode only
2. **Days 3-4:** Live with $50 + 5x leverage
3. **Day 5:** Full parameters if profitable

**Decision:** Continue if <10% loss, stop if >20% loss.

---

## What the Bot Does

Every 15 minutes:
1. Check SL/TP on open positions → close if triggered
2. Fetch crypto news (last 6 hours)
3. Analyze sentiment (bullish/bearish)
4. Run AutoHedge technical analysis
5. Combine signals (news + technical)
6. Execute if signal ≥ 5/20 and no position exists
7. Max 3 trades/day

---

## Documentation

- **TRADING_README.md** - Full usage guide
- **DEPLOYMENT_SUMMARY.md** - Quick reference
- **autohedge/README.md** - Original AutoHedge docs

---

## Support

Reach me via:
- This chat (web UI)
- Telegram (approved ✓, user ID: 724213470)

---

**System is ready. Deposit funds, test first, then deploy carefully.**

— Irona ⚙️
