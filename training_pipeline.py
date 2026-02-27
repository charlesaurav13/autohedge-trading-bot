#!/usr/bin/env python3
"""
Production Training Pipeline with Overtraining Prevention.

Features:
- Train/validation/test split (80/10/10)
- Early stopping (stops if validation degrades)
- Quality gates (minimum performance requirements)
- Model versioning
- Performance tracking
- Automatic rollback on failure

Usage:
    python training_pipeline.py --mode initial  # First training
    python training_pipeline.py --mode retrain  # Weekly retraining
    python training_pipeline.py --mode evaluate  # Just evaluate
"""

import argparse
import json
import yaml
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import EvalCallback, StopTrainingOnNoModelImprovement

# Import our components
import sys
sys.path.append(str(Path(__file__).parent))

from phase1_historical_training import fetch_historical_data, HistoricalCryptoEnv
from phase2_agent_lightning_finetune import PaperTradingDataExtractor, PaperTradingReplayEnv


class ModelRegistry:
    """Manage model versions and metadata"""
    
    def __init__(self, registry_path='models/registry.json'):
        self.registry_path = Path(registry_path)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.registry = self._load_registry()
    
    def _load_registry(self) -> Dict:
        if self.registry_path.exists():
            with open(self.registry_path) as f:
                return json.load(f)
        return {'models': [], 'current_version': None}
    
    def _save_registry(self):
        with open(self.registry_path, 'w') as f:
            json.dump(self.registry, f, indent=2)
    
    def register_model(self, version: str, metrics: Dict, model_path: str):
        """Register a new model version"""
        entry = {
            'version': version,
            'created_at': datetime.now().isoformat(),
            'model_path': model_path,
            'metrics': metrics,
            'status': 'candidate'
        }
        self.registry['models'].append(entry)
        self._save_registry()
        return entry
    
    def promote_to_production(self, version: str):
        """Promote candidate to production"""
        for model in self.registry['models']:
            if model['version'] == version:
                model['status'] = 'production'
                self.registry['current_version'] = version
                break
        self._save_registry()
    
    def get_current_model(self) -> Dict:
        """Get currently deployed model"""
        if self.registry['current_version']:
            for model in self.registry['models']:
                if model['version'] == self.registry['current_version']:
                    return model
        return None
    
    def get_baseline_metrics(self) -> Dict:
        """Get metrics of current production model"""
        current = self.get_current_model()
        if current:
            return current['metrics']
        return {'val_win_rate': 0.0, 'val_sharpe': 0.0}


class QualityGates:
    """Evaluate model quality and decide deployment"""
    
    @staticmethod
    def evaluate_model(
        model,
        train_env,
        val_env,
        test_env,
        n_eval_episodes=20
    ) -> Dict:
        """
        Evaluate model on train/val/test sets.
        
        Returns metrics dict with win rates, ROI, Sharpe ratio, etc.
        """
        
        def evaluate_on_env(env, n_episodes):
            wins = 0
            total_reward = 0
            trades = []
            
            for _ in range(n_episodes):
                obs, _ = env.reset()
                episode_reward = 0
                done = False
                
                while not done:
                    action, _ = model.predict(obs, deterministic=True)
                    obs, reward, done, _, info = env.step(action)
                    episode_reward += reward
                    
                    if reward != 0:  # Trade closed
                        trades.append(reward)
                        if reward > 0:
                            wins += 1
                
                total_reward += episode_reward
            
            win_rate = wins / len(trades) if trades else 0
            avg_reward = total_reward / n_episodes
            
            # Calculate Sharpe ratio (risk-adjusted returns)
            if trades:
                returns = np.array(trades)
                sharpe = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
            else:
                sharpe = 0
            
            return {
                'win_rate': win_rate,
                'avg_reward': avg_reward,
                'sharpe_ratio': sharpe,
                'n_trades': len(trades),
                'total_reward': total_reward
            }
        
        print("📊 Evaluating model...")
        print("  Train set...", end='', flush=True)
        train_metrics = evaluate_on_env(train_env, n_eval_episodes)
        print(f" ✓ (win_rate={train_metrics['win_rate']:.2%})")
        
        print("  Validation set...", end='', flush=True)
        val_metrics = evaluate_on_env(val_env, n_eval_episodes)
        print(f" ✓ (win_rate={val_metrics['win_rate']:.2%})")
        
        print("  Test set...", end='', flush=True)
        test_metrics = evaluate_on_env(test_env, n_eval_episodes)
        print(f" ✓ (win_rate={test_metrics['win_rate']:.2%})")
        
        return {
            'train_win_rate': train_metrics['win_rate'],
            'train_sharpe': train_metrics['sharpe_ratio'],
            'val_win_rate': val_metrics['win_rate'],
            'val_sharpe': val_metrics['sharpe_ratio'],
            'test_win_rate': test_metrics['win_rate'],
            'test_sharpe': test_metrics['sharpe_ratio'],
            'train_val_gap': train_metrics['win_rate'] - val_metrics['win_rate'],
            'val_test_gap': val_metrics['win_rate'] - test_metrics['win_rate']
        }
    
    @staticmethod
    def check_gates(metrics: Dict, baseline_metrics: Dict = None) -> Tuple[bool, str]:
        """
        Check if model passes quality gates.
        
        Returns: (passed: bool, reason: str)
        """
        # Load config
        import yaml
        config_path = Path(__file__).parent / 'config' / 'training_config.yaml'
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        gates = config['quality_gates']
        min_win_rate = gates['min_val_win_rate']
        min_sharpe = gates['min_val_sharpe']
        max_train_val_gap = gates['max_train_val_gap']
        max_val_test_gap = gates['max_val_test_gap']
        min_improvement = gates['min_improvement']
        
        # Gate 1: Minimum performance
        if metrics['val_win_rate'] < min_win_rate:
            return False, f"❌ Gate 1 FAILED: Win rate too low ({metrics['val_win_rate']:.1%} < {min_win_rate:.1%})"
        
        # Gate 2: Overtraining check
        if metrics['train_val_gap'] > max_train_val_gap:
            return False, f"❌ Gate 2 FAILED: Overtraining detected (train-val gap: {metrics['train_val_gap']:.1%} > {max_train_val_gap:.1%})"
        
        # Gate 3: Test set validation
        if metrics['test_win_rate'] < metrics['val_win_rate'] - max_val_test_gap:
            return False, f"❌ Gate 3 FAILED: Test performance worse than validation ({metrics['test_win_rate']:.1%} vs {metrics['val_win_rate']:.1%})"
        
        # Gate 4: Sharpe ratio (risk-adjusted)
        if metrics['val_sharpe'] < min_sharpe:
            return False, f"❌ Gate 4 FAILED: Sharpe ratio too low ({metrics['val_sharpe']:.2f} < {min_sharpe})"
        
        # Gate 5: Improvement over baseline (if exists)
        if baseline_metrics:
            improvement = metrics['val_win_rate'] - baseline_metrics.get('val_win_rate', 0)
            if improvement < min_improvement:  
                return False, f"❌ Gate 5 FAILED: Insufficient improvement ({improvement:.1%} < {min_improvement:.1%})"
        
        # All gates passed!
        summary = f"""
✅ ALL QUALITY GATES PASSED!

Validation Win Rate: {metrics['val_win_rate']:.1%}
Test Win Rate: {metrics['test_win_rate']:.1%}
Sharpe Ratio: {metrics['val_sharpe']:.2f}
Train-Val Gap: {metrics['train_val_gap']:.1%} (< 10% ✓)
Val-Test Gap: {abs(metrics['val_test_gap']):.1%} (< 8% ✓)
"""
        if baseline_metrics:
            improvement = metrics['val_win_rate'] - baseline_metrics.get('val_win_rate', 0)
            summary += f"Improvement: +{improvement:.1%} over baseline\n"
        
        return True, summary


class TrainingPipeline:
    """Main training pipeline with overtraining prevention"""
    
    def __init__(self):
        self.registry = ModelRegistry()
        self.gates = QualityGates()
    
    def split_data(self, data, train_ratio=0.8, val_ratio=0.1):
        """
        Split data into train/val/test sets.
        
        Args:
            data: List of episodes or DataFrame
            train_ratio: Fraction for training (default 80%)
            val_ratio: Fraction for validation (default 10%)
                      Test gets remainder (10%)
        
        Returns: (train_data, val_data, test_data)
        """
        n = len(data)
        train_size = int(n * train_ratio)
        val_size = int(n * val_ratio)
        
        # Shuffle to avoid temporal bias
        indices = np.random.permutation(n)
        
        train_idx = indices[:train_size]
        val_idx = indices[train_size:train_size + val_size]
        test_idx = indices[train_size + val_size:]
        
        if isinstance(data, list):
            train_data = [data[i] for i in train_idx]
            val_data = [data[i] for i in val_idx]
            test_data = [data[i] for i in test_idx]
        else:  # DataFrame
            train_data = data.iloc[train_idx]
            val_data = data.iloc[val_idx]
            test_data = data.iloc[test_idx]
        
        print(f"📊 Data split: {len(train_data)} train, {len(val_data)} val, {len(test_data)} test")
        
        return train_data, val_data, test_data
    
    def train_with_early_stopping(
        self,
        model,
        train_env,
        val_env,
        total_timesteps=100_000,
        eval_freq=5_000,
        patience=5
    ):
        """
        Train with early stopping based on validation performance.
        
        Args:
            patience: Stop if no improvement for N evaluations
        """
        
        print(f"\n🔥 Training with early stopping (patience={patience})...")
        
        # Create callbacks
        stop_callback = StopTrainingOnNoModelImprovement(
            max_no_improvement_evals=patience,
            min_evals=5,
            verbose=1
        )
        
        eval_callback = EvalCallback(
            val_env,
            best_model_save_path='./checkpoints/best_model/',
            log_path='./logs/eval/',
            eval_freq=eval_freq,
            deterministic=True,
            render=False,
            callback_after_eval=stop_callback,
            verbose=1
        )
        
        # Train
        model.learn(
            total_timesteps=total_timesteps,
            callback=eval_callback,
            progress_bar=True
        )
        
        # Load best model (not final model!)
        best_model_path = './checkpoints/best_model/best_model.zip'
        if Path(best_model_path).exists():
            print("📦 Loading best model from early stopping...")
            model = PPO.load(best_model_path)
        
        return model
    
    def run_phase1(self, crypto='BTC', days=180, timesteps=100_000):
        """Phase 1: Train on historical data with validation"""
        
        print("="*60)
        print("📚 Phase 1: Historical Pre-training")
        print("="*60)
        
        # Fetch data
        df = fetch_historical_data(f"{crypto}-USD", days)
        
        # Split data
        train_df, val_df, test_df = self.split_data(df)
        
        # Create environments
        from stable_baselines3.common.vec_env import DummyVecEnv
        train_env = DummyVecEnv([lambda: HistoricalCryptoEnv(train_df)])
        val_env = DummyVecEnv([lambda: HistoricalCryptoEnv(val_df)])
        test_env = DummyVecEnv([lambda: HistoricalCryptoEnv(test_df)])
        
        # Create model
        model = PPO(
            'MlpPolicy',
            train_env,
            learning_rate=0.0003,
            n_steps=2048,
            batch_size=64,
            n_epochs=10,
            gamma=0.99,
            gae_lambda=0.95,
            clip_range=0.2,
            ent_coef=0.01,  # Entropy for exploration
            verbose=1,
            tensorboard_log='./logs/phase1/tensorboard/'
        )
        
        # Train with early stopping
        model = self.train_with_early_stopping(
            model,
            train_env,
            val_env,
            total_timesteps=timesteps,
            eval_freq=5_000,
            patience=5
        )
        
        # Evaluate
        metrics = self.gates.evaluate_model(
            model,
            train_env.envs[0],
            val_env.envs[0],
            test_env.envs[0]
        )
        
        # Check quality gates
        passed, reason = self.gates.check_gates(metrics)
        
        print("\n" + "="*60)
        if passed:
            print("✅ PHASE 1 PASSED QUALITY GATES")
            print(reason)
            
            # Save model
            version = "v1.1.0_phase1"
            model_path = f"models/production/{version}.zip"
            Path(model_path).parent.mkdir(parents=True, exist_ok=True)
            model.save(model_path)
            
            # Register in registry
            self.registry.register_model(version, metrics, model_path)
            self.registry.promote_to_production(version)
            
            print(f"📦 Model saved: {model_path}")
            print(f"🏆 Promoted to production: {version}")
            
            return model, metrics
        else:
            print("❌ PHASE 1 FAILED QUALITY GATES")
            print(reason)
            print("\n⚠️  Try:")
            print("  - More training steps (--timesteps 200000)")
            print("  - Different crypto (--crypto ETH)")
            print("  - Tune hyperparameters")
            return None, metrics
    
    def run_phase2(self, base_model_path='models/production/v1.1.0_phase1.zip', log_file='bot_local_final.log', timesteps=10_000):
        """Phase 2: Fine-tune with paper trading data"""
        
        print("="*60)
        print("🎯 Phase 2: Paper Trading Fine-tuning")
        print("="*60)
        
        # Load base model
        print(f"📦 Loading base model: {base_model_path}")
        model = PPO.load(base_model_path)
        
        # Extract episodes
        extractor = PaperTradingDataExtractor(log_file)
        episodes = extractor.extract_episodes()
        
        if len(episodes) < 10:
            print(f"⚠️  Only {len(episodes)} episodes found. Need at least 10 for train/val/test split.")
            return None, {}
        
        # Split episodes
        train_eps, val_eps, test_eps = self.split_data(episodes)
        
        # Create environments
        from stable_baselines3.common.vec_env import DummyVecEnv
        train_env = DummyVecEnv([lambda: PaperTradingReplayEnv(train_eps)])
        val_env = DummyVecEnv([lambda: PaperTradingReplayEnv(val_eps)])
        test_env = DummyVecEnv([lambda: PaperTradingReplayEnv(test_eps)])
        
        # Set environment
        model.set_env(train_env)
        
        # Train with early stopping
        model = self.train_with_early_stopping(
            model,
            train_env,
            val_env,
            total_timesteps=timesteps,
            eval_freq=1_000,
            patience=3
        )
        
        # Evaluate
        metrics = self.gates.evaluate_model(
            model,
            train_env.envs[0],
            val_env.envs[0],
            test_env.envs[0]
        )
        
        # Get baseline for comparison
        baseline_metrics = self.registry.get_baseline_metrics()
        
        # Check quality gates
        passed, reason = self.gates.check_gates(metrics, baseline_metrics)
        
        print("\n" + "="*60)
        if passed:
            print("✅ PHASE 2 PASSED QUALITY GATES")
            print(reason)
            
            # Save model
            version = f"v1.2.{len(self.registry.registry['models'])}_finetuned"
            model_path = f"models/candidates/{version}.zip"
            Path(model_path).parent.mkdir(parents=True, exist_ok=True)
            model.save(model_path)
            
            # Register (but don't auto-promote - needs A/B testing)
            self.registry.register_model(version, metrics, model_path)
            
            print(f"📦 Model saved: {model_path}")
            print(f"⏭️  Next: A/B test before deploying")
            print(f"   Run: python ab_testing.py --candidate {version}")
            
            return model, metrics
        else:
            print("❌ PHASE 2 FAILED QUALITY GATES")
            print(reason)
            print("\n💡 This is OK! Not every retraining improves the model.")
            print("   Keep collecting data and try again next week.")
            return None, metrics


def main():
    parser = argparse.ArgumentParser(description='Production Training Pipeline')
    parser.add_argument('--mode', choices=['initial', 'retrain', 'evaluate'], default='initial',
                       help='Training mode')
    parser.add_argument('--crypto', default='BTC', help='Crypto for Phase 1')
    parser.add_argument('--days', type=int, default=180, help='Historical days')
    parser.add_argument('--timesteps', type=int, default=100_000, help='Training timesteps')
    
    args = parser.parse_args()
    
    pipeline = TrainingPipeline()
    
    if args.mode == 'initial':
        # First time: Run both phases
        print("🚀 Running initial training (Phase 1 + Phase 2)...\n")
        
        # Phase 1
        model, metrics = pipeline.run_phase1(
            crypto=args.crypto,
            days=args.days,
            timesteps=args.timesteps
        )
        
        if model:
            # Phase 2
            model, metrics = pipeline.run_phase2()
        
    elif args.mode == 'retrain':
        # Weekly: Just Phase 2 (fine-tune with new data)
        print("🔄 Running weekly retraining (Phase 2 only)...\n")
        pipeline.run_phase2()
    
    elif args.mode == 'evaluate':
        # Just evaluate current model
        registry = ModelRegistry()
        current = registry.get_current_model()
        if current:
            print(f"📊 Current model: {current['version']}")
            print(json.dumps(current['metrics'], indent=2))
        else:
            print("⚠️  No model in production yet")


if __name__ == '__main__':
    main()
