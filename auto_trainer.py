#!/usr/bin/env python3
"""
Automated continuous learning trainer.

Runs as a cron job (weekly) to:
1. Check if enough new data collected
2. Run retraining with quality gates
3. Deploy if passed, reject if failed
4. Send notifications

Setup cron:
    0 2 * * 1 /path/to/auto_trainer.py >> /path/to/auto_trainer.log 2>&1

    (Every Monday at 2 AM)
"""

import os
import sys
import json
import yaml
from pathlib import Path
from datetime import datetime, timedelta
import subprocess
from typing import Dict, Tuple

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from training_pipeline import TrainingPipeline, ModelRegistry
from phase2_agent_lightning_finetune import PaperTradingDataExtractor


class AutoTrainer:
    """Automated continuous learning system"""
    
    def __init__(self, config_path='config/training_config.yaml'):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.pipeline = TrainingPipeline()
        self.registry = ModelRegistry()
        self.log_file = Path('logs/auto_trainer.log')
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _load_config(self) -> Dict:
        with open(self.config_path) as f:
            return yaml.safe_load(f)
    
    def log(self, message: str, level='INFO'):
        """Log message to file and console"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] [{level}] {message}"
        
        print(log_entry)
        
        with open(self.log_file, 'a') as f:
            f.write(log_entry + '\n')
    
    def check_should_retrain(self) -> Tuple[bool, str]:
        """
        Check if retraining should be triggered.
        
        Returns: (should_retrain: bool, reason: str)
        """
        
        config = self.config['auto_retraining']
        
        if not config['enabled']:
            return False, "Auto-retraining disabled in config"
        
        # Check 1: Enough new trades?
        try:
            extractor = PaperTradingDataExtractor(
                self.config['phase2']['log_file']
            )
            episodes = extractor.extract_episodes()
            n_episodes = len(episodes)
            
            min_trades = config['triggers']['min_new_trades']
            if n_episodes < min_trades:
                return False, f"Not enough trades: {n_episodes} < {min_trades}"
        except Exception as e:
            return False, f"Error extracting episodes: {e}"
        
        # Check 2: Enough time passed since last training?
        current_model = self.registry.get_current_model()
        if current_model:
            last_train = datetime.fromisoformat(current_model['created_at'])
            days_since = (datetime.now() - last_train).days
            
            min_days = config['triggers']['min_days_since_last_train']
            if days_since < min_days:
                return False, f"Too recent: {days_since} days < {min_days} days"
        
        # Check 3: Performance degradation?
        if config['triggers']['retrain_if_performance_degrades']:
            # Check if recent performance dropped
            # (This would need live trading metrics)
            pass
        
        # All checks passed
        return True, f"Ready to retrain: {n_episodes} new episodes, {days_since if current_model else 'N/A'} days since last"
    
    def run_retraining(self) -> Tuple[bool, Dict]:
        """
        Run Phase 2 retraining with quality gates.
        
        Returns: (success: bool, metrics: Dict)
        """
        
        try:
            self.log("Starting Phase 2 retraining...")
            
            # Get current production model
            current = self.registry.get_current_model()
            if not current:
                self.log("No base model found, run initial training first", 'ERROR')
                return False, {}
            
            base_model_path = current['model_path']
            
            # Run Phase 2
            model, metrics = self.pipeline.run_phase2(
                base_model_path=base_model_path,
                log_file=self.config['phase2']['log_file'],
                timesteps=self.config['phase2']['training']['total_timesteps']
            )
            
            if model is None:
                self.log("Retraining failed quality gates", 'WARNING')
                return False, metrics
            
            self.log("Retraining passed quality gates! ✅")
            return True, metrics
            
        except Exception as e:
            self.log(f"Retraining failed with error: {e}", 'ERROR')
            import traceback
            self.log(traceback.format_exc(), 'ERROR')
            return False, {}
    
    def send_notification(self, subject: str, message: str):
        """Send notification (email, Telegram, etc.)"""
        
        # For now, just log it
        # In production, integrate with your notification system
        
        self.log(f"NOTIFICATION: {subject}")
        self.log(message)
        
        # Example: Send to Telegram (if configured)
        # telegram_chat_id = os.environ.get('TELEGRAM_CHAT_ID')
        # if telegram_chat_id:
        #     send_telegram_message(telegram_chat_id, f"{subject}\n\n{message}")
    
    def create_training_report(self, metrics: Dict) -> str:
        """Generate human-readable training report"""
        
        report = f"""
{'='*60}
Automated Training Report
{'='*60}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

PERFORMANCE METRICS:
{'─'*60}
Training Win Rate:    {metrics.get('train_win_rate', 0):.1%}
Validation Win Rate:  {metrics.get('val_win_rate', 0):.1%}
Test Win Rate:        {metrics.get('test_win_rate', 0):.1%}

Training Sharpe:      {metrics.get('train_sharpe', 0):.2f}
Validation Sharpe:    {metrics.get('val_sharpe', 0):.2f}
Test Sharpe:          {metrics.get('test_sharpe', 0):.2f}

OVERTRAINING CHECK:
{'─'*60}
Train-Val Gap:        {metrics.get('train_val_gap', 0):.1%}
Val-Test Gap:         {metrics.get('val_test_gap', 0):.1%}

Status: {'✅ NOT OVERTRAINED' if metrics.get('train_val_gap', 0) < 0.10 else '⚠️ POTENTIAL OVERTRAINING'}

COMPARISON TO BASELINE:
{'─'*60}
"""
        
        baseline = self.registry.get_baseline_metrics()
        if baseline:
            improvement = metrics.get('val_win_rate', 0) - baseline.get('val_win_rate', 0)
            report += f"Baseline Win Rate:    {baseline.get('val_win_rate', 0):.1%}\n"
            report += f"New Win Rate:         {metrics.get('val_win_rate', 0):.1%}\n"
            report += f"Improvement:          {improvement:+.1%}\n"
        
        report += f"\n{'='*60}\n"
        
        return report
    
    def run(self):
        """Main execution loop"""
        
        self.log("="*60)
        self.log("🤖 Automated Trainer Started")
        self.log("="*60)
        
        # Check if should retrain
        should_retrain, reason = self.check_should_retrain()
        self.log(f"Retraining check: {reason}")
        
        if not should_retrain:
            self.log("Skipping retraining this cycle")
            return
        
        # Run retraining
        self.log("\n🔥 Triggering retraining...")
        success, metrics = self.run_retraining()
        
        # Generate report
        if metrics:
            report = self.create_training_report(metrics)
            self.log("\n" + report)
        
        # Send notification
        if success:
            self.send_notification(
                subject="✅ Retraining Successful",
                message=f"New model passed quality gates!\n\n{report if metrics else ''}"
            )
        else:
            self.send_notification(
                subject="⚠️ Retraining Failed",
                message=f"Model did not pass quality gates.\n\n{report if metrics else 'No metrics available.'}"
            )
        
        self.log("="*60)
        self.log("🤖 Automated Trainer Completed")
        self.log("="*60)


def setup_cron():
    """Helper to set up cron job"""
    
    script_path = Path(__file__).absolute()
    venv_python = Path(sys.executable).absolute()
    log_path = Path(__file__).parent / 'logs' / 'auto_trainer.log'
    
    cron_command = f"0 2 * * 1 {venv_python} {script_path} >> {log_path} 2>&1"
    
    print("Add this line to your crontab (crontab -e):")
    print()
    print(cron_command)
    print()
    print("This will run every Monday at 2:00 AM")
    print()
    print("To test now, run:")
    print(f"  {venv_python} {script_path}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Automated continuous learning trainer')
    parser.add_argument('--setup-cron', action='store_true', help='Show cron setup instructions')
    parser.add_argument('--dry-run', action='store_true', help='Check conditions without training')
    
    args = parser.parse_args()
    
    if args.setup_cron:
        setup_cron()
        return
    
    trainer = AutoTrainer()
    
    if args.dry_run:
        should_retrain, reason = trainer.check_should_retrain()
        print(f"Should retrain: {should_retrain}")
        print(f"Reason: {reason}")
        return
    
    # Run full training cycle
    trainer.run()


if __name__ == '__main__':
    main()
