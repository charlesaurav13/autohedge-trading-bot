#!/usr/bin/env python3
"""
Trained Model Wrapper - Bridge between RL model and trading bot.

This module provides the interface to use the trained PPO model
alongside the existing AutoHedge LLM-based system.

Usage:
    from trained_model_wrapper import TrainedModelWrapper, IntegrationMode
    
    # Load model
    model = TrainedModelWrapper('models/production/v1.2.0.zip')
    
    # Get prediction
    action = model.predict_action(
        symbol='BTCUSDT',
        current_price=67000,
        rsi=45,
        macd=-50,
        current_volume=1500000000
    )
    
    # action: 0=HOLD, 1=LONG, 2=SHORT
"""

import numpy as np
from enum import Enum
from pathlib import Path
from typing import Dict, Tuple, Optional
import logging

# Try to import stable_baselines3
try:
    from stable_baselines3 import PPO
    SB3_AVAILABLE = True
except ImportError:
    SB3_AVAILABLE = False
    print("⚠️ Warning: stable_baselines3 not installed. Model predictions disabled.")
    print("   Install with: pip install stable-baselines3")


class IntegrationMode(Enum):
    """Integration modes for combining RL model with AutoHedge"""
    HYBRID = "hybrid"          # LLM + RL consensus (recommended)
    REPLACE = "replace"        # RL only (no LLM)
    VETO = "veto"             # LLM decides, RL can block
    ENSEMBLE = "ensemble"      # Multiple models vote


class TrainedModelWrapper:
    """
    Wrapper for trained RL model to integrate with trading bot.
    
    Features:
    - State preparation (converts market data to model input)
    - Action prediction (HOLD/LONG/SHORT)
    - Confidence scoring
    - Performance tracking
    """
    
    def __init__(
        self,
        model_path: str = 'models/production/v1.2.0.zip',
        integration_mode: IntegrationMode = IntegrationMode.HYBRID
    ):
        """
        Initialize model wrapper.
        
        Args:
            model_path: Path to trained PPO model (.zip file)
            integration_mode: How to combine with LLM
        """
        self.model_path = Path(model_path)
        self.integration_mode = integration_mode
        self.logger = logging.getLogger(__name__)
        
        # State tracking (for calculating changes)
        self.prev_price = {}
        self.prev_volume = {}
        
        # Performance tracking
        self.predictions = []
        self.correct_predictions = 0
        self.total_predictions = 0
        
        # Load model
        self.model = self._load_model()
    
    def _load_model(self):
        """Load trained PPO model"""
        if not SB3_AVAILABLE:
            self.logger.error("stable_baselines3 not installed!")
            return None
        
        if not self.model_path.exists():
            self.logger.warning(f"Model not found: {self.model_path}")
            self.logger.warning("RL predictions will be disabled")
            return None
        
        try:
            model = PPO.load(self.model_path)
            self.logger.info(f"✅ Loaded RL model: {self.model_path}")
            return model
        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")
            return None
    
    def is_ready(self) -> bool:
        """Check if model is loaded and ready"""
        return self.model is not None
    
    def prepare_state(
        self,
        symbol: str,
        current_price: float,
        rsi: float,
        macd: float,
        current_volume: float,
        position: Optional[str] = None,
        balance: float = 100.0,
        initial_balance: float = 100.0
    ) -> np.ndarray:
        """
        Convert raw market data into state vector for model.
        
        The model expects 6 features:
        1. Price change % (vs previous check)
        2. RSI normalized to [-1, 1]
        3. MACD normalized
        4. Volume change %
        5. Position encoding (-1/0/+1)
        6. Balance normalized (profit/loss %)
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            current_price: Current price in USDT
            rsi: RSI value (0-100)
            macd: MACD value
            current_volume: Current 24h volume
            position: Current position ('LONG'/'SHORT'/None)
            balance: Current balance
            initial_balance: Starting balance
        
        Returns:
            State vector (6 numbers)
        """
        
        # 1. Calculate price change %
        if symbol in self.prev_price:
            price_change_pct = ((current_price - self.prev_price[symbol]) / self.prev_price[symbol]) * 100
        else:
            price_change_pct = 0.0
        self.prev_price[symbol] = current_price
        
        # 2. Calculate volume change %
        if symbol in self.prev_volume:
            if self.prev_volume[symbol] > 0:
                volume_change_pct = ((current_volume - self.prev_volume[symbol]) / self.prev_volume[symbol]) * 100
            else:
                volume_change_pct = 0.0
        else:
            volume_change_pct = 0.0
        self.prev_volume[symbol] = current_volume
        
        # 3. Normalize RSI to [-1, 1]
        rsi_normalized = (rsi - 50) / 50
        
        # 4. Normalize MACD (approximate)
        macd_normalized = np.clip(macd / 100, -1, 1)
        
        # 5. Encode position
        position_encoding = 0
        if position == 'LONG':
            position_encoding = 1
        elif position == 'SHORT':
            position_encoding = -1
        
        # 6. Normalize balance (profit/loss %)
        balance_normalized = (balance - initial_balance) / initial_balance
        
        # Create state vector
        state = np.array([
            price_change_pct,
            rsi_normalized,
            macd_normalized,
            volume_change_pct,
            position_encoding,
            balance_normalized
        ], dtype=np.float32)
        
        return state
    
    def predict_action(
        self,
        symbol: str,
        current_price: float,
        rsi: float,
        macd: float,
        current_volume: float,
        position: Optional[str] = None,
        balance: float = 100.0,
        initial_balance: float = 100.0,
        deterministic: bool = True
    ) -> int:
        """
        Predict trading action based on market state.
        
        Args:
            symbol: Trading pair
            current_price: Current price
            rsi: RSI indicator (0-100)
            macd: MACD value
            current_volume: 24h volume
            position: Current position ('LONG'/'SHORT'/None)
            balance: Current balance
            initial_balance: Starting balance
            deterministic: If True, use best action (no exploration)
        
        Returns:
            Action integer:
                0 = HOLD (don't trade)
                1 = LONG (buy)
                2 = SHORT (sell)
        """
        
        if not self.is_ready():
            self.logger.warning("Model not loaded, defaulting to HOLD")
            return 0
        
        # Prepare state
        state = self.prepare_state(
            symbol, current_price, rsi, macd, current_volume,
            position, balance, initial_balance
        )
        
        # Get prediction
        try:
            action, _states = self.model.predict(state, deterministic=deterministic)
            action = int(action)
            
            # Track prediction
            self.total_predictions += 1
            self.predictions.append({
                'symbol': symbol,
                'action': action,
                'state': state.tolist(),
                'timestamp': np.datetime64('now')
            })
            
            return action
            
        except Exception as e:
            self.logger.error(f"Prediction error: {e}")
            return 0  # Default to HOLD on error
    
    def get_action_name(self, action: int) -> str:
        """Convert action integer to name"""
        names = {0: 'HOLD', 1: 'LONG', 2: 'SHORT'}
        return names.get(action, 'UNKNOWN')
    
    def combine_with_autohedge(
        self,
        rl_action: int,
        autohedge_result: Dict
    ) -> Tuple[bool, str, str]:
        """
        Combine RL model prediction with AutoHedge analysis.
        
        Args:
            rl_action: RL model's action (0/1/2)
            autohedge_result: AutoHedge output dict with:
                - should_trade: bool
                - direction: 'LONG'/'SHORT'
                - confidence: float (0-1)
                - reasoning: str
        
        Returns:
            (should_trade: bool, direction: str, reasoning: str)
        """
        
        rl_direction = self.get_action_name(rl_action)
        ah_direction = autohedge_result.get('direction', 'HOLD')
        ah_confidence = autohedge_result.get('confidence', 0.5)
        ah_should_trade = autohedge_result.get('should_trade', False)
        
        if self.integration_mode == IntegrationMode.REPLACE:
            # RL only
            should_trade = (rl_action != 0)
            direction = rl_direction
            reasoning = f"RL Model decision: {direction}"
            
        elif self.integration_mode == IntegrationMode.VETO:
            # AutoHedge decides, RL can veto
            if not ah_should_trade:
                return False, 'HOLD', "AutoHedge says no trade"
            
            if rl_action == 0:
                return False, 'HOLD', f"RL Model vetoed AutoHedge's {ah_direction} signal"
            
            # RL approves
            if rl_direction == ah_direction:
                return True, ah_direction, f"AutoHedge + RL consensus: {ah_direction}"
            else:
                return False, 'HOLD', f"RL disagrees: AutoHedge={ah_direction}, RL={rl_direction}"
        
        elif self.integration_mode == IntegrationMode.HYBRID:
            # Both must agree (consensus)
            if not ah_should_trade:
                return False, 'HOLD', "AutoHedge says no trade"
            
            if rl_action == 0:
                return False, 'HOLD', "RL Model says HOLD"
            
            # Both want to trade - check direction
            if rl_direction == ah_direction:
                return True, ah_direction, f"✅ Consensus: Both systems agree on {ah_direction}"
            
            # Conflict - use confidence to break tie
            if ah_confidence > 0.80:
                return True, ah_direction, f"⚠️ Conflict resolved: Following AutoHedge (confidence: {ah_confidence:.1%})"
            else:
                return False, 'HOLD', f"⚠️ Conflict: AutoHedge={ah_direction} ({ah_confidence:.1%}), RL={rl_direction}. No trade on low confidence."
        
        elif self.integration_mode == IntegrationMode.ENSEMBLE:
            # Multiple signals vote (placeholder for future)
            # Could add more signals here (e.g., simple technical strategy)
            votes = {'LONG': 0, 'SHORT': 0, 'HOLD': 0}
            
            # AutoHedge vote (weighted by confidence)
            if ah_should_trade:
                votes[ah_direction] += ah_confidence
            else:
                votes['HOLD'] += 1
            
            # RL vote
            votes[rl_direction] += 1
            
            # Winner
            winner = max(votes, key=votes.get)
            
            if winner != 'HOLD' and votes[winner] >= 1.5:  # Need strong support
                return True, winner, f"Ensemble vote: {winner} ({votes[winner]:.1f} votes)"
            else:
                return False, 'HOLD', f"No clear consensus (votes: {votes})"
        
        else:
            self.logger.error(f"Unknown integration mode: {self.integration_mode}")
            return False, 'HOLD', "Unknown integration mode"
    
    def get_performance_stats(self) -> Dict:
        """Get model performance statistics"""
        if self.total_predictions == 0:
            return {'status': 'no_predictions_yet'}
        
        return {
            'total_predictions': self.total_predictions,
            'correct_predictions': self.correct_predictions,
            'accuracy': self.correct_predictions / self.total_predictions if self.total_predictions > 0 else 0,
            'model_path': str(self.model_path),
            'integration_mode': self.integration_mode.value,
            'is_ready': self.is_ready()
        }
    
    def update_performance(self, correct: bool):
        """Update performance tracking after trade outcome"""
        if correct:
            self.correct_predictions += 1


# Example usage
if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize wrapper
    wrapper = TrainedModelWrapper('models/production/v1.2.0.zip')
    
    if wrapper.is_ready():
        print("✅ Model loaded successfully!")
        
        # Example prediction
        action = wrapper.predict_action(
            symbol='BTCUSDT',
            current_price=67000,
            rsi=45,
            macd=-50,
            current_volume=1500000000,
            position=None,
            balance=100,
            initial_balance=100
        )
        
        print(f"\nPrediction: {wrapper.get_action_name(action)}")
        print(f"Action code: {action}")
        
        # Example integration with AutoHedge
        autohedge_result = {
            'should_trade': True,
            'direction': 'LONG',
            'confidence': 0.75,
            'reasoning': "Bullish technical indicators + positive news"
        }
        
        should_trade, direction, reasoning = wrapper.combine_with_autohedge(
            action, autohedge_result
        )
        
        print(f"\nIntegration result:")
        print(f"  Should trade: {should_trade}")
        print(f"  Direction: {direction}")
        print(f"  Reasoning: {reasoning}")
        
        # Stats
        print(f"\nPerformance stats:")
        print(wrapper.get_performance_stats())
        
    else:
        print("❌ Model not loaded. Check path and dependencies.")
