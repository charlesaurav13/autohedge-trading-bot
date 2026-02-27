#!/usr/bin/env python3
"""
Run Phase 2 training only (skip Phase 1).
Uses existing baseline model or creates one if needed.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from phase2_agent_lightning_finetune import PaperTradingDataExtractor, PaperTradingReplayEnv
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import EvalCallback, StopTrainingOnNoModelImprovement
import numpy as np
import os

def main():
    print("\n" + "=" * 60)
    print("🚀 PHASE 2: Fine-tuning on Real Trading Data")
    print("=" * 60)
    
    # Extract episodes from paper trading logs
    print("\n📊 Step 1: Extracting episodes from logs...")
    extractor = PaperTradingDataExtractor('bot_local_final.log')
    episodes = extractor.extract_episodes()
    
    if len(episodes) < 20:
        print(f"❌ Not enough episodes: {len(episodes)} < 20 minimum")
        print("   Keep trading to accumulate more data!")
        return 1
    
    print(f"✅ Found {len(episodes)} episodes")
    
    # Split data (80/10/10)
    print("\n📊 Step 2: Splitting data (train/val/test)...")
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
    
    print(f"   Train: {len(train_episodes)} episodes")
    print(f"   Val:   {len(val_episodes)} episodes")
    print(f"   Test:  {len(test_episodes)} episodes")
    
    # Create environments
    print("\n📊 Step 3: Creating training environments...")
    train_env = PaperTradingReplayEnv(train_episodes)
    val_env = PaperTradingReplayEnv(val_episodes)
    test_env = PaperTradingReplayEnv(test_episodes)
    
    # Load or create baseline model
    print("\n📦 Step 4: Loading model...")
    baseline_path = 'models/baseline/baseline_model.zip'
    
    if os.path.exists(baseline_path):
        print(f"   Loading from {baseline_path}")
        model = PPO.load(baseline_path, env=train_env)
    else:
        print("   Creating new model (no baseline found)")
        model = PPO('MlpPolicy', train_env, verbose=0)
    
    # Train with early stopping
    print("\n🔥 Step 5: Training...")
    print("   This will take 2-5 minutes...")
    
    os.makedirs('logs/phase2', exist_ok=True)
    os.makedirs('models/phase2_best', exist_ok=True)
    
    stop_callback = StopTrainingOnNoModelImprovement(
        max_no_improvement_evals=5,
        min_evals=3,
        verbose=1
    )
    
    eval_callback = EvalCallback(
        val_env,
        best_model_save_path='models/phase2_best/',
        log_path='logs/phase2/',
        eval_freq=2000,
        callback_after_eval=stop_callback,
        verbose=1
    )
    
    try:
        model.learn(
            total_timesteps=20000,
            callback=eval_callback,
            progress_bar=True
        )
    except KeyboardInterrupt:
        print("\n⚠️  Training interrupted by user")
    
    # Load best model
    print("\n📦 Step 6: Loading best model...")
    best_model_path = 'models/phase2_best/best_model.zip'
    if os.path.exists(best_model_path):
        model = PPO.load(best_model_path)
        print("   ✅ Loaded best model from early stopping")
    else:
        print("   ⚠️  No best model found, using final state")
    
    # Evaluate
    print("\n📊 Step 7: Evaluating model...")
    
    def evaluate_on_env(env, name, n_episodes=10):
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
                
                if reward != 0:
                    trades.append(reward)
                    if reward > 0:
                        wins += 1
            
            total_reward += episode_reward
        
        win_rate = wins / len(trades) if trades else 0
        avg_reward = total_reward / n_episodes
        
        print(f"   {name:6s}: win_rate={win_rate:.1%}, avg_reward={avg_reward:.2f}, trades={len(trades)}")
        return win_rate, avg_reward
    
    train_wr, train_reward = evaluate_on_env(train_env, "Train")
    val_wr, val_reward = evaluate_on_env(val_env, "Val")
    test_wr, test_reward = evaluate_on_env(test_env, "Test")
    
    # Save final model
    print("\n💾 Step 8: Saving final model...")
    os.makedirs('models/phase2_final', exist_ok=True)
    final_path = 'models/phase2_final/phase2_trained.zip'
    model.save(final_path)
    print(f"   ✅ Saved to {final_path}")
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ PHASE 2 TRAINING COMPLETE!")
    print("=" * 60)
    print(f"Train:      {train_wr:.1%} win rate")
    print(f"Validation: {val_wr:.1%} win rate")
    print(f"Test:       {test_wr:.1%} win rate")
    print(f"\nModel saved: {final_path}")
    print("\nNext steps:")
    print("1. Review results above")
    print("2. If validation > 40%, deploy to production")
    print("3. If < 40%, accumulate more trading data and retry")
    print("=" * 60)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
