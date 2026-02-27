# Episode Monitoring Guide

Automated monitoring system to track trading bot progress and alert when ready for Agent Lightning training.

## Quick Start

### Manual Check (Run Anytime)

```bash
./check_episodes.sh
```

Shows current status:
- Bot running? ✅/❌
- Episode count
- Balance
- Daily reset status

### Setup Automated Monitoring (Cron)

```bash
./setup_monitor.sh
```

Interactive setup:
1. Choose check frequency (every 2/4/6 hours)
2. Installs cron job
3. Sends alerts at milestones

**Recommended:** Every 2 hours (12 checks/day)

---

## Alert Milestones

The monitor sends alerts at these thresholds:

| Episodes | Alert | Meaning |
|----------|-------|---------|
| **40** | 📊 Progress Update | Getting close to training ready |
| **50** | 🎯 **READY FOR TRAINING** | Minimum episodes for Agent Lightning |
| **75** | 📈 Good Progress | High confidence data |
| **100** | 🚀 **EXCELLENT** | Production-ready dataset |
| **150** | 💎 Premium Dataset | Very strong learning signal |
| **200** | 🏆 Elite Dataset | Maximum confidence |

---

## What Gets Monitored

### 1. Bot Health
- **Running?** Process check
- **Logs:** Latest bot log file
- **Uptime:** How long running

### 2. Episode Count
- Tracks completed trades (OPENED/CLOSED)
- Compares to last check
- Shows progress to next milestone

### 3. Balance
- Current USDT balance
- Warns if below $30 (high loss rate)

### 4. Daily Reset
- Checks if trade counter resets at midnight
- Warns if stuck (like the Feb 23-27 bug)

---

## Alert Types

### 🎯 SUCCESS (Green)
- Episode milestones reached (50, 100, etc.)
- Ready for training

### ℹ️ INFO (Blue)
- Progress updates (40, 75, etc.)
- New episodes collected

### ⚠️ WARNING (Yellow)
- Low balance (<$30)
- Daily reset not working

### ❌ ERROR (Red)
- Bot stopped/crashed
- Critical issues

---

## Alert Delivery

### Terminal Output
Colored, formatted alerts in console

### macOS Notifications
Native notification center alerts (if available)

### Log Files
All checks logged to `logs/monitor.log`

---

## Files

```
episode_monitor.py          Main monitoring script
setup_monitor.sh           Interactive cron setup
check_episodes.sh          Quick manual check
monitor_state.json         State tracking (auto-created)
logs/monitor.log           Monitor check history
```

---

## Cron Management

### View Active Cron Jobs
```bash
crontab -l
```

### View Monitor Logs
```bash
tail -f logs/monitor.log
```

### Remove Cron Job
```bash
crontab -l | grep -v episode_monitor.py | crontab -
```

### Reinstall/Change Schedule
```bash
./setup_monitor.sh
# Choose new schedule when prompted
```

---

## When You Get the 50-Episode Alert

**You'll see:**
```
🎯 MILESTONE: 50 episodes collected!

✅ Ready for Agent Lightning training!

Next steps:
1. Review episode quality
2. Run: python phase2_agent_lightning_finetune.py
3. Let training run overnight (2-4 hours)
4. Validate results and deploy
```

**What to do:**

### 1. Review Episode Quality
```bash
# Check recent trades
tail -100 bot_restart_*.log | grep -E "OPENED|CLOSED"

# Check win rate
./daily_report.sh
```

### 2. Start Agent Lightning Training
```bash
source venv/bin/activate
python phase2_agent_lightning_finetune.py
```

Training takes 2-4 hours. Let it run overnight.

### 3. Validate Results
After training completes:
- Check validation metrics (win rate, accuracy)
- Compare to baseline
- Review quality gates

### 4. Deploy (if validation passes)
```bash
# Update .env
USE_RL_MODEL=true
RL_MODEL_PATH=models/agent_lightning/final_model/

# Restart bot
kill $(pgrep -f main_trading_loop.py)
nohup python main_trading_loop.py > bot_with_agent_lightning.log 2>&1 &
```

---

## Troubleshooting

### Monitor says bot is running, but no trades

**Check:**
```bash
tail -50 bot_restart_*.log
```

**Possible reasons:**
- Signal threshold too high (no strong signals)
- Market ranging (no clear opportunities)
- Daily trade limit reached

### Monitor shows old episode count

**Fix:** Monitor might be reading old log file. Check:
```bash
ls -lt *.log | head -5
```

Delete old logs if needed:
```bash
rm bot_local_final.log  # Old log from before restart
```

### Cron job not running

**Check cron status:**
```bash
crontab -l  # Should show episode_monitor.py line
```

**Check permissions:**
```bash
chmod +x episode_monitor.py
chmod +x setup_monitor.sh
```

**Check logs:**
```bash
tail -20 logs/monitor.log
```

---

## Advanced: Custom Thresholds

Edit `episode_monitor.py` line ~15:

```python
ALERT_THRESHOLDS = [40, 50, 75, 100, 150, 200]
```

Add your own milestones:
```python
ALERT_THRESHOLDS = [25, 40, 50, 75, 100, 150, 200, 300]
```

---

## Performance Notes

- **Check frequency:** Every 2 hours is optimal (12/day)
  - More frequent = faster alerts, more overhead
  - Less frequent = miss milestones, delayed response
  
- **Resource usage:** Minimal (<1 second per check)

- **Log rotation:** Monitor logs don't auto-rotate
  - Manually clean `logs/monitor.log` if it grows large
  - Or add log rotation to cron

---

## Example Output

```
🔍 Episode Monitor - 2026-02-27 16:00:00

Bot Running:     ✅ YES
Log File:        bot_restart_20260227_140456.log
Episodes:        52 collected
Daily Reset:     ✅ Working
Balance:         $112.34 USDT
Last Check:      2026-02-27 14:00:00

📈 New episodes since last check: +12

🎯 MILESTONE: 52 episodes collected!

✅ Ready for Agent Lightning training!

Next steps:
1. Review episode quality
2. Run: python phase2_agent_lightning_finetune.py
3. Let training run overnight (2-4 hours)
4. Validate results and deploy

Target: 75 episodes for high confidence

✓ Monitor check complete

🎯 Status: READY FOR AGENT LIGHTNING TRAINING
```

---

## Integration with Daily Reports

Episode monitor is separate from daily reports:

| Feature | Episode Monitor | Daily Reports |
|---------|----------------|---------------|
| **Purpose** | Training readiness | Performance tracking |
| **Frequency** | Every 2-4 hours | Once daily (9 AM) |
| **Focus** | Episode count | Win rate, PnL, trades |
| **Alerts** | Milestone-based | Performance issues |
| **Action** | Start training | Review strategy |

**Use both:**
- Episode monitor: "Are we ready to train?"
- Daily reports: "How's the strategy performing?"

---

## Next Steps After 100 Episodes

Once you hit 100 episodes with Agent Lightning:

1. **Model is mature** - Strong learning signal
2. **Consider live trading** - If win rate >60%
3. **Adjust monitoring** - Reduce check frequency (every 6h)
4. **Focus on performance** - Use daily reports more
5. **Continuous improvement** - Retrain every 50-100 new episodes

---

**Questions?** Check:
- `AGENT_LIGHTNING_PLAN.md` - Training details
- `DAILY_REPORTS_GUIDE.md` - Performance monitoring
- `phase2_agent_lightning_finetune.py` - Training script

---

_Last updated: 2026-02-27_
