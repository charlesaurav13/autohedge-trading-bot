#!/bin/bash

# Deploy the trained model to replace DeepSeek in live bot
# This is a placeholder - actual deployment depends on model format

set -e

echo "========================================"
echo "🚀 Deploying Trained Model"
echo "========================================"
echo ""

MODEL_PATH="models/phase2_specialized.zip"

if [ ! -f "$MODEL_PATH" ]; then
    echo "❌ Model not found: $MODEL_PATH"
    echo "   Run train_hybrid_model.sh first!"
    exit 1
fi

echo "📦 Model found: $MODEL_PATH"
echo ""

# Show model info
echo "📋 Model Information:"
echo "   Created: $(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" "$MODEL_PATH" 2>/dev/null || stat -c "%y" "$MODEL_PATH" 2>/dev/null || echo "unknown")"
echo "   Size: $(du -h "$MODEL_PATH" | cut -f1)"
echo ""

# Confirm deployment
echo "⚠️  This will replace the current DeepSeek model with the trained version."
echo ""
read -p "Continue with deployment? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Deployment cancelled"
    exit 1
fi

echo ""
echo "🔄 Deployment process:"
echo ""

# Step 1: Stop trading bot
echo "1️⃣  Stopping trading bot..."
if pgrep -f "main_trading_loop.py" > /dev/null; then
    pkill -f "main_trading_loop.py"
    echo "   ✅ Bot stopped"
    sleep 2
else
    echo "   ℹ️  Bot not running"
fi

# Step 2: Backup current model (if exists)
echo ""
echo "2️⃣  Backing up current model..."
OLLAMA_MODEL_DIR="$HOME/.ollama/models"
if [ -d "$OLLAMA_MODEL_DIR" ]; then
    BACKUP_DIR="$OLLAMA_MODEL_DIR/backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # Copy existing DeepSeek model files (if any)
    if [ -d "$OLLAMA_MODEL_DIR/blobs" ]; then
        cp -r "$OLLAMA_MODEL_DIR/blobs" "$BACKUP_DIR/" 2>/dev/null || true
        echo "   ✅ Backup created: $BACKUP_DIR"
    else
        echo "   ℹ️  No existing model to backup"
    fi
else
    echo "   ⚠️  Ollama model directory not found"
fi

# Step 3: Export trained model
echo ""
echo "3️⃣  Exporting trained model..."
echo "   ⚠️  NOTE: This requires converting Stable-Baselines3 PPO to Ollama format"
echo "   📝 Current implementation uses trained model for ACTION SELECTION"
echo "   🤖 DeepSeek still generates trading thesis, trained model picks trades"
echo ""

# Create model wrapper script
cat > trained_model_wrapper.py << 'EOF'
"""
Wrapper to use trained PPO model for trade selection.
DeepSeek generates analysis, trained model makes final decision.
"""
from stable_baselines3 import PPO
import numpy as np

class TrainedModelWrapper:
    def __init__(self, model_path='models/phase2_specialized.zip'):
        self.model = PPO.load(model_path)
    
    def predict_action(self, rsi, macd, price_change=0, volume_change=0):
        """
        Predict trading action based on market state.
        Returns: 0=HOLD, 1=LONG, 2=SHORT
        """
        # Normalize inputs
        rsi_norm = (rsi - 50) / 50
        macd_norm = macd / 100
        
        obs = np.array([
            price_change,
            rsi_norm,
            macd_norm,
            volume_change,
            0,  # position
            0   # balance
        ], dtype=np.float32)
        
        action, _ = self.model.predict(obs, deterministic=True)
        return int(action)

# Test the model
if __name__ == '__main__':
    wrapper = TrainedModelWrapper()
    
    # Test case: BTC with RSI=40 (oversold), MACD=-10 (bearish)
    action = wrapper.predict_action(rsi=40, macd=-10)
    actions = ['HOLD', 'LONG', 'SHORT']
    print(f"Test prediction: {actions[action]}")
EOF

echo "   ✅ Created trained_model_wrapper.py"

# Step 4: Update main_trading_loop.py to use trained model
echo ""
echo "4️⃣  Updating trading loop..."
echo "   📝 You need to manually integrate trained_model_wrapper.py"
echo "   💡 Suggested integration:"
echo ""
echo "   from trained_model_wrapper import TrainedModelWrapper"
echo "   trained_model = TrainedModelWrapper()"
echo ""
echo "   # Before opening trade, get trained model's opinion:"
echo "   model_action = trained_model.predict_action(rsi, macd)"
echo "   if model_action == 0:  # HOLD"
echo "       print('Trained model says HOLD')"
echo "       continue"
echo ""

# Step 5: Document deployment
echo ""
echo "5️⃣  Creating deployment record..."
DEPLOY_LOG="deployment_log.txt"
{
    echo "========================================"
    echo "Deployment Record"
    echo "========================================"
    echo "Date: $(date)"
    echo "Model: $MODEL_PATH"
    echo "Backup: $BACKUP_DIR"
    echo "Status: Pending manual integration"
    echo ""
    echo "Integration steps:"
    echo "1. Add trained_model_wrapper.py to main_trading_loop.py"
    echo "2. Use trained model for final trade decision"
    echo "3. Restart bot with: ./start_bot.sh"
    echo "4. Monitor first trades closely"
    echo ""
} > "$DEPLOY_LOG"

echo "   ✅ Deployment log: $DEPLOY_LOG"

echo ""
echo "========================================"
echo "✅ Deployment Prepared!"
echo "========================================"
echo ""
echo "📋 Next Steps (Manual):"
echo ""
echo "1. Review trained_model_wrapper.py"
echo "2. Integrate into main_trading_loop.py:"
echo "   - Import TrainedModelWrapper"
echo "   - Use for trade selection"
echo "   - DeepSeek still generates analysis"
echo ""
echo "3. Test integration:"
echo "   python trained_model_wrapper.py"
echo ""
echo "4. Restart bot:"
echo "   ./start_bot.sh"
echo ""
echo "5. Monitor first 5-10 trades:"
echo "   tail -f bot_local_final.log"
echo ""
echo "6. Compare to baseline:"
echo "   - Old: 33% win rate (1/3)"
echo "   - Target: 60-70% win rate"
echo ""
echo "⚠️  Rollback if needed:"
echo "   Restore from: $BACKUP_DIR"
echo ""
echo "📊 Weekly retraining:"
echo "   python phase2_agent_lightning_finetune.py"
echo ""
