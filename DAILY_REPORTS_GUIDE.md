# 📊 Daily Performance Reports

Automated system health and performance tracking for your trading bot.

---

## ✅ What You Get

### System Status
- ✅ Trading bot uptime and health
- ✅ Continuous learner status
- ⚠️ Alerts if anything stopped

### Trading Performance (Last 24h)
- 💰 Current balance and PnL
- 📈 Win rate and trade statistics
- 📊 Performance by symbol (BTC/ETH/SOL)
- 🎯 Positions opened/closed

### Learning Progress
- 🧠 Episodes processed
- 🔄 Training cycles completed
- 📅 Last training time
- 🔮 Next training estimate
- 📦 Latest model info

### Smart Recommendations
- 🎯 Issues detected (if any)
- 💡 Actionable next steps
- ✨ Deployment readiness

---

## 🚀 Quick Start

### View Report Now
```bash
cd ~/workspace/AutoHedge
./daily_report.sh
```

### Save Report to File
```bash
python3 generate_daily_report.py --save
```

### View Saved Reports
```bash
ls -lh reports/
cat reports/daily_report_*.txt
```

---

## ⏰ Automated Daily Reports

### Setup (One-time)
```bash
./setup_daily_reports.sh
```

This will:
1. Add cron job for 9:00 AM daily
2. Auto-save reports to `reports/` directory
3. Log to `logs/daily_reports.log`

### Verify Cron Setup
```bash
crontab -l | grep daily_report
```

### Change Schedule
Edit cron timing:
```bash
crontab -e
```

Cron format: `minute hour day month weekday command`

Examples:
- `0 9 * * *` - 9:00 AM daily
- `0 9,18 * * *` - 9 AM and 6 PM
- `0 9 * * 1` - 9 AM every Monday
- `0 */6 * * *` - Every 6 hours

---

## 📋 Usage Examples

### Standard Report (24 hours)
```bash
python3 generate_daily_report.py
```

### Last 48 Hours
```bash
python3 generate_daily_report.py --hours 48
```

### Last Week
```bash
python3 generate_daily_report.py --hours 168
```

### Save Without Displaying
```bash
python3 generate_daily_report.py --save > /dev/null 2>&1
```

---

## 📊 Report Sections Explained

### System Status
Shows if bot and learner are running. If either stopped:
- **Bot stopped:** No trading happening, data not accumulating
- **Learner stopped:** No retraining happening, model not improving

**Fix:** Check logs and restart:
```bash
./status.sh  # Shows PIDs
ps aux | grep main_trading_loop  # Check bot
ps aux | grep continuous_learner  # Check learner
```

### Trading Performance
**Key metrics:**
- **Win Rate:** % of profitable trades (target: 50%+)
- **PnL:** Profit/loss percentage from starting balance
- **Positions Opened:** New trades entered
- **Positions Closed:** Trades exited (with PnL realized)
- **Signals Generated:** Total analysis runs (not all lead to trades)

**Interpretation:**
- Low win rate + many trades → Strategy needs improvement (wait for training)
- High win rate + few trades → Conservative strategy (working as intended)
- Many signals, few trades → Min signal threshold filtering (good)

### Learning Progress
**Key metrics:**
- **Episodes:** Trading decisions logged (need 50+ for deployment)
- **Training Cycles:** How many times model retrained
- **Next Training:** Retrains every 20 new episodes

**Milestones:**
- 20 episodes → First training possible
- 50 episodes → Deployment consideration
- 100 episodes → High confidence deployment
- 200+ episodes → Mature system

### Recommendations
System automatically suggests:
- When to accumulate more data
- When ready to deploy RL model
- Issues requiring attention
- Performance improvements

---

## 🔍 Interpreting Results

### Good Signs ✅
- Both systems running
- Win rate trending upward
- Episodes accumulating steadily
- Regular training cycles
- No critical issues

### Warning Signs ⚠️
- System stopped
- No trades in 24h (check market conditions)
- Win rate declining
- No training cycles
- Validation worse than training (overfitting)

### Action Needed ❌
- Bot/learner stopped → Restart immediately
- Win rate <30% after 50+ episodes → Review strategy
- No episodes growing → Check bot logs for errors

---

## 📁 File Locations

```
AutoHedge/
├── generate_daily_report.py   # Report generator
├── setup_daily_reports.sh     # Cron setup script
├── daily_report.sh            # Quick report trigger
├── reports/                   # Saved reports
│   └── daily_report_*.txt
└── logs/
    └── daily_reports.log      # Cron execution log
```

---

## 🛠️ Customization

### Add Custom Metrics
Edit `generate_daily_report.py` and add to `parse_bot_logs()` or `parse_learner_state()`:

```python
# Example: Track max drawdown
if 'drawdown' in line:
    dd_match = re.search(r'([-]?\d+\.?\d*)%', line)
    if dd_match:
        stats['max_drawdown'] = float(dd_match.group(1))
```

### Change Report Time
```bash
crontab -e
# Change: 0 9 * * *
# To:     0 21 * * *  (9 PM instead)
```

### Email Reports
Install mail utility:
```bash
brew install mailutils  # macOS
```

Modify cron:
```bash
0 9 * * * cd ~/workspace/AutoHedge && python3 generate_daily_report.py | mail -s "Trading Report" your@email.com
```

---

## 📧 Future Enhancements

Coming soon:
- ✉️ Email integration
- 📱 Telegram notifications
- 📊 Charts and graphs (PNG attachments)
- 📈 Weekly/monthly aggregated reports
- 🎯 Performance trends over time
- ⚡ Real-time alerts for significant events

---

## 🐛 Troubleshooting

### Cron Not Running
```bash
# Check cron service
ps aux | grep cron

# Check cron logs (macOS)
log show --predicate 'process == "cron"' --last 1d

# Test manually
cd ~/workspace/AutoHedge
python3 generate_daily_report.py --save
```

### Report Errors
```bash
# Check Python environment
which python3

# Check file permissions
ls -l generate_daily_report.py

# Run with debug
python3 generate_daily_report.py 2>&1 | more
```

### Missing Data
- Bot not running → No trade data
- Learner not running → No training data
- Logs deleted → Historical data lost

**Solution:** Ensure both systems running continuously

---

## 💡 Pro Tips

1. **Review daily** - Quick `./daily_report.sh` each morning
2. **Track trends** - Compare reports over time
3. **Save milestones** - Keep reports at 50, 100, 200 episodes
4. **Watch recommendations** - System tells you what to do next
5. **Check before changes** - Generate report before deploying updates

---

## 📞 Quick Reference

```bash
# Generate report
./daily_report.sh

# Save report
python3 generate_daily_report.py --save

# Setup automation
./setup_daily_reports.sh

# View saved reports
ls -lh reports/

# Check cron status
crontab -l

# System status
./status.sh
```

---

**Your trading system just got smarter!** 📊⚙️

Track progress without manual checking. Know exactly when to deploy, when to wait, and when something needs attention.
