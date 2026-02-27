# Model Integration Architecture

## Problem Statement

The trained RL model expects a **state vector** (6 numbers) and outputs an **action** (0/1/2).

The trading bot currently uses **AutoHedge Director** (LLM) which analyzes text and generates decisions.

**How do we connect them?**

---

## State Representation

### What the Model Expects:

```python
state = np.array([
    price_change_pct,      # e.g., +2.5% or -1.3%
    rsi_normalized,        # RSI scaled to [-1, 1] range
    macd_normalized,       # MACD scaled
    volume_change_pct,     # Volume change
    position_encoding,     # -1 (SHORT), 0 (NONE), +1 (LONG)
    balance_normalized     # Portfolio performance
], dtype=np.float32)
```

**Size:** 6 numbers (observation_space)

### Where to Get This Data:

**From your trading bot:**
```python
# In main_trading_loop.py, you already have:
current_price = get_ticker_price(symbol)
rsi = calculate_rsi(symbol)
macd = calculate_macd(symbol)
volume = get_volume(symbol)
position = get_current_position(symbol)  # From paper_trading.py
balance = paper_trader.balance
```

---

## Integration Approaches

### Option 1: Replace AutoHedge (Simple, but loses reasoning)

```python
# main_trading_loop.py

from trained_model_wrapper import TrainedModelWrapper

# Load trained model
trained_model = TrainedModelWrapper('models/production/v1.2.0.zip')

async def check_and_trade():
    for symbol in ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']:
        # Get market data
        price = get_ticker_price(symbol)
        rsi = calculate_rsi(symbol)
        macd = calculate_macd(symbol)
        
        # Prepare state for model
        state = prepare_state(price, rsi, macd, volume, position, balance)
        
        # Get action from trained model
        action = trained_model.predict_action(state)
        
        if action == 1:  # LONG
            open_long_position(symbol, price)
        elif action == 2:  # SHORT
            open_short_position(symbol, price)
        else:  # HOLD
            continue
```

**Pros:**
- ✅ Simple integration
- ✅ Fast execution
- ✅ Uses trained model directly

**Cons:**
- ❌ Loses AutoHedge reasoning
- ❌ No news sentiment analysis
- ❌ Can't explain decisions

---

### Option 2: Hybrid (LLM analysis + RL decision) ⭐ RECOMMENDED

```python
# main_trading_loop.py

from trained_model_wrapper import TrainedModelWrapper
from autohedge.main import run_autohedge

# Load trained model
trained_model = TrainedModelWrapper('models/production/v1.2.0.zip')

async def check_and_trade():
    for symbol in ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']:
        # Get market data
        price = get_ticker_price(symbol)
        rsi = calculate_rsi(symbol)
        macd = calculate_macd(symbol)
        news_sentiment = await get_news_sentiment(symbol)
        
        # === STEP 1: AutoHedge generates analysis ===
        autohedge_analysis = await run_autohedge({
            'symbol': symbol,
            'price': price,
            'rsi': rsi,
            'macd': macd,
            'news': news_sentiment
        })
        
        # AutoHedge output: {
        #   'should_trade': True,
        #   'direction': 'LONG',
        #   'confidence': 0.75,
        #   'reasoning': "Bullish technical + positive news..."
        # }
        
        # === STEP 2: Trained model makes final decision ===
        state = prepare_state(price, rsi, macd, volume, position, balance)
        rl_action = trained_model.predict_action(state)
        
        # === STEP 3: Combine both signals ===
        if autohedge_analysis['should_trade'] and rl_action != 0:
            # Both agree to trade!
            
            # Check if directions match
            if autohedge_analysis['direction'] == 'LONG' and rl_action == 1:
                logger.info(f"✅ CONSENSUS: Both systems say LONG")
                open_long_position(symbol, price)
                
            elif autohedge_analysis['direction'] == 'SHORT' and rl_action == 2:
                logger.info(f"✅ CONSENSUS: Both systems say SHORT")
                open_short_position(symbol, price)
                
            else:
                logger.info(f"⚠️ CONFLICT: AutoHedge says {autohedge_analysis['direction']}, RL says {rl_action}")
                # Use confidence to break tie
                if autohedge_analysis['confidence'] > 0.8:
                    logger.info(f"→ Following AutoHedge (high confidence)")
                    execute_trade(autohedge_analysis['direction'])
                else:
                    logger.info(f"→ Following RL model")
                    execute_trade(rl_action)
        else:
            logger.info(f"❌ No trade: AutoHedge={autohedge_analysis['should_trade']}, RL={rl_action}")
```

**Pros:**
- ✅ Best of both worlds
- ✅ LLM provides reasoning + news analysis
- ✅ RL provides pattern-based decision
- ✅ Can explain decisions
- ✅ Consensus = higher confidence

**Cons:**
- ⚠️ More complex
- ⚠️ Slower (both systems run)

---

### Option 3: Ensemble Voting

```python
# Multiple models vote, majority wins

async def check_and_trade():
    # Get all signals
    autohedge_signal = await run_autohedge(data)
    rl_signal = trained_model.predict(state)
    technical_signal = simple_technical_strategy(rsi, macd)
    
    # Voting
    votes = {
        'LONG': 0,
        'SHORT': 0,
        'HOLD': 0
    }
    
    # Vote 1: AutoHedge
    if autohedge_signal['should_trade']:
        votes[autohedge_signal['direction']] += autohedge_signal['confidence']
    else:
        votes['HOLD'] += 1
    
    # Vote 2: RL Model
    if rl_signal == 1:
        votes['LONG'] += 1
    elif rl_signal == 2:
        votes['SHORT'] += 1
    else:
        votes['HOLD'] += 1
    
    # Vote 3: Technical
    votes[technical_signal] += 0.5
    
    # Winner
    winner = max(votes, key=votes.get)
    
    if winner != 'HOLD' and votes[winner] >= 2.0:  # Need at least 2 votes
        execute_trade(winner)
```

**Pros:**
- ✅ Multiple perspectives
- ✅ More robust
- ✅ Can add more signals easily

**Cons:**
- ⚠️ Complex logic
- ⚠️ May be too conservative

---

### Option 4: RL as Veto (Conservative)

```python
# AutoHedge decides, RL can veto

async def check_and_trade():
    # AutoHedge makes decision
    autohedge_decision = await run_autohedge(data)
    
    if autohedge_decision['should_trade']:
        # Check with RL model
        rl_action = trained_model.predict(state)
        
        # RL veto check
        if rl_action == 0:  # RL says HOLD
            logger.warning(f"⚠️ RL MODEL VETO: AutoHedge wanted to trade, RL blocked it")
            return  # Don't trade
        
        # RL approves (or suggests same direction)
        direction_map = {1: 'LONG', 2: 'SHORT'}
        rl_direction = direction_map.get(rl_action)
        
        if rl_direction == autohedge_decision['direction']:
            logger.info(f"✅ RL APPROVED: Proceeding with {rl_direction}")
            execute_trade(autohedge_decision)
        else:
            logger.warning(f"⚠️ RL DISAGREES: AutoHedge={autohedge_decision['direction']}, RL={rl_direction}")
            # Don't trade on disagreement
```

**Pros:**
- ✅ Conservative (reduces false positives)
- ✅ RL acts as safety check
- ✅ AutoHedge still generates reasoning

**Cons:**
- ⚠️ May miss opportunities
- ⚠️ RL can block good trades

---

## Implementation: State Preparation

### Core Function:

```python
# trained_model_wrapper.py

import numpy as np
from stable_baselines3 import PPO

class TrainedModelWrapper:
    """
    Wrapper to integrate trained PPO model with trading bot.
    """
    
    def __init__(self, model_path='models/production/v1.2.0.zip'):
        self.model = PPO.load(model_path)
        self.prev_price = {}  # Track price changes
        self.prev_volume = {}  # Track volume changes
    
    def prepare_state(
        self,
        symbol: str,
        current_price: float,
        rsi: float,
        macd: float,
        current_volume: float,
        position: str = None,  # 'LONG', 'SHORT', or None
        balance: float = 100.0,
        initial_balance: float = 100.0
    ) -> np.ndarray:
        """
        Convert raw market data into state vector for model.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            current_price: Current price in USDT
            rsi: RSI value (0-100)
            macd: MACD value
            current_volume: Current 24h volume
            position: Current position ('LONG'/'SHORT'/None)
            balance: Current balance
            initial_balance: Starting balance
        
        Returns:
            State vector (6 numbers)
        """
        
        # Calculate price change
        if symbol in self.prev_price:
            price_change_pct = ((current_price - self.prev_price[symbol]) / self.prev_price[symbol]) * 100
        else:
            price_change_pct = 0.0
        self.prev_price[symbol] = current_price
        
        # Calculate volume change
        if symbol in self.prev_volume:
            volume_change_pct = ((current_volume - self.prev_volume[symbol]) / self.prev_volume[symbol]) * 100 if self.prev_volume[symbol] > 0 else 0.0
        else:
            volume_change_pct = 0.0
        self.prev_volume[symbol] = current_volume
        
        # Normalize RSI to [-1, 1]
        rsi_normalized = (rsi - 50) / 50
        
        # Normalize MACD
        macd_normalized = macd / 100  # Approximate normalization
        
        # Encode position
        position_encoding = 0
        if position == 'LONG':
            position_encoding = 1
        elif position == 'SHORT':
            position_encoding = -1
        
        # Normalize balance
        balance_normalized = (balance - initial_balance) / initial_balance
        
        # Create state vector
        state = np.array([
            price_change_pct,
            rsi_normalized,
            macd_normalized,
            volume_change_pct,
            position_encoding,
            balance_normalized
        ], dtype=np.float32)
        
        return state
    
    def predict_action(
        self,
        symbol: str,
        current_price: float,
        rsi: float,
        macd: float,
        current_volume: float,
        position: str = None,
        balance: float = 100.0,
        initial_balance: float = 100.0
    ) -> int:
        """
        Predict trading action.
        
        Returns:
            0 = HOLD
            1 = LONG
            2 = SHORT
        """
        
        # Prepare state
        state = self.prepare_state(
            symbol, current_price, rsi, macd, current_volume,
            position, balance, initial_balance
        )
        
        # Get prediction
        action, _states = self.model.predict(state, deterministic=True)
        
        return int(action)
    
    def predict_with_confidence(self, *args, **kwargs) -> tuple:
        """
        Predict action with confidence score.
        
        Returns:
            (action: int, confidence: float)
        """
        state = self.prepare_state(*args, **kwargs)
        
        # Get action probabilities
        action, _states = self.model.predict(state, deterministic=False)
        
        # PPO stores action probabilities in policy
        # For simplicity, use deterministic prediction
        # Real confidence would need policy.get_distribution()
        
        return int(action), 0.75  # Placeholder confidence
```

---

## Integration Example (Complete)

```python
# main_trading_loop.py - MODIFIED

import asyncio
from trained_model_wrapper import TrainedModelWrapper
from autohedge.main import run_autohedge
from paper_trading import PaperTradingExecutor
from news_monitor import get_news_sentiment
from trading_bot import get_ticker_price, calculate_rsi, calculate_macd

# Load trained model
TRAINED_MODEL = TrainedModelWrapper('models/production/v1.2.0.zip')
paper_trader = PaperTradingExecutor()

async def check_and_trade_with_rl():
    """
    Main trading loop with RL integration.
    """
    
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
    
    for symbol in symbols:
        try:
            # === STEP 1: Collect market data ===
            current_price = get_ticker_price(symbol)
            rsi = calculate_rsi(symbol, period=14)
            macd = calculate_macd(symbol)
            volume = get_24h_volume(symbol)
            news_sentiment = await get_news_sentiment(symbol)
            
            # Get current position
            current_position = paper_trader.get_position(symbol)
            position_type = None
            if current_position:
                position_type = current_position['side']  # 'LONG' or 'SHORT'
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Analyzing {symbol}")
            logger.info(f"Price: ${current_price:,.2f} | RSI: {rsi:.1f} | MACD: {macd:.2f}")
            logger.info(f"Position: {position_type or 'NONE'} | Balance: ${paper_trader.balance:.2f}")
            
            # === STEP 2: AutoHedge analysis ===
            logger.info(f"\n🤖 Running AutoHedge Director...")
            autohedge_result = await run_autohedge({
                'symbol': symbol,
                'price': current_price,
                'rsi': rsi,
                'macd': macd,
                'news_sentiment': news_sentiment
            })
            
            logger.info(f"AutoHedge: {autohedge_result['direction']} "
                       f"(confidence: {autohedge_result['confidence']:.1%}, "
                       f"should_trade: {autohedge_result['should_trade']})")
            
            # === STEP 3: RL model prediction ===
            logger.info(f"\n🧠 Running RL Model...")
            rl_action = TRAINED_MODEL.predict_action(
                symbol=symbol,
                current_price=current_price,
                rsi=rsi,
                macd=macd,
                current_volume=volume,
                position=position_type,
                balance=paper_trader.balance
            )
            
            action_names = {0: 'HOLD', 1: 'LONG', 2: 'SHORT'}
            logger.info(f"RL Model: {action_names[rl_action]}")
            
            # === STEP 4: Decision logic (HYBRID APPROACH) ===
            logger.info(f"\n🎯 Making decision...")
            
            # Both must agree to trade
            if autohedge_result['should_trade'] and rl_action != 0:
                autohedge_direction = autohedge_result['direction']
                rl_direction = action_names[rl_action]
                
                if autohedge_direction == rl_direction:
                    # CONSENSUS!
                    logger.info(f"✅ CONSENSUS: Both systems agree on {rl_direction}")
                    logger.info(f"   AutoHedge reasoning: {autohedge_result.get('reasoning', 'N/A')}")
                    
                    # Execute trade
                    if rl_direction == 'LONG':
                        paper_trader.open_long(symbol, current_price)
                    elif rl_direction == 'SHORT':
                        paper_trader.open_short(symbol, current_price)
                    
                else:
                    # CONFLICT!
                    logger.warning(f"⚠️ CONFLICT: AutoHedge={autohedge_direction}, RL={rl_direction}")
                    
                    # Use AutoHedge confidence to break tie
                    if autohedge_result['confidence'] > 0.80:
                        logger.info(f"→ Following AutoHedge (high confidence: {autohedge_result['confidence']:.1%})")
                        if autohedge_direction == 'LONG':
                            paper_trader.open_long(symbol, current_price)
                        else:
                            paper_trader.open_short(symbol, current_price)
                    else:
                        logger.info(f"→ No trade on low-confidence conflict")
            
            else:
                # At least one says NO
                if not autohedge_result['should_trade']:
                    logger.info(f"❌ AutoHedge says NO TRADE")
                if rl_action == 0:
                    logger.info(f"❌ RL Model says HOLD")
            
            logger.info(f"{'='*60}\n")
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            continue
    
    # Check for position closures
    await paper_trader.check_positions()


async def main():
    logger.info("🚀 Trading Bot Started with RL Integration")
    
    while True:
        await check_and_trade_with_rl()
        await asyncio.sleep(900)  # 15 minutes


if __name__ == '__main__':
    asyncio.run(main())
```

---

## Configuration

Add to `.env`:

```bash
# RL Model Integration
USE_RL_MODEL=true
RL_MODEL_PATH=models/production/v1.2.0.zip
RL_INTEGRATION_MODE=hybrid  # hybrid, replace, veto, ensemble

# Decision thresholds
RL_MIN_CONFIDENCE=0.70
REQUIRE_CONSENSUS=true  # Both systems must agree
AUTOHEDGE_OVERRIDE_THRESHOLD=0.85  # High confidence overrides RL
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    MARKET DATA                          │
│  (Binance API, News Sources, Technical Indicators)     │
└────────────────────┬────────────────────────────────────┘
                     │
                     ├──────────────────┬─────────────────┐
                     ▼                  ▼                 ▼
              ┌─────────────┐    ┌──────────┐    ┌──────────┐
              │  AutoHedge  │    │ RL Model │    │Technical │
              │  Director   │    │   PPO    │    │ Strategy │
              │   (LLM)     │    │ (Trained)│    │ (Simple) │
              └──────┬──────┘    └────┬─────┘    └────┬─────┘
                     │                │               │
                     │ Direction      │ Action        │ Signal
                     │ Confidence     │ (0/1/2)       │
                     │ Reasoning      │               │
                     └────────┬───────┴───────────┬───┘
                              │                   │
                              ▼                   ▼
                      ┌────────────────────────────────┐
                      │    DECISION COMBINER           │
                      │  (Consensus/Voting/Veto Logic) │
                      └────────────┬───────────────────┘
                                   │
                                   ▼
                           ┌───────────────┐
                           │  EXECUTE      │
                           │  TRADE        │
                           └───────────────┘
                                   │
                                   ▼
                         ┌──────────────────┐
                         │ Paper Trading     │
                         │ or Live Execution │
                         └──────────────────┘
```

---

## Summary

**Answer to "How are u planning to ingest the input in the model?"**

1. **Extract** market data (price, RSI, MACD, volume) from trading bot
2. **Normalize** into 6-number state vector
3. **Feed** to trained PPO model
4. **Get** action (0=HOLD, 1=LONG, 2=SHORT)
5. **Combine** with AutoHedge analysis using hybrid approach
6. **Execute** if both systems agree (consensus)

**Integration modes:**
- 🥇 **Hybrid** (recommended): LLM + RL together
- 🥈 **Replace**: RL only (simple but loses reasoning)
- 🥉 **Veto**: LLM decides, RL can block
- 🏅 **Ensemble**: Multiple models vote

**Files needed:**
- `trained_model_wrapper.py` (state preparation + prediction)
- Modified `main_trading_loop.py` (integration logic)
- Config in `.env` (mode selection)
