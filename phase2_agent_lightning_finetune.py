#!/usr/bin/env python3
"""
Phase 2: Fine-tune with paper trading logs using Agent Lightning concepts.

Takes the pre-trained model from Phase 1 and specializes it using
your actual paper trading decisions and outcomes.

Usage:
    python phase2_agent_lightning_finetune.py --base-model models/phase1_historical_base --steps 10000
"""

import json
import re
import argparse
from pathlib import Path
from typing import List, Dict
import numpy as np
import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from datetime import datetime


class PaperTradingDataExtractor:
    """Extract trading episodes from paper trading logs"""
    
    def __init__(self, log_file='bot_local_final.log'):
        self.log_file = log_file
        self.episodes = []
    
    def extract_episodes(self) -> List[Dict]:
        """Parse logs and extract trading episodes"""
        
        episodes = []
        current_episode = None
        
        print(f"📊 Parsing {self.log_file}...")
        
        try:
            with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    # New trading cycle
                    if 'ITERATION' in line or 'Starting analysis' in line:
                        if current_episode and current_episode.get('action') is not None:
                            episodes.append(current_episode)
                        
                        current_episode = {
                            'timestamp': self._extract_timestamp(line),
                            'state': {},
                            'action': 0,  # Default HOLD
                            'reward': 0.0,
                            'symbol': None
                        }
                    
                    if current_episode is None:
                        continue
                    
                    # Market data
                    if 'Price:' in line or 'price:' in line:
                        price = self._extract_number(line)
                        if price > 0:
                            current_episode['state']['price'] = price
                    
                    if 'RSI' in line:
                        rsi = self._extract_number(line)
                        if 0 <= rsi <= 100:
                            current_episode['state']['rsi'] = rsi
                    
                    if 'MACD' in line:
                        macd = self._extract_number(line)
                        current_episode['state']['macd'] = macd
                    
                    # Symbol detection
                    if 'BTC' in line and current_episode['symbol'] is None:
                        current_episode['symbol'] = 'BTCUSDT'
                    elif 'ETH' in line and current_episode['symbol'] is None:
                        current_episode['symbol'] = 'ETHUSDT'
                    elif 'SOL' in line and current_episode['symbol'] is None:
                        current_episode['symbol'] = 'SOLUSDT'
                    
                    # Trading decision
                    if 'BEST OPPORTUNITY' in line or 'Successfully opened' in line:
                        if 'LONG' in line:
                            current_episode['action'] = 1
                        elif 'SHORT' in line:
                            current_episode['action'] = 2
                        else:
                            current_episode['action'] = 0
                    
                    # Reward (profit/loss)
                    if 'PnL' in line or 'profit' in line.lower() or 'loss' in line.lower():
                        pnl = self._extract_number(line)
                        if abs(pnl) > 0.01:  # Ignore tiny values
                            current_episode['reward'] = pnl
        
        except FileNotFoundError:
            print(f"⚠️  Log file not found: {self.log_file}")
            return []
        
        # Add last episode
        if current_episode and current_episode.get('action') is not None:
            episodes.append(current_episode)
        
        # Filter valid episodes (must have state and action)
        valid_episodes = [
            ep for ep in episodes 
            if ep.get('state') and len(ep['state']) > 0 and ep.get('action') is not None
        ]
        
        self.episodes = valid_episodes
        print(f"✅ Extracted {len(valid_episodes)} valid episodes")
        
        return valid_episodes
    
    def _extract_timestamp(self, line):
        match = re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', line)
        return match.group(0) if match else None
    
    def _extract_number(self, line):
        # Look for numbers with optional +/- and $
        match = re.search(r'[-+]?\$?[\d,]+\.?\d*', line)
        if match:
            try:
                return float(match.group(0).replace('$', '').replace(',', '').replace('+', ''))
            except:
                pass
        return 0.0


class PaperTradingReplayEnv(gym.Env):
    """Replay paper trading episodes for fine-tuning"""
    
    def __init__(self, episodes):
        super().__init__()
        
        if not episodes:
            raise ValueError("No episodes provided for training!")
        
        self.episodes = episodes
        self.current_ep_idx = 0
        
        self.action_space = spaces.Discrete(3)
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(6,), dtype=np.float32
        )
    
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.current_ep_idx = np.random.randint(0, len(self.episodes))
        return self._get_obs(), {}
    
    def _get_obs(self):
        """Convert episode to observation"""
        ep = self.episodes[self.current_ep_idx]
        state = ep.get('state', {})
        
        # Extract state features
        price = state.get('price', 0)
        rsi = state.get('rsi', 50)
        macd = state.get('macd', 0)
        
        # Normalize to observation format
        obs = np.array([
            0,  # price_change (not available in current logs)
            (rsi - 50) / 50,  # Normalize RSI to [-1, 1]
            macd / 100,  # Normalize MACD
            0,  # volume change (not available)
            0,  # position (not tracked in extractor)
            0   # balance (not tracked in extractor)
        ], dtype=np.float32)
        
        return obs
    
    def step(self, action):
        """
        Compare agent's action with actual paper trading decision.
        Reward positive if matched successful trade, penalty if different.
        """
        ep = self.episodes[self.current_ep_idx]
        
        actual_action = ep.get('action', 0)
        actual_reward = ep.get('reward', 0) / 50.0  # Normalize to [-1, 1]
        actual_reward = max(-1.0, min(1.0, actual_reward))
        
        # Imitation learning: reward matching expert behavior
        if action == actual_action:
            # If we matched, give the actual reward from that trade
            reward = actual_reward if actual_reward != 0 else 0.1
        else:
            # If we diverged from expert, small penalty
            reward = -0.1
        
        # Episode ends after one step (we're replaying individual decisions)
        done = True
        obs = self._get_obs()
        info = {'episode': self.current_ep_idx, 'actual_reward': actual_reward}
        
        return obs, reward, done, False, info


def finetune_with_paper_trading(
    base_model_path='models/phase1_historical_base',
    paper_trading_log='bot_local_final.log',
    output_model='models/phase2_specialized',
    finetune_steps=10_000
):
    """
    Fine-tune pre-trained model with paper trading data.
    
    Args:
        base_model_path: Path to Phase 1 model
        paper_trading_log: Your bot's log file
        output_model: Where to save fine-tuned model
        finetune_steps: Number of fine-tuning steps
    """
    
    print("="*60)
    print("🚀 Phase 2: Fine-tuning with Paper Trading Data")
    print("="*60)
    
    # Load Phase 1 model
    print(f"\n📦 Loading Phase 1 model from {base_model_path}...")
    try:
        base_model = PPO.load(base_model_path)
        print("✅ Model loaded successfully")
    except FileNotFoundError:
        print("❌ Phase 1 model not found!")
        print("   Run phase1_historical_training.py first.")
        return None
    
    # Extract paper trading data
    print(f"\n📊 Extracting paper trading episodes...")
    extractor = PaperTradingDataExtractor(paper_trading_log)
    episodes = extractor.extract_episodes()
    
    if len(episodes) == 0:
        print("⚠️  No episodes found! Need at least 1 trade to fine-tune.")
        print("   Continue paper trading and try again later.")
        return None
    
    # Save episodes for reference
    episodes_file = 'training_data/paper_trading_episodes.json'
    Path('training_data').mkdir(exist_ok=True)
    with open(episodes_file, 'w') as f:
        json.dump(episodes, f, indent=2)
    print(f"💾 Saved episodes to {episodes_file}")
    
    # Display episode summary
    print(f"\n📋 Episode Summary:")
    action_names = ['HOLD', 'LONG', 'SHORT']
    for i, ep in enumerate(episodes[:5]):  # Show first 5
        action = ep.get('action', 0)
        reward = ep.get('reward', 0)
        symbol = ep.get('symbol', 'UNKNOWN')
        print(f"  #{i+1}: {symbol} {action_names[action]} → ${reward:+.2f}")
    if len(episodes) > 5:
        print(f"  ... and {len(episodes) - 5} more episodes")
    
    # Create replay environment
    print(f"\n🔄 Creating fine-tuning environment...")
    try:
        replay_env = PaperTradingReplayEnv(episodes)
        replay_env = DummyVecEnv([lambda: replay_env])
    except ValueError as e:
        print(f"❌ {e}")
        return None
    
    # Set environment for continued training
    base_model.set_env(replay_env)
    
    # Fine-tune
    print(f"\n🔥 Fine-tuning for {finetune_steps:,} steps...")
    print(f"⏱️  Estimated time: 2-4 hours on M4 Mac")
    print(f"📊 Learning from {len(episodes)} real trading episodes\n")
    
    start_time = datetime.now()
    
    base_model.learn(
        total_timesteps=finetune_steps,
        progress_bar=True,
        reset_num_timesteps=False  # Continue from Phase 1
    )
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds() / 3600
    
    # Save fine-tuned model
    Path(output_model).parent.mkdir(parents=True, exist_ok=True)
    base_model.save(output_model)
    
    print(f"\n✅ Phase 2 Complete!")
    print(f"📦 Specialized model saved to: {output_model}.zip")
    print(f"⏱️  Fine-tuning time: {duration:.2f} hours")
    
    return base_model


def evaluate_finetuned_model(
    model_path='models/phase2_specialized',
    episodes_file='training_data/paper_trading_episodes.json'
):
    """Evaluate the fine-tuned model on paper trading episodes"""
    
    print("\n📊 Evaluating Phase 2 model...")
    
    # Load model
    try:
        model = PPO.load(model_path)
    except FileNotFoundError:
        print(f"❌ Model not found: {model_path}")
        return None
    
    # Load episodes
    try:
        with open(episodes_file, 'r') as f:
            episodes = json.load(f)
    except FileNotFoundError:
        print(f"❌ Episodes file not found: {episodes_file}")
        return None
    
    if not episodes:
        print("⚠️  No episodes to evaluate")
        return None
    
    # Test on episodes
    env = PaperTradingReplayEnv(episodes)
    
    correct_predictions = 0
    total_episodes = min(len(episodes), 100)  # Test on up to 100 episodes
    
    action_names = ['HOLD', 'LONG', 'SHORT']
    
    for i in range(total_episodes):
        obs, _ = env.reset()
        action, _ = model.predict(obs, deterministic=True)
        
        ep = episodes[env.current_ep_idx]
        actual_action = ep.get('action', 0)
        
        if action == actual_action:
            correct_predictions += 1
    
    accuracy = (correct_predictions / total_episodes) * 100
    
    print(f"\n{'='*60}")
    print(f"Phase 2 Evaluation Results:")
    print(f"{'='*60}")
    print(f"Episodes Tested: {total_episodes}")
    print(f"Correct Predictions: {correct_predictions}")
    print(f"Accuracy: {accuracy:.1f}%")
    print(f"{'='*60}\n")
    
    return {
        'accuracy': accuracy,
        'correct': correct_predictions,
        'total': total_episodes
    }


def main():
    parser = argparse.ArgumentParser(description='Phase 2: Fine-tune with paper trading data')
    parser.add_argument('--base-model', default='models/phase1_historical_base', 
                       help='Phase 1 model path')
    parser.add_argument('--log-file', default='bot_local_final.log', 
                       help='Paper trading log')
    parser.add_argument('--steps', type=int, default=10_000, 
                       help='Fine-tuning steps')
    parser.add_argument('--eval-only', action='store_true',
                       help='Only evaluate existing model')
    
    args = parser.parse_args()
    
    # Create directories
    Path('models').mkdir(exist_ok=True)
    Path('training_data').mkdir(exist_ok=True)
    
    if args.eval_only:
        # Just evaluate
        evaluate_finetuned_model()
    else:
        # Fine-tune
        model = finetune_with_paper_trading(
            base_model_path=args.base_model,
            paper_trading_log=args.log_file,
            finetune_steps=args.steps
        )
        
        if model:
            # Evaluate
            evaluate_finetuned_model()


if __name__ == '__main__':
    main()
