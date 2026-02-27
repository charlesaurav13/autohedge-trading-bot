#!/bin/bash

# Weekly retraining script - run this every week to improve the model

set -e

echo "========================================"
echo "🔄 Weekly Model Retraining"
echo "========================================"
echo ""
echo "Date: $(date)"
echo ""

# Activate training environment
if [ ! -d "training_env" ]; then
    echo "❌ Training environment not found!"
    echo "   Run: ./setup_training.sh first"
    exit 1
fi

source training_env/bin/activate

# Check paper trading log
LOG_FILE="bot_local_final.log"
if [ ! -f "$LOG_FILE" ]; then
    echo "❌ Paper trading log not found: $LOG_FILE"
    exit 1
fi

echo "📊 Analyzing paper trading log..."
TRADES=$(grep -c "Successfully opened" "$LOG_FILE" || echo "0")
echo "   Trades found: $TRADES"
echo ""

if [ "$TRADES" -lt "10" ]; then
    echo "⚠️  Only $TRADES trades found"
    echo "   Recommendation: Wait for 20-30 trades before retraining"
    echo ""
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Retraining cancelled"
        exit 0
    fi
fi

# Backup current model
echo "💾 Backing up current model..."
BACKUP_DIR="models/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

if [ -f "models/phase2_specialized.zip" ]; then
    cp models/phase2_specialized.zip "$BACKUP_DIR/"
    echo "   ✅ Backup: $BACKUP_DIR/phase2_specialized.zip"
else
    echo "   ℹ️  No existing model to backup"
fi

echo ""

# Run Phase 2 fine-tuning
echo "🔥 Starting fine-tuning with latest data..."
echo ""

python phase2_agent_lightning_finetune.py \
    --base-model models/phase1_historical_base \
    --log-file "$LOG_FILE" \
    --steps 10000

echo ""
echo "✅ Retraining Complete!"
echo ""

# Evaluate
echo "📊 Evaluating updated model..."
python phase2_agent_lightning_finetune.py --eval-only

echo ""
echo "========================================"
echo "✅ Weekly Retraining Complete!"
echo "========================================"
echo ""
echo "📦 Updated model: models/phase2_specialized.zip"
echo "💾 Backup: $BACKUP_DIR/"
echo "📊 Trades used: $TRADES"
echo ""
echo "Next steps:"
echo "1. Review evaluation metrics above"
echo "2. If improved, deploy: ./deploy_trained_model.sh"
echo "3. If worse, rollback: cp $BACKUP_DIR/phase2_specialized.zip models/"
echo ""
echo "📅 Next retraining: $(date -v+7d '+%Y-%m-%d' 2>/dev/null || date -d '+7 days' '+%Y-%m-%d' 2>/dev/null || echo 'in 7 days')"
echo ""
