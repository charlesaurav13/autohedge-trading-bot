# AutoHedge Trading Bot - OpenClaw Integration

## 🤖 What This Is

An AI-powered cryptocurrency trading bot with reinforcement learning (RL) capabilities, integrated with OpenClaw agent memory and context.

**Latest Performance:** +27.69% gain in 9 hours (3 SHORT positions closed on 2026-02-28)

## 📂 Repository Contents

### Trading Bot Files
- `main_trading_loop.py` - Main bot entry point
- `paper_trading.py` - Paper trading simulator (no real money)
- `trading_bot.py` - Live trading implementation
- Training scripts for RL model fine-tuning
- Episode monitoring and automated learning

### OpenClaw Memory Context
- **`memory/`** - Agent memory logs (2026-02-21 to 2026-02-28)
- `AGENTS.md` - Agent workspace guidelines
- `SOUL.md` - Agent personality  
- `USER.md` - User context
- `TOOLS.md` - Tool configuration
- `IDENTITY.md` - Agent identity
- `HEARTBEAT.md` - Proactive checks

## 🚀 Quick Start

```bash
# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements_trading.txt

# Configure API keys
cp .env.example .env
# Edit .env with your Binance API keys

# Run paper trading (safe mode)
python3 main_trading_loop.py
```

## 📊 Trading Strategy

**Model:** DeepSeek-R1-Distill-Llama-8B

**Risk Management:**
- Position size: 30-40% per trade
- Leverage: 10x
- Stop Loss: 5% | Take Profit: 10%
- Max daily trades: 3

**Supported Pairs:** BTC/USDT, ETH/USDT, SOL/USDT

## 📈 Recent Performance

**2026-02-27 to 2026-02-28:**
- 3 SHORT positions closed profitably
- **Total P&L: +$27.69 USDT (+27.69%)**
- Starting balance: $100 → Final: $127.69

Details in `memory/2026-02-28.md`

## ⚠️ Disclaimer

**USE AT YOUR OWN RISK.** Cryptocurrency trading is highly volatile. Start with paper trading. No warranties provided.

## 📚 Documentation

- `TRADING_README.md` - Trading bot overview
- `AGENT_LIGHTNING_PLAN.md` - RL training plan
- `EPISODE_MONITORING_GUIDE.md` - Episode collection
- `PAPER_TRADING_TEST_SUMMARY.md` - Test results

## 🤝 OpenClaw Integration

Includes full agent memory and context for seamless deployment on any system.

---

**Created:** 2026-02-28 | **Status:** Experimental - Paper Trading Validated ✅
