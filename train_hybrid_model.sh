#!/bin/bash

# Complete two-phase hybrid training pipeline
# Combines historical data + paper trading logs

set -e  # Exit on error

echo "========================================"
echo "🚀 Hybrid RL Training Pipeline"
echo "========================================"
echo ""
echo "This will:"
echo "1. Pre-train on 6 months historical data (8 hours)"
echo "2. Fine-tune with your paper trading logs (4 hours)"
echo ""

# Activate training environment
if [ ! -d "training_env" ]; then
    echo "❌ Training environment not found!"
    echo "   Run: ./setup_training.sh first"
    exit 1
fi

source training_env/bin/activate

# Check if Phase 1 already done
SKIP_PHASE1=false
if [ -f "models/phase1_historical_base.zip" ]; then
    echo "📦 Phase 1 model already exists: models/phase1_historical_base.zip"
    read -p "Skip Phase 1 training? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        SKIP_PHASE1=true
    fi
fi

# Phase 1: Pre-training on historical data
if [ "$SKIP_PHASE1" = false ]; then
    echo ""
    echo "========================================" echo "📚 Phase 1: Pre-training on Historical Data"
    echo "========================================"
    echo ""
    echo "⏱️  Estimated time: 6-8 hours on M4 Mac"
    echo "💻 Using Metal Performance Shaders (GPU)"
    echo ""

    python phase1_historical_training.py \
        --crypto BTC \
        --days 180 \
        --timesteps 100000

    echo ""
    echo "✅ Phase 1 Complete!"
    echo ""
else
    echo "⏭️  Skipping Phase 1 (using existing model)"
fi

# Evaluate Phase 1
echo ""
echo "📊 Evaluating Phase 1 model..."
python phase1_historical_training.py --eval-only

echo ""

# Phase 2: Fine-tuning with paper trading data
echo ""
echo "========================================"
echo "🎯 Phase 2: Fine-tuning with Paper Trading"
echo "========================================"
echo ""
echo "⏱️  Estimated time: 2-4 hours on M4 Mac"
echo ""

python phase2_agent_lightning_finetune.py \
    --base-model models/phase1_historical_base \
    --log-file bot_local_final.log \
    --steps 10000

echo ""
echo "✅ Phase 2 Complete!"
echo ""

# Final evaluation
echo ""
echo "========================================"
echo "📊 Final Evaluation"
echo "========================================"
python phase2_agent_lightning_finetune.py --eval-only

echo ""
echo "========================================"
echo "🎉 Training Pipeline Complete!"
echo "========================================"
echo ""
echo "📦 Models created:"
echo "   - Phase 1: models/phase1_historical_base.zip"
echo "   - Phase 2: models/phase2_specialized.zip"
echo ""
echo "📊 Training data:"
echo "   - Episodes: training_data/paper_trading_episodes.json"
echo "   - Checkpoints: checkpoints/"
echo "   - Logs: logs/"
echo ""
echo "Next steps:"
echo "1. Review evaluation metrics above"
echo "2. If satisfied, deploy with: ./deploy_trained_model.sh"
echo "3. Monitor performance in paper trading"
echo "4. Retrain weekly with: python phase2_agent_lightning_finetune.py"
echo ""
