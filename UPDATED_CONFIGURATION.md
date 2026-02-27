# AutoHedge Bot - Updated Configuration

**Status:** ✅ Running (PID 66299)  
**Started:** 2026-02-22 20:59:26 IST  
**Mode:** Paper Trading

---

## Changes Made

### 1. Position Size Increased ✅

**Old:** 30% of capital  
**New:** 40% of capital

**With $100 USDT balance + 10x leverage:**
- Position size: $40 USDT
- Leverage: 10x
- **Effective exposure: $400 per trade** ✅

### 2. Trade Selection Logic Changed ✅

**Old behavior:**
- Analyzed BTC → if good, trade BTC
- Then ETH → if good, trade ETH (if BTC wasn't traded)
- Then SOL → if good, trade SOL (if neither BTC nor ETH traded)
- **Result:** Traded first valid signal

**New behavior:**
- Analyze ALL 3 cryptos first (BTC + ETH + SOL)
- Compare all valid signals
- **Trade ONLY the BEST one** (highest combined_score)

### 3. Director Veto Kept ✅

**Decision:** Keep AutoHedge Director's NO-GO veto
- If Director says NO-GO, signal won't trade
- Even if score is above threshold
- Ensures quality over quantity

---

## Current Bot Logic

### Analysis Flow:

```
1. Check existing positions & SL/TP
2. Analyze BTC:
   - Fetch news (BEARISH/BULLISH/NEUTRAL)
   - Run AutoHedge (5 agents: Thesis, Quant, Risk, Order, Director)
   - Calculate combined_score (0-20)
   - Check: score >= 4.0 AND Director != NO-GO

3. Analyze ETH:
   - Same process

4. Analyze SOL:
   - Same process

5. Compare all valid signals
6. Pick BEST one (highest score)
7. Execute ONLY that trade
```

### Signal Scoring (0-20 scale):

- **News contribution:**
  - Bullish news: +0 to +10
  - Bearish news: +0 to +10
  - Neutral: +0

- **AutoHedge contribution:**
  - If Director says GO: +confidence (0-10)
  - If Director says NO-GO: signal invalid

- **Conflicts:**
  - If news and AutoHedge disagree: score × 0.5

### Trade Execution:

**Requirements:**
- `combined_score >= 4.0`
- `trade_direction != None`
- `analysis['decision'] != 'NO-GO'`

**Position parameters:**
- Size: 40% of capital
- Leverage: 10x
- Stop Loss: 5%
- Take Profit: 10%
- Max trades per day: 3

---

## Example Scenarios

### Scenario 1: Strong News + Director Approval
```
BTC Analysis:
  News: BEARISH (10/10)
  AutoHedge: GO / SHORT (8/10)
  Combined: 10 + 8 = 18/20
  Result: ✅ TRADE BTC SHORT

ETH Analysis:
  News: NEUTRAL (0/10)
  AutoHedge: GO / LONG (6/10)
  Combined: 0 + 6 = 6/20
  Result: ✅ Valid but lower than BTC

SOL Analysis:
  News: BULLISH (5/10)
  AutoHedge: NO-GO / LONG (7/10)
  Combined: Invalid (Director veto)
  Result: ❌ No trade

Winner: BTC (18/20) → SHORT $400 position
```

### Scenario 2: All Signals Weak
```
BTC: 3/20 (below 4.0 threshold)
ETH: 2/20 (below 4.0 threshold)
SOL: NO-GO (Director veto)

Result: No trades executed
```

### Scenario 3: Director Blocks Everything
```
BTC: News 10/10, AutoHedge NO-GO → Invalid
ETH: News 8/10, AutoHedge NO-GO → Invalid
SOL: News 7/10, AutoHedge NO-GO → Invalid

Result: No trades executed (all vetoed)
```

---

## Monitoring

**Log file:** `~/workspace/AutoHedge/bot_output_new.log`

**Key indicators to watch:**
- `ANALYZING ALL CRYPTOS` - Start of analysis cycle
- `BEST OPPORTUNITY: [SYMBOL]` - Winner selected
- `Successfully opened [DIRECTION] position` - Trade executed
- `NO VALID TRADE SIGNALS` - No trades this cycle

**Check status:**
```bash
tail -f ~/.openclaw/workspace/AutoHedge/bot_output_new.log | grep -E "(🔍|⭐|BEST|Signal Summary)"
```

---

## Trading Rules Applied

✅ **Position sizing:** 40% × 10x = 400% exposure per trade  
✅ **Best-of-3 selection:** Compares all signals, trades the winner  
✅ **Director veto:** Quality filter active  
✅ **Risk management:** SL 5%, TP 10%, max 3 trades/day  
✅ **Paper trading:** Safe testing with real prices  

---

## Expected Behavior

**Frequency:**
- Analysis cycle: Every 15 minutes
- ~96 checks per day
- Expected trades: 0-3 per day (highly selective)

**Why trades might not happen:**
- Market ranging (no clear trends)
- Director being conservative
- News not strong enough
- All signals below 4.0 threshold

**This is normal** - The bot is designed to wait for high-conviction opportunities.

---

## Files

```
AutoHedge/
├── .env                      # Config (POSITION_SIZE_PCT=40)
├── main_trading_loop.py      # Updated logic (best-of-3)
├── bot_output_new.log        # Current run logs
├── paper_trading_*.log       # Paper trade history
└── bot_state.json            # Position state (will be created on first trade)
```

---

**Next:** Wait for first complete analysis cycle (~10-15 minutes) to see if any trades execute. ⚙️
