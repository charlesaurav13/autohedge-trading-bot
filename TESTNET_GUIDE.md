# 🧪 Testnet Setup Guide

## Why Testnet?

Test the trading strategy with **real market data** but **fake money** before risking real capital.

---

## Step 1: Get Testnet API Keys

### Go to Binance Futures Testnet
**URL:** https://testnet.binancefuture.com/

1. Click **"Generate HMAC_SHA256 Key"**
2. Copy the **API Key** and **Secret Key**
3. You'll get **10,000 fake USDT** to test with

**No signup required** — keys are generated instantly.

---

## Step 2: Configure Testnet Mode

Edit the `.env` file:

```bash
cd /Users/openclaw/.openclaw/workspace/AutoHedge
nano .env
```

Add your testnet keys:

```bash
# Binance Testnet API (for testing with fake money)
BINANCE_TESTNET_API_KEY=your_testnet_api_key_here
BINANCE_TESTNET_SECRET_KEY=your_testnet_secret_key_here

# Trading Mode (testnet or live)
TRADING_MODE=testnet
```

Save and exit (Ctrl+X, Y, Enter).

---

## Step 3: Run Bot in Testnet

### Test Connection
```bash
source venv/bin/activate
python test_binance_connection.py
```

Should show:
- 🧪 Testnet mode active
- Balance: ~10,000 USDT (fake)

### Run Test Mode (Single Check)
```bash
python main_trading_loop.py --test
```

This will:
- Check news signals
- Run AutoHedge analysis
- Execute 1 trade if signals align
- Exit

### Run Continuous (Recommended)
```bash
python main_trading_loop.py
```

- Checks every 15 minutes
- Max 3 trades/day
- Automatic SL/TP monitoring
- Press Ctrl+C to stop

---

## Step 4: Monitor Results

### Watch Logs in Real-Time
```bash
tail -f trading_bot_*.log
```

### Check Status
```bash
python main_trading_loop.py --status
```

Shows:
- Testnet balance
- Open positions
- Daily trades
- Current PnL

### Check on Binance Testnet Web
Go to: https://testnet.binancefuture.com/en/futures/BTCUSDT

- Log in with your testnet API key
- View positions, orders, PnL
- Same interface as live Binance

---

## What to Test For

### Day 1-2: Strategy Validation
- ✓ Does it open positions correctly?
- ✓ Are SL/TP levels accurate?
- ✓ Does it close at SL/TP?
- ✓ Are signals reasonable?
- ✓ Does it respect 3 trades/day limit?

### Day 3-5: Performance
- What's the win rate?
- Average profit per trade?
- Largest drawdown?
- Are the signals too aggressive/conservative?

---

## Adjusting Parameters

If testnet results look bad:

### Reduce Risk
```bash
POSITION_SIZE_PCT=20    # Lower from 30%
LEVERAGE=5              # Lower from 10x
STOP_LOSS_PCT=3         # Tighter stop
```

### Increase Signal Quality
```bash
MIN_SIGNAL_STRENGTH=7.0  # Raise from 5.0 (fewer but stronger signals)
NEWS_CHECK_HOURS=12      # Look at more news
```

### Reduce Trading Frequency
```bash
MAX_TRADES_PER_DAY=2     # Lower from 3
CHECK_INTERVAL_MINUTES=30 # Check less often
```

---

## Switch to Live Mode

**ONLY after 5 days of testnet + good results:**

1. Edit `.env`:
   ```bash
   TRADING_MODE=live
   ```

2. Deposit $100 USDT to **real Futures account**

3. Restart bot:
   ```bash
   python main_trading_loop.py
   ```

The bot will show: **💰 LIVE MODE (REAL MONEY)**

---

## Testnet vs Live Differences

| Feature | Testnet | Live |
|---------|---------|------|
| Money | Fake (10k USDT) | Real ($100) |
| Market data | Real-time | Real-time |
| Order execution | Simulated | Real |
| Risk | Zero | High |
| Fees | None | ~0.04% per trade |
| Slippage | Minimal | Can be significant |

**Testnet is optimistic** — live trading will have more slippage and fees.

---

## Commands Cheatsheet

```bash
# Get testnet keys
# → https://testnet.binancefuture.com/

# Edit config
nano .env

# Test connection
python test_binance_connection.py

# Run once
python main_trading_loop.py --test

# Run continuous
python main_trading_loop.py

# Check status
python main_trading_loop.py --status

# Watch logs
tail -f trading_bot_*.log

# Stop bot
Ctrl+C
```

---

## Expected Timeline

**Days 1-2:** Testnet setup + observation  
**Days 3-5:** Full testnet validation (adjust if needed)  
**Day 6+:** Switch to live if profitable/break-even

**Target:** 50%+ win rate, positive PnL after fees

---

## Testnet Known Issues

1. **Slower execution** — testnet can lag slightly
2. **No real liquidity** — orders fill easier than live
3. **Fake balance doesn't reset** — if you blow the account, generate new keys

These are minor. Testnet is still the best way to validate strategy logic.

---

**Next Steps:**
1. Go to https://testnet.binancefuture.com/
2. Generate API keys (takes 10 seconds)
3. Add them to `.env`
4. Run `python main_trading_loop.py --test`

Let me know when you have the testnet keys ready. ⚙️
