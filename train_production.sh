#!/bin/bash

# Production Training Pipeline - Quick Start
# Uses training_pipeline.py with quality gates and overtraining prevention

set -e

echo "========================================"
echo "🏗️  Production Training Pipeline"
echo "========================================"
echo ""
echo "Features:"
echo "  ✅ Train/Validation/Test split (80/10/10)"
echo "  ✅ Early stopping (prevents overtraining)"
echo "  ✅ Quality gates (deployment criteria)"
echo "  ✅ Model versioning"
echo "  ✅ Performance tracking"
echo ""

# Check if setup already done
if [ ! -d "training_env" ]; then
    echo "❌ Training environment not found!"
    echo "   Run: ./setup_training.sh first"
    exit 1
fi

# Activate environment
source training_env/bin/activate

# Check if config exists
if [ ! -f "config/training_config.yaml" ]; then
    echo "⚠️  Config file not found, using defaults"
fi

# Determine mode
if [ ! -f "models/registry.json" ] || [ ! -s "models/registry.json" ]; then
    MODE="initial"
    echo "📋 Mode: INITIAL (first-time training)"
    echo ""
    echo "This will:"
    echo "  1. Train Phase 1 on historical data (6-8 hours)"
    echo "  2. Fine-tune Phase 2 with paper trading (2-4 hours)"
    echo ""
else
    MODE="retrain"
    echo "📋 Mode: RETRAIN (weekly update)"
    echo ""
    echo "This will:"
    echo "  1. Load existing Phase 1 model"
    echo "  2. Fine-tune with NEW paper trading data"
    echo "  3. Check quality gates"
    echo "  4. Deploy only if better than baseline"
    echo ""
fi

# Confirm
read -p "Continue? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Cancelled"
    exit 0
fi

echo ""
echo "🚀 Starting training pipeline..."
echo ""

# Run training pipeline
if [ "$MODE" == "initial" ]; then
    python training_pipeline.py --mode initial \
        --crypto BTC \
        --days 180 \
        --timesteps 100000
else
    python training_pipeline.py --mode retrain
fi

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Training completed successfully!"
    echo ""
    echo "📊 Review metrics:"
    echo "   python training_pipeline.py --mode evaluate"
    echo ""
    echo "📈 View in TensorBoard:"
    echo "   tensorboard --logdir ./logs/tensorboard/"
    echo ""
    echo "📦 Model registry:"
    echo "   cat models/registry.json | python -m json.tool"
    echo ""
    
    if [ "$MODE" == "initial" ]; then
        echo "🎯 Next steps:"
        echo "   1. Review quality gates results above"
        echo "   2. If passed, model is ready for deployment"
        echo "   3. Run A/B testing: python ab_testing.py"
        echo "   4. Deploy: ./deploy_trained_model.sh"
    else
        echo "🎯 Next steps:"
        echo "   1. Review if new model is better than baseline"
        echo "   2. If yes, run A/B testing before deployment"
        echo "   3. If no, keep current model (it's OK!)"
    fi
    
    echo ""
else
    echo ""
    echo "❌ Training failed!"
    echo "   Check logs for details"
    echo ""
fi
