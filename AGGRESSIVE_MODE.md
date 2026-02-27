# AGGRESSIVE MODE - Paper Trading

**Purpose:** Test AutoHedge by taking RISKS (it's paper trading, no real money!)

---

## Changes Made for Aggressive Testing

### 1. ✅ Lowered Signal Threshold
**Old:** 4.0/20 (very selective)  
**New:** 2.0/20 (much more aggressive)

**Impact:** Will trade on much weaker signals

### 2. ✅ Removed Director Veto (Paper Trading Only)
**Old:** Director NO-GO = no trade  
**New:** Director NO-GO = trade anyway (with warning)

**Code logic:**
```python
if paper_trading:
    # Ignore Director veto - take risks!
    should_trade = (score >= 2.0 AND direction exists)
else:
    # Live trading: respect Director
    should_trade = (score >= 2.0 AND direction exists AND Director != NO-GO)
```

### 3. ✅ Position Size: $400 per trade
Still 40% × 10x leverage = $400 effective

---

## What This Means

### Much More Likely to Trade:

**Before (Conservative):**
- Needed 4.0/20 score + Director approval
- Result: 0 trades in 15 hours

**Now (Aggressive):**
- Only needs 2.0/20 score
- Director veto IGNORED
- Result: Should trade soon!

---

## Example Scenarios

### Scenario 1: Weak Signal (Would Not Trade Before)
```
BTC:
  News: NEUTRAL (0/10)
  AutoHedge: NO-GO / LONG (3/10)
  Combined: 0 + 3 = 3.0/20
  
Old behavior: ❌ No trade (below 4.0 AND Director veto)
New behavior: ✅ TRADE! (3.0 > 2.0, Director ignored)
```

### Scenario 2: Any Signal Above 2.0
```
ETH:
  News: BULLISH (2/10)
  AutoHedge: NO-GO / LONG (4/10)
  Combined: 2 + 4 = 6.0/20
  
Old behavior: ❌ No trade (Director veto)
New behavior: ✅ TRADE! (6.0 > 2.0, Director ignored)
```

### Scenario 3: Even Weak News Enough
```
SOL:
  News: BEARISH (3/10)
  AutoHedge: NO-GO / SHORT (1/10)
  Combined: 3 + 1 = 4.0/20
  
Old behavior: ❌ No trade (Director veto)
New behavior: ✅ TRADE! (4.0 > 2.0, Director ignored)
```

---

## Expected Behavior

**Next analysis cycle (9:15 PM):**
- Bot will analyze all 3 cryptos
- Pick best score above 2.0
- **SHOULD EXECUTE TRADE** (much more likely now!)

**Why this will work:**
- AutoHedge agents often give 5-7/10 confidence
- Even with neutral news (0), that's enough (5-7 > 2.0)
- Director can't block it anymore

---

## Safety Note

**⚠️ THIS IS ONLY FOR PAPER TRADING!**

When switching to live trading:
- This aggressive mode will NOT apply
- Director veto will be respected
- Threshold will be higher (or adjustable)

**Current mode:** Paper trading = Take risks to test system ✅

---

## Monitoring

**Watch for:**
```bash
tail -f ~/workspace/AutoHedge/bot_aggressive.log | grep -E "(BEST OPPORTUNITY|Successfully opened|⚠️ Director said NO-GO)"
```

**What you'll see:**
- `⚠️ Director said NO-GO but overriding for paper trading test` - Good! Taking risks
- `BEST OPPORTUNITY: BTC` - Winner selected
- `Successfully opened LONG position in BTCUSDT` - TRADE EXECUTED! 🎉

---

## Config Summary

| Setting | Conservative | Aggressive (Now) |
|---------|-------------|------------------|
| Threshold | 4.0/20 | **2.0/20** |
| Director Veto | Respected | **Ignored** |
| Position Size | $400 | $400 |
| Max Trades/Day | 3 | 3 |
| Mode | Paper | Paper |

---

**Status:** ✅ Running aggressively (PID 66903)  
**Expected:** First trade within 15-30 minutes  
**Log:** `~/workspace/AutoHedge/bot_aggressive.log`

Let's see AutoHedge work! 🚀
