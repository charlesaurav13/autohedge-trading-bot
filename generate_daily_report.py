#!/usr/bin/env python3
"""
Daily Performance Report Generator

Analyzes trading bot and learning system performance.
Generates comprehensive daily summary.

Usage:
    python generate_daily_report.py                    # Console output
    python generate_daily_report.py --save            # Save to file
    python generate_daily_report.py --telegram        # Send to Telegram
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import argparse


class DailyReportGenerator:
    """Generate comprehensive daily performance reports"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.bot_log = self.base_dir / 'bot_local_final.log'
        self.learner_log = self.base_dir / 'learner.log'
        self.state_file = self.base_dir / 'models' / 'learner_state.json'
        self.report_dir = self.base_dir / 'reports'
        self.report_dir.mkdir(exist_ok=True)
        
    def get_bot_pid(self):
        """Get trading bot PID if running"""
        try:
            import subprocess
            result = subprocess.run(
                ['pgrep', '-f', 'main_trading_loop.py'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0]
        except:
            pass
        return None
    
    def get_learner_pid(self):
        """Get learner PID if running"""
        try:
            import subprocess
            result = subprocess.run(
                ['pgrep', '-f', 'continuous_learner.py'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0]
        except:
            pass
        return None
    
    def get_process_uptime(self, pid):
        """Get process uptime"""
        if not pid:
            return None
        try:
            import subprocess
            result = subprocess.run(
                ['ps', '-p', pid, '-o', 'etime='],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        return None
    
    def parse_bot_logs(self, hours=24):
        """Parse bot logs for last N hours"""
        if not self.bot_log.exists():
            return {}
        
        cutoff = datetime.now() - timedelta(hours=hours)
        
        stats = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0.0,
            'balance': 100.0,
            'positions_opened': 0,
            'positions_closed': 0,
            'signals_generated': 0,
            'trades_by_symbol': defaultdict(int),
            'pnl_by_symbol': defaultdict(float),
            'last_balance': None,
            'last_pnl_pct': None
        }
        
        try:
            with open(self.bot_log, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    # Extract timestamp
                    ts_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                    if not ts_match:
                        continue
                    
                    try:
                        ts = datetime.strptime(ts_match.group(1), '%Y-%m-%d %H:%M:%S')
                        if ts < cutoff:
                            continue
                    except:
                        continue
                    
                    # Parse different log entries
                    if 'OPENED' in line:
                        stats['positions_opened'] += 1
                        symbol_match = re.search(r'(BTC|ETH|SOL)', line)
                        if symbol_match:
                            stats['trades_by_symbol'][symbol_match.group(1)] += 1
                    
                    if 'CLOSED' in line:
                        stats['positions_closed'] += 1
                        pnl_match = re.search(r'PnL: ([-+]?\$[\d.]+)', line)
                        if pnl_match:
                            pnl_str = pnl_match.group(1).replace('$', '').replace(',', '')
                            pnl = float(pnl_str)
                            stats['total_pnl'] += pnl
                            if pnl > 0:
                                stats['winning_trades'] += 1
                            elif pnl < 0:
                                stats['losing_trades'] += 1
                            
                            symbol_match = re.search(r'(BTC|ETH|SOL)', line)
                            if symbol_match:
                                stats['pnl_by_symbol'][symbol_match.group(1)] += pnl
                    
                    if 'Balance:' in line:
                        bal_match = re.search(r'Balance: \$([\d.]+)', line)
                        if bal_match:
                            stats['last_balance'] = float(bal_match.group(1))
                    
                    if 'PnL: ' in line and '%' in line:
                        pnl_match = re.search(r'PnL: ([+-]?[\d.]+)%', line)
                        if pnl_match:
                            stats['last_pnl_pct'] = float(pnl_match.group(1))
                    
                    if 'COMBINED SIGNAL:' in line:
                        stats['signals_generated'] += 1
            
            stats['total_trades'] = stats['winning_trades'] + stats['losing_trades']
            if stats['last_balance']:
                stats['balance'] = stats['last_balance']
            
        except Exception as e:
            print(f"Error parsing bot logs: {e}")
        
        return stats
    
    def parse_learner_state(self):
        """Parse learner state"""
        if not self.state_file.exists():
            return {}
        
        try:
            with open(self.state_file) as f:
                state = json.load(f)
                return {
                    'episodes_processed': state.get('last_episode_count', 0),
                    'total_trainings': state.get('total_trainings', 0),
                    'last_training': state.get('last_training_time', None)
                }
        except:
            return {}
    
    def get_model_info(self):
        """Get latest model info"""
        model_path = self.base_dir / 'models' / 'continuous' / 'latest.zip'
        if not model_path.exists():
            return {}
        
        stat = model_path.stat()
        return {
            'size_kb': stat.st_size / 1024,
            'last_updated': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def parse_recent_training(self):
        """Parse most recent training from learner log"""
        if not self.learner_log.exists():
            return {}
        
        try:
            with open(self.learner_log, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # Look for last training session
            val_wr = None
            train_wr = None
            
            for line in reversed(lines):
                if 'Val   : win_rate=' in line:
                    match = re.search(r'win_rate=([\d.]+)%', line)
                    if match and val_wr is None:
                        val_wr = float(match.group(1))
                
                if 'Train : win_rate=' in line:
                    match = re.search(r'win_rate=([\d.]+)%', line)
                    if match and train_wr is None:
                        train_wr = float(match.group(1))
                
                if val_wr and train_wr:
                    break
            
            return {
                'train_win_rate': train_wr,
                'val_win_rate': val_wr
            }
        except:
            return {}
    
    def generate_report(self, hours=24):
        """Generate complete report"""
        print(f"\n{'='*70}")
        print(f"  📊 DAILY PERFORMANCE REPORT")
        print(f"  {datetime.now().strftime('%A, %B %d, %Y %I:%M %p')}")
        print(f"{'='*70}\n")
        
        # System Status
        print(f"{'─'*70}")
        print(f"  🖥️  SYSTEM STATUS")
        print(f"{'─'*70}")
        
        bot_pid = self.get_bot_pid()
        learner_pid = self.get_learner_pid()
        
        if bot_pid:
            uptime = self.get_process_uptime(bot_pid)
            print(f"  ✅ Trading Bot:       RUNNING (PID {bot_pid}, uptime: {uptime})")
        else:
            print(f"  ❌ Trading Bot:       STOPPED")
        
        if learner_pid:
            uptime = self.get_process_uptime(learner_pid)
            print(f"  ✅ Continuous Learner: RUNNING (PID {learner_pid}, uptime: {uptime})")
        else:
            print(f"  ❌ Continuous Learner: STOPPED")
        
        print()
        
        # Trading Performance
        print(f"{'─'*70}")
        print(f"  💰 TRADING PERFORMANCE (Last {hours}h)")
        print(f"{'─'*70}")
        
        bot_stats = self.parse_bot_logs(hours)
        
        win_rate = 0
        if bot_stats['total_trades'] > 0:
            win_rate = (bot_stats['winning_trades'] / bot_stats['total_trades']) * 100
        
        print(f"  Balance:              ${bot_stats['balance']:.2f} USDT")
        if bot_stats['last_pnl_pct'] is not None:
            pnl_emoji = "📈" if bot_stats['last_pnl_pct'] >= 0 else "📉"
            print(f"  Total PnL:            {pnl_emoji} {bot_stats['last_pnl_pct']:+.2f}%")
        print(f"  Trades Executed:      {bot_stats['total_trades']}")
        print(f"    ├─ Winning:         {bot_stats['winning_trades']} ✅")
        print(f"    └─ Losing:          {bot_stats['losing_trades']} ❌")
        print(f"  Win Rate:             {win_rate:.1f}%")
        print(f"  Positions Opened:     {bot_stats['positions_opened']}")
        print(f"  Positions Closed:     {bot_stats['positions_closed']}")
        print(f"  Signals Generated:    {bot_stats['signals_generated']}")
        
        if bot_stats['trades_by_symbol']:
            print(f"\n  By Symbol:")
            for symbol in sorted(bot_stats['trades_by_symbol'].keys()):
                count = bot_stats['trades_by_symbol'][symbol]
                pnl = bot_stats['pnl_by_symbol'].get(symbol, 0)
                pnl_str = f"{pnl:+.2f}" if pnl != 0 else "0.00"
                print(f"    {symbol}:  {count} trades, ${pnl_str} PnL")
        
        print()
        
        # Learning Progress
        print(f"{'─'*70}")
        print(f"  🧠 LEARNING PROGRESS")
        print(f"{'─'*70}")
        
        learner_state = self.parse_learner_state()
        model_info = self.get_model_info()
        training_stats = self.parse_recent_training()
        
        if learner_state:
            episodes = learner_state.get('episodes_processed', 0)
            trainings = learner_state.get('total_trainings', 0)
            print(f"  Episodes Processed:   {episodes}")
            print(f"  Training Cycles:      {trainings}")
            
            if learner_state.get('last_training'):
                last_train = learner_state['last_training']
                try:
                    dt = datetime.fromisoformat(last_train)
                    time_ago = datetime.now() - dt
                    hours_ago = time_ago.total_seconds() / 3600
                    if hours_ago < 1:
                        ago_str = f"{int(time_ago.total_seconds() / 60)} minutes ago"
                    elif hours_ago < 24:
                        ago_str = f"{int(hours_ago)} hours ago"
                    else:
                        ago_str = f"{int(hours_ago / 24)} days ago"
                    print(f"  Last Training:        {ago_str}")
                except:
                    print(f"  Last Training:        {last_train}")
            
            # Next training estimate
            next_training_at = episodes + (20 - (episodes % 20))
            episodes_needed = next_training_at - episodes
            print(f"  Next Training:        In {episodes_needed} episodes (at {next_training_at} total)")
        
        if model_info:
            print(f"  Latest Model:         {model_info['size_kb']:.1f} KB")
            print(f"  Model Updated:        {model_info['last_updated']}")
        
        if training_stats:
            if training_stats.get('train_win_rate'):
                print(f"\n  Latest Training Results:")
                print(f"    Train Win Rate:     {training_stats['train_win_rate']:.1f}%")
                if training_stats.get('val_win_rate'):
                    print(f"    Val Win Rate:       {training_stats['val_win_rate']:.1f}%")
        
        print()
        
        # Summary & Recommendations
        print(f"{'─'*70}")
        print(f"  📋 SUMMARY & RECOMMENDATIONS")
        print(f"{'─'*70}")
        
        issues = []
        recommendations = []
        
        # Check system health
        if not bot_pid:
            issues.append("❌ Trading bot is not running")
            recommendations.append("Start bot: nohup python main_trading_loop.py > bot_local_final.log 2>&1 &")
        
        if not learner_pid:
            issues.append("❌ Continuous learner is not running")
            recommendations.append("Start learner: nohup python continuous_learner.py > learner.log 2>&1 &")
        
        # Check performance
        if bot_stats['total_trades'] == 0 and hours >= 24:
            issues.append("⚠️  No trades executed in last 24 hours")
            recommendations.append("Check bot logs for errors or market conditions")
        
        if bot_stats['total_trades'] > 0:
            if win_rate < 40:
                issues.append(f"⚠️  Low win rate: {win_rate:.1f}% (target: 50%+)")
                recommendations.append("Wait for more training cycles to improve model")
            elif win_rate >= 60:
                issues.append(f"✅ Excellent win rate: {win_rate:.1f}%!")
        
        # Check learning progress
        if learner_state:
            episodes = learner_state.get('episodes_processed', 0)
            if episodes < 50:
                recommendations.append(f"Accumulate more data: {episodes}/50 episodes (need {50-episodes} more)")
            elif episodes >= 50 and episodes < 100:
                if training_stats.get('val_win_rate', 0) >= 60:
                    recommendations.append("✨ Consider deploying RL model (hybrid mode) - good validation!")
            elif episodes >= 100:
                recommendations.append("🚀 Ready for production deployment - excellent data volume!")
        
        if issues:
            print(f"\n  Issues:")
            for issue in issues:
                print(f"    {issue}")
        
        if recommendations:
            print(f"\n  Recommendations:")
            for rec in recommendations:
                print(f"    • {rec}")
        
        if not issues:
            print(f"  ✅ System operating normally")
        
        print(f"\n{'='*70}\n")
        
        return {
            'bot_stats': bot_stats,
            'learner_state': learner_state,
            'model_info': model_info,
            'training_stats': training_stats,
            'system_status': {
                'bot_running': bool(bot_pid),
                'learner_running': bool(learner_pid)
            }
        }
    
    def save_report(self, data, hours=24):
        """Save report to file"""
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        filename = self.report_dir / f'daily_report_{timestamp}.txt'
        
        # Redirect stdout to file
        original_stdout = sys.stdout
        with open(filename, 'w') as f:
            sys.stdout = f
            self.generate_report(hours)
        sys.stdout = original_stdout
        
        print(f"✅ Report saved to: {filename}")
        return filename


def main():
    parser = argparse.ArgumentParser(description='Generate daily performance report')
    parser.add_argument('--hours', type=int, default=24, help='Hours of data to analyze')
    parser.add_argument('--save', action='store_true', help='Save report to file')
    parser.add_argument('--telegram', action='store_true', help='Send to Telegram (requires setup)')
    
    args = parser.parse_args()
    
    generator = DailyReportGenerator()
    
    if args.save:
        filename = generator.save_report(data=None, hours=args.hours)
        print(f"\n📄 Report saved to: {filename}")
    else:
        data = generator.generate_report(hours=args.hours)
    
    if args.telegram:
        print("\n⚠️  Telegram notifications not yet configured")
        print("   Run: python setup_telegram_notifications.py")


if __name__ == '__main__':
    main()
