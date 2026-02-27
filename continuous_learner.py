#!/usr/bin/env python3
"""
Continuous Learning Daemon - Trains model on live trading data while bot runs.

This runs alongside the trading bot:
1. Monitors paper trading logs
2. Retrains when enough new episodes collected
3. Updates model automatically
4. Never stops the trading bot

Usage:
    nohup python continuous_learner.py > learner.log 2>&1 &
"""

import os
import sys
import time
import signal
from pathlib import Path
from datetime import datetime
import json

sys.path.append(str(Path(__file__).parent))

from phase2_agent_lightning_finetune import PaperTradingDataExtractor, PaperTradingReplayEnv
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import EvalCallback, StopTrainingOnNoModelImprovement
import numpy as np


class ContinuousLearner:
    """Background trainer that learns from live trading data"""
    
    def __init__(self):
        self.running = True
        self.state_file = Path('models/learner_state.json')
        self.log_file = 'bot_local_final.log'
        self.model_path = 'models/continuous/latest.zip'
        self.best_model_path = 'models/continuous/best.zip'
        
        # Training config
        self.min_new_episodes = 20  # Retrain when 20+ new episodes
        self.check_interval = 3600  # Check every hour (3600 sec)
        self.training_timesteps = 20000
        
        # Create directories
        Path('models/continuous').mkdir(parents=True, exist_ok=True)
        Path('logs/continuous').mkdir(parents=True, exist_ok=True)
        
        # Load state (last episode count)
        self.last_episode_count = self._load_state()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        print(f"✅ Continuous Learner initialized")
        print(f"   Checking every {self.check_interval}s for new data")
        print(f"   Retraining when {self.min_new_episodes}+ new episodes collected")
    
    def _load_state(self) -> int:
        """Load last training state"""
        if self.state_file.exists():
            with open(self.state_file) as f:
                state = json.load(f)
                return state.get('last_episode_count', 0)
        return 0
    
    def _save_state(self, episode_count: int):
        """Save training state"""
        state = {
            'last_episode_count': episode_count,
            'last_training_time': datetime.now().isoformat(),
            'total_trainings': self._get_training_count() + 1
        }
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def _get_training_count(self) -> int:
        """Get number of training runs"""
        if self.state_file.exists():
            with open(self.state_file) as f:
                return json.load(f).get('total_trainings', 0)
        return 0
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print(f"\n⚠️  Received signal {signum}, shutting down...")
        self.running = False
    
    def check_for_new_data(self) -> tuple:
        """Check if enough new episodes for retraining"""
        try:
            extractor = PaperTradingDataExtractor(self.log_file)
            episodes = extractor.extract_episodes()
            current_count = len(episodes)
            new_episodes = current_count - self.last_episode_count
            
            return current_count, new_episodes, episodes
        except Exception as e:
            print(f"❌ Error checking data: {e}")
            return self.last_episode_count, 0, []
    
    def train_model(self, episodes):
        """Train model on accumulated episodes"""
        print(f"\n{'='*60}")
        print(f"🔥 RETRAINING MODEL")
        print(f"{'='*60}")
        print(f"Total episodes: {len(episodes)}")
        print(f"Training started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Split data
        n = len(episodes)
        indices = np.random.permutation(n)
        train_size = int(n * 0.8)
        val_size = int(n * 0.1)
        
        train_idx = indices[:train_size]
        val_idx = indices[train_size:train_size + val_size]
        test_idx = indices[train_size + val_size:]
        
        train_episodes = [episodes[i] for i in train_idx]
        val_episodes = [episodes[i] for i in val_idx]
        test_episodes = [episodes[i] for i in test_idx]
        
        print(f"Split: {len(train_episodes)} train / {len(val_episodes)} val / {len(test_episodes)} test")
        
        # Create environments
        train_env = PaperTradingReplayEnv(train_episodes)
        val_env = PaperTradingReplayEnv(val_episodes)
        
        # Load existing model or create new
        if Path(self.model_path).exists():
            print(f"Loading existing model from {self.model_path}")
            model = PPO.load(self.model_path, env=train_env)
        elif Path(self.best_model_path).exists():
            print(f"Loading best model from {self.best_model_path}")
            model = PPO.load(self.best_model_path, env=train_env)
        elif Path('models/baseline/baseline_model.zip').exists():
            print("Loading baseline model")
            model = PPO.load('models/baseline/baseline_model.zip', env=train_env)
        else:
            print("Creating new model")
            model = PPO('MlpPolicy', train_env, verbose=0)
        
        # Setup callbacks
        stop_callback = StopTrainingOnNoModelImprovement(
            max_no_improvement_evals=5,
            min_evals=3,
            verbose=1
        )
        
        eval_callback = EvalCallback(
            val_env,
            best_model_save_path='models/continuous/',
            log_path='logs/continuous/',
            eval_freq=2000,
            callback_after_eval=stop_callback,
            verbose=1
        )
        
        # Train
        print(f"Training {self.training_timesteps} steps...")
        model.learn(
            total_timesteps=self.training_timesteps,
            callback=eval_callback,
            progress_bar=True
        )
        
        # Save updated model
        model.save(self.model_path)
        print(f"✅ Model saved to {self.model_path}")
        
        # Evaluate
        print("\n📊 Evaluation:")
        def eval_env(env, name):
            wins = 0
            total = 0
            for _ in range(10):
                obs, _ = env.reset()
                done = False
                while not done:
                    action, _ = model.predict(obs, deterministic=True)
                    obs, reward, done, _, _ = env.step(action)
                    if reward != 0:
                        total += 1
                        if reward > 0:
                            wins += 1
            wr = wins / total if total > 0 else 0
            print(f"   {name:6s}: {wr:.1%} win rate ({wins}/{total})")
            return wr
        
        train_wr = eval_env(train_env, "Train")
        val_wr = eval_env(val_env, "Val")
        
        print(f"\n{'='*60}")
        print(f"✅ Training complete!")
        print(f"   Validation: {val_wr:.1%} win rate")
        print(f"{'='*60}\n")
        
        return val_wr
    
    def run(self):
        """Main loop - check periodically and train when needed"""
        print(f"\n🚀 Starting continuous learning loop...")
        print(f"   Press Ctrl+C to stop\n")
        
        iteration = 0
        
        while self.running:
            iteration += 1
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"[{timestamp}] Check #{iteration}")
            
            # Check for new data
            current_count, new_count, episodes = self.check_for_new_data()
            
            print(f"   Episodes: {current_count} total, {new_count} new")
            
            if new_count >= self.min_new_episodes:
                print(f"   ✅ Threshold met ({new_count} >= {self.min_new_episodes})")
                print(f"   🔥 Starting training...")
                
                try:
                    val_wr = self.train_model(episodes)
                    
                    # Update state
                    self._save_state(current_count)
                    self.last_episode_count = current_count
                    
                    print(f"   ✅ Training successful! (val: {val_wr:.1%})")
                    
                except Exception as e:
                    print(f"   ❌ Training failed: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                needed = self.min_new_episodes - new_count
                print(f"   ⏳ Need {needed} more episodes")
            
            # Sleep until next check
            if self.running:
                print(f"   💤 Sleeping {self.check_interval}s...\n")
                time.sleep(self.check_interval)
        
        print("\n✅ Continuous learner stopped")


def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║  CONTINUOUS LEARNING DAEMON                               ║
║  Automatically trains on live trading data               ║
╚══════════════════════════════════════════════════════════╝
""")
    
    learner = ContinuousLearner()
    learner.run()


if __name__ == '__main__':
    main()
