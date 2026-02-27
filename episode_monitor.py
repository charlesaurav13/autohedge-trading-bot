#!/usr/bin/env python3
"""
Episode Monitor - Alert when ready for Agent Lightning training
Checks episode count and bot health, sends alerts at milestones
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
import subprocess

# Thresholds for alerts
ALERT_THRESHOLDS = [40, 50, 75, 100, 150, 200]
STATE_FILE = "monitor_state.json"

def load_state():
    """Load monitoring state"""
    if Path(STATE_FILE).exists():
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {
        'last_check': None,
        'last_episode_count': 0,
        'alerts_sent': [],
        'last_alert_time': None
    }

def save_state(state):
    """Save monitoring state"""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def get_latest_bot_log():
    """Find the most recent bot log file"""
    # Check for bot_restart_*.log files (newest first)
    restart_logs = sorted(Path('.').glob('bot_restart_*.log'), key=lambda p: p.stat().st_mtime, reverse=True)
    if restart_logs:
        return str(restart_logs[0])
    
    # Fall back to bot_local_final.log
    if Path('bot_local_final.log').exists():
        return 'bot_local_final.log'
    
    return None

def count_episodes():
    """Count episodes in bot log"""
    log_file = get_latest_bot_log()
    if not log_file:
        return 0
    
    try:
        # Count OPENED or CLOSED lines (each represents an episode decision)
        result = subprocess.run(
            ['grep', '-c', 'OPENED\\|CLOSED', log_file],
            capture_output=True,
            text=True
        )
        return int(result.stdout.strip()) if result.returncode == 0 else 0
    except:
        return 0

def check_bot_running():
    """Check if trading bot is running"""
    try:
        result = subprocess.run(
            ['ps', 'aux'],
            capture_output=True,
            text=True
        )
        return 'main_trading_loop.py' in result.stdout
    except:
        return False

def check_daily_reset():
    """Check if daily trades counter is working"""
    log_file = get_latest_bot_log()
    if not log_file:
        return True  # Assume OK if no log
    
    try:
        # Check last 50 lines for "Daily Trades: 0/3" (indicates reset happened)
        result = subprocess.run(
            ['tail', '-50', log_file],
            capture_output=True,
            text=True
        )
        # If we see "Daily reset" message or "0/3" trades, reset is working
        return '🔄 Daily reset' in result.stdout or 'Daily Trades: 0/3' in result.stdout
    except:
        return True

def get_bot_balance():
    """Extract current balance from log"""
    log_file = get_latest_bot_log()
    if not log_file:
        return None
    
    try:
        result = subprocess.run(
            ['tail', '-100', log_file],
            capture_output=True,
            text=True
        )
        # Find last "Balance: $X.XX USDT"
        for line in reversed(result.stdout.split('\n')):
            if 'Balance: $' in line and 'USDT' in line:
                # Extract balance
                parts = line.split('Balance: $')[1].split(' USDT')[0]
                return float(parts)
    except:
        pass
    return None

def send_alert(message, level="INFO"):
    """Send alert (terminal + notification)"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Color codes
    colors = {
        "INFO": "\033[94m",      # Blue
        "SUCCESS": "\033[92m",   # Green
        "WARNING": "\033[93m",   # Yellow
        "ERROR": "\033[91m",     # Red
        "RESET": "\033[0m"
    }
    
    color = colors.get(level, colors["INFO"])
    reset = colors["RESET"]
    
    # Print to terminal
    print(f"\n{color}{'='*70}{reset}")
    print(f"{color}[{level}] {timestamp}{reset}")
    print(f"{color}{message}{reset}")
    print(f"{color}{'='*70}{reset}\n")
    
    # Try to send macOS notification
    try:
        subprocess.run([
            'osascript', '-e',
            f'display notification "{message}" with title "Trading Bot Alert" subtitle "{level}"'
        ], capture_output=True)
    except:
        pass  # Notification failed, terminal output is enough

def main():
    print(f"\n🔍 Episode Monitor - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    state = load_state()
    
    # Check bot health
    bot_running = check_bot_running()
    episode_count = count_episodes()
    daily_reset_ok = check_daily_reset()
    balance = get_bot_balance()
    current_log = get_latest_bot_log()
    
    print(f"Bot Running:     {'✅ YES' if bot_running else '❌ NO'}")
    print(f"Log File:        {current_log or 'None found'}")
    print(f"Episodes:        {episode_count} collected")
    print(f"Daily Reset:     {'✅ Working' if daily_reset_ok else '⚠️  Check logs'}")
    print(f"Balance:         ${balance:.2f} USDT" if balance else "Balance:         Unknown")
    print(f"Last Check:      {state['last_check'] or 'Never'}")
    
    # Check for alerts
    new_episodes = episode_count - state['last_episode_count']
    
    if new_episodes > 0:
        print(f"\n📈 New episodes since last check: +{new_episodes}")
    
    # Bot stopped alert
    if not bot_running:
        send_alert(
            "⚠️ TRADING BOT IS NOT RUNNING!\n"
            "Check if it crashed. Restart with:\n"
            "cd /Users/openclaw/.openclaw/workspace/AutoHedge\n"
            "source venv/bin/activate\n"
            "nohup python main_trading_loop.py > bot_restart.log 2>&1 &",
            level="ERROR"
        )
    
    # Daily reset broken alert (only warn if bot has been running >24h and no reset seen)
    if bot_running and not daily_reset_ok:
        # Check bot uptime - only alert if running >24 hours
        try:
            ps_result = subprocess.run(
                ['ps', '-p', str(subprocess.check_output(['pgrep', '-f', 'main_trading_loop.py']).decode().strip()), '-o', 'etime='],
                capture_output=True,
                text=True
            )
            uptime = ps_result.stdout.strip()
            # Parse uptime (format: [[DD-]HH:]MM:SS)
            if '-' in uptime:  # Running for days
                send_alert(
                    "⚠️ Daily trade counter may not be resetting!\n"
                    "Check bot_local_final.log for reset messages.",
                    level="WARNING"
                )
        except:
            pass  # Can't determine uptime, skip warning
    
    # Episode milestone alerts
    for threshold in ALERT_THRESHOLDS:
        if episode_count >= threshold and threshold not in state['alerts_sent']:
            # Calculate episodes needed for next milestone
            next_threshold = min([t for t in ALERT_THRESHOLDS if t > threshold], default=None)
            episodes_to_next = next_threshold - episode_count if next_threshold else 0
            
            if threshold == 50:
                message = (
                    f"🎯 MILESTONE: {episode_count} episodes collected!\n\n"
                    f"✅ Ready for Agent Lightning training!\n\n"
                    f"Next steps:\n"
                    f"1. Review episode quality\n"
                    f"2. Run: python phase2_agent_lightning_finetune.py\n"
                    f"3. Let training run overnight (2-4 hours)\n"
                    f"4. Validate results and deploy\n\n"
                    f"Target: {next_threshold} episodes for high confidence"
                    if next_threshold else ""
                )
                level = "SUCCESS"
            elif threshold == 100:
                message = (
                    f"🚀 EXCELLENT: {episode_count} episodes!\n\n"
                    f"High confidence training data accumulated.\n"
                    f"Model will have strong learning signal.\n\n"
                    f"Ready for production Agent Lightning training."
                )
                level = "SUCCESS"
            else:
                message = (
                    f"📊 Progress: {episode_count} episodes collected\n"
                    f"{'Target: 50 episodes for initial training' if threshold < 50 else ''}\n"
                    f"{f'Next milestone: {episodes_to_next} more episodes to reach {next_threshold}' if next_threshold else ''}"
                )
                level = "INFO"
            
            send_alert(message, level=level)
            state['alerts_sent'].append(threshold)
            state['last_alert_time'] = datetime.now().isoformat()
    
    # Balance warning
    if balance and balance < 30:
        send_alert(
            f"⚠️ Low balance alert: ${balance:.2f} USDT\n"
            f"Balance is below $30. Consider:\n"
            f"1. Reviewing strategy performance\n"
            f"2. Adjusting risk parameters\n"
            f"3. Resetting balance if needed",
            level="WARNING"
        )
    
    # Update state
    state['last_check'] = datetime.now().isoformat()
    state['last_episode_count'] = episode_count
    save_state(state)
    
    print(f"\n✓ Monitor check complete\n")
    
    # Return exit code based on readiness
    if episode_count >= 50:
        print("🎯 Status: READY FOR AGENT LIGHTNING TRAINING\n")
        return 0
    else:
        needed = 50 - episode_count
        print(f"⏳ Status: Need {needed} more episodes (current: {episode_count}/50)\n")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nMonitor interrupted by user\n")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Monitor error: {e}\n")
        sys.exit(1)
