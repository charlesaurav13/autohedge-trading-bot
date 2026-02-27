#!/usr/bin/env python3
"""
Phase 1: Pre-train on historical crypto data using Stable-Baselines3 PPO.

This trains a base model on 6 months of BTC/ETH/SOL data to learn
general market patterns before fine-tuning on paper trading logs.

Usage:
    python phase1_historical_training.py --crypto BTC --days 180 --timesteps 100000
    python phase1_historical_training.py --eval-only  # Just evaluate existing model
"""

import gymnasium as gym
import numpy as np
import pandas as pd
import yfinance as yf
from pathlib import Path
from ta.momentum import RSIIndicator
from ta.trend import MACD
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback
from gymnasium import spaces
import argparse
from datetime import datetime


class HistoricalCryptoEnv(gym.Env):
    """
    Historical crypto trading environment for pre-training.
    
    State: [price_change%, RSI, MACD, volume_change%, position, balance%]
    Action: 0=HOLD, 1=LONG, 2=SHORT
    Reward: profit/loss from trades (normalized)
    """
    
    def __init__(self, df, initial_balance=100, position_size=0.4, leverage=10):
        super().__init__()
        
        self.df = df.reset_index(drop=True)
        self.initial_balance = initial_balance
        self.position_size = position_size
        self.leverage = leverage
        
        # Action space: HOLD, LONG, SHORT
        self.action_space = spaces.Discrete(3)
        
        # Observation: [price_change%, RSI, MACD, volume_change%, position, balance%]
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(6,),
            dtype=np.float32
        )
        
        self.reset()
    
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        
        # Start from random point in history
        max_start = len(self.df) - 500  # Leave 500 steps for episode
        self.current_step = np.random.randint(0, max(1, max_start))
        
        self.balance = self.initial_balance
        self.position = None  # None, 'LONG', 'SHORT'
        self.entry_price = 0
        self.position_value = 0
        
        return self._get_observation(), {}
    
    def _get_observation(self):
        """Get normalized market state"""
        row = self.df.iloc[self.current_step]
        prev_row = self.df.iloc[max(0, self.current_step - 1)]
        
        # Calculate changes
        price_change = ((row['close'] - prev_row['close']) / prev_row['close']) * 100 if prev_row['close'] > 0 else 0
        volume_change = ((row['volume'] - prev_row['volume']) / prev_row['volume']) * 100 if prev_row['volume'] > 0 else 0
        
        # Normalize RSI and MACD
        rsi_norm = (row['rsi'] - 50) / 50 if not np.isnan(row['rsi']) else 0  # -1 to 1
        macd_norm = row['macd'] / 100 if not np.isnan(row['macd']) else 0  # Approximate normalization
        
        position_encoding = 0 if self.position is None else (1 if self.position == 'LONG' else -1)
        balance_norm = (self.balance - self.initial_balance) / self.initial_balance
        
        obs = np.array([
            price_change,
            rsi_norm,
            macd_norm,
            volume_change,
            position_encoding,
            balance_norm
        ], dtype=np.float32)
        
        return obs
    
    def step(self, action):
        """Execute action and return next state"""
        current_price = self.df.iloc[self.current_step]['close']
        
        # Execute action (open position)
        if action == 1 and self.position is None:  # LONG
            self.position = 'LONG'
            self.entry_price = current_price
            self.position_value = self.balance * self.position_size * self.leverage
            
        elif action == 2 and self.position is None:  # SHORT
            self.position = 'SHORT'
            self.entry_price = current_price
            self.position_value = self.balance * self.position_size * self.leverage
        
        # Move forward
        self.current_step += 1
        done = self.current_step >= len(self.df) - 1
        
        reward = 0
        if not done:
            next_price = self.df.iloc[self.current_step]['close']
            
            # Calculate PnL if we have position
            if self.position == 'LONG':
                pnl_pct = (next_price - self.entry_price) / self.entry_price
                pnl = self.position_value * pnl_pct
                
                # Close if hit SL or TP
                if pnl_pct <= -0.05 or pnl_pct >= 0.10:
                    reward = pnl / 10  # Normalize reward
                    self.balance += pnl
                    self.position = None
                    self.position_value = 0
                    
            elif self.position == 'SHORT':
                pnl_pct = (self.entry_price - next_price) / self.entry_price
                pnl = self.position_value * pnl_pct
                
                # Close if hit SL or TP
                if pnl_pct <= -0.05 or pnl_pct >= 0.10:
                    reward = pnl / 10  # Normalize reward
                    self.balance += pnl
                    self.position = None
                    self.position_value = 0
            
            # Small penalty for holding without position (encourage action)
            if self.position is None and action == 0:
                reward = -0.001
        
        observation = self._get_observation()
        info = {
            'balance': self.balance,
            'position': self.position,
            'step': self.current_step
        }
        
        return observation, reward, done, False, info


def fetch_historical_data(symbol='BTC-USD', days=180):
    """Fetch and prepare historical data"""
    print(f"📊 Fetching {days} days of {symbol} data...")
    
    df = yf.download(symbol, period=f'{days}d', interval='1h', progress=False)
    
    if df.empty:
        raise ValueError(f"No data returned for {symbol}")
    
    # Add technical indicators (ensure 1D arrays)
    close_series = df['Close'].squeeze()
    df['rsi'] = RSIIndicator(close_series, window=14).rsi()
    macd = MACD(close_series)
    df['macd'] = macd.macd()
    df['volume'] = df['Volume'].squeeze()
    
    # Clean up
    df = df[['Close', 'rsi', 'macd', 'volume']].copy()
    df.columns = ['close', 'rsi', 'macd', 'volume']
    df = df.dropna()
    
    print(f"✅ Prepared {len(df)} data points")
    return df


def train_on_historical_data(
    crypto='BTC',
    days=180,
    total_timesteps=100_000,
    output_model='models/phase1_historical_base'
):
    """
    Train base model on historical data.
    
    Args:
        crypto: Crypto symbol (BTC, ETH, SOL)
        days: Days of historical data
        total_timesteps: Training steps
        output_model: Where to save model
    """
    
    print("="*60)
    print(f"🚀 Phase 1: Pre-training on Historical Data")
    print("="*60)
    print(f"Crypto: {crypto}")
    print(f"History: {days} days")
    print(f"Timesteps: {total_timesteps:,}")
    print("")
    
    # Fetch data
    symbol = f"{crypto}-USD"
    df = fetch_historical_data(symbol, days)
    
    # Create environment
    env = HistoricalCryptoEnv(df, initial_balance=100)
    env = DummyVecEnv([lambda: env])
    
    # Callbacks
    checkpoint_callback = CheckpointCallback(
        save_freq=10_000,
        save_path='./checkpoints/phase1/',
        name_prefix='historical_model'
    )
    
    eval_env = HistoricalCryptoEnv(df, initial_balance=100)
    eval_env = DummyVecEnv([lambda: eval_env])
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path='./checkpoints/phase1/best/',
        log_path='./logs/phase1/',
        eval_freq=5_000,
        deterministic=True,
        render=False
    )
    
    # Initialize PPO model
    print(f"📚 Creating PPO model...")
    model = PPO(
        'MlpPolicy',
        env,
        learning_rate=0.0003,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        verbose=1,
        tensorboard_log='./logs/phase1/tensorboard/'
    )
    
    # Train
    print(f"\n🔥 Training for {total_timesteps:,} timesteps...")
    print(f"⏱️  Estimated time: 6-8 hours on M4 Mac")
    print(f"💾 Checkpoints every 10,000 steps")
    print(f"📊 Monitor: tensorboard --logdir ./logs/phase1/tensorboard/\n")
    
    start_time = datetime.now()
    
    model.learn(
        total_timesteps=total_timesteps,
        callback=[checkpoint_callback, eval_callback],
        progress_bar=True
    )
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds() / 3600
    
    # Save final model
    Path(output_model).parent.mkdir(parents=True, exist_ok=True)
    model.save(output_model)
    
    print(f"\n✅ Phase 1 Complete!")
    print(f"📦 Model saved to: {output_model}.zip")
    print(f"⏱️  Training time: {duration:.2f} hours")
    
    return model


def evaluate_historical_model(model_path='models/phase1_historical_base', crypto='BTC'):
    """Evaluate the trained historical model"""
    
    print("\n📊 Evaluating Phase 1 model...")
    
    # Load model
    model = PPO.load(model_path)
    
    # Load fresh test data (last 30 days)
    symbol = f"{crypto}-USD"
    test_df = fetch_historical_data(symbol, days=30)
    
    # Test environment
    test_env = HistoricalCryptoEnv(test_df, initial_balance=100)
    
    obs, _ = test_env.reset()
    total_reward = 0
    trades = []
    
    for step in range(len(test_df) - 1):
        action, _states = model.predict(obs, deterministic=True)
        obs, reward, done, _, info = test_env.step(action)
        
        total_reward += reward
        
        if reward != 0:  # Trade closed
            trades.append({
                'step': step,
                'balance': info['balance'],
                'reward': reward
            })
        
        if done:
            break
    
    # Calculate metrics
    final_balance = test_env.balance
    roi = ((final_balance - 100) / 100) * 100
    win_rate = len([t for t in trades if t['reward'] > 0]) / len(trades) if trades else 0
    
    print(f"\n{'='*60}")
    print(f"Phase 1 Evaluation Results:")
    print(f"{'='*60}")
    print(f"Starting Balance: $100.00")
    print(f"Final Balance: ${final_balance:.2f}")
    print(f"ROI: {roi:+.2f}%")
    print(f"Total Trades: {len(trades)}")
    print(f"Win Rate: {win_rate:.1%}")
    print(f"Total Reward: {total_reward:.2f}")
    print(f"{'='*60}\n")
    
    return {
        'roi': roi,
        'win_rate': win_rate,
        'trades': len(trades),
        'final_balance': final_balance
    }


def main():
    parser = argparse.ArgumentParser(description='Phase 1: Pre-train on historical data')
    parser.add_argument('--crypto', default='BTC', help='Crypto symbol (BTC, ETH, SOL)')
    parser.add_argument('--days', type=int, default=180, help='Days of historical data')
    parser.add_argument('--timesteps', type=int, default=100_000, help='Training timesteps')
    parser.add_argument('--eval-only', action='store_true', help='Only evaluate existing model')
    
    args = parser.parse_args()
    
    # Create directories
    Path('models').mkdir(exist_ok=True)
    Path('checkpoints/phase1').mkdir(parents=True, exist_ok=True)
    Path('logs/phase1').mkdir(parents=True, exist_ok=True)
    
    if args.eval_only:
        # Just evaluate
        evaluate_historical_model(crypto=args.crypto)
    else:
        # Train
        model = train_on_historical_data(
            crypto=args.crypto,
            days=args.days,
            total_timesteps=args.timesteps
        )
        
        # Evaluate
        evaluate_historical_model(crypto=args.crypto)


if __name__ == '__main__':
    main()
