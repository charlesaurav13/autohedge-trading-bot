# 🏗️ Production Training System - Complete Guide

**Advanced continuous learning pipeline with overtraining prevention and quality gates.**

---

## 🎯 What's Different From Basic Scripts?

### ❌ Basic Scripts (Manual):
- Train on ALL data → overtraining risk
- No validation → can't detect if model memorizing
- Manual deployment → human error
- No versioning → can't rollback
- Static model → never improves

### ✅ Production System (Automatic):
- **Train/Val/Test split** → prevents overtraining
- **Early stopping** → stops when validation degrades
- **Quality gates** → only deploys if better
- **Model versioning** → easy rollback
- **Continuous learning** → improves weekly
- **A/B testing** → safe deployment
- **Monitoring** → detects degradation

---

## 📁 File Structure

```
AutoHedge/
├── 🏗️ PRODUCTION SYSTEM (NEW!)
│   ├── training_pipeline.py          # Main orchestrator with quality gates
│   ├── auto_trainer.py                # Automated weekly retraining (cron)
│   ├── train_production.sh            # Quick start script
│   └── config/
│       └── training_config.yaml       # All hyperparameters (tune here!)
│
├── 📊 BASIC SCRIPTS (For reference)
│   ├── phase1_historical_training.py
│   ├── phase2_agent_lightning_finetune.py
│   ├── train_hybrid_model.sh
│   └── setup_training.sh
│
├── 📚 DOCUMENTATION
│   ├── PIPELINE_ARCHITECTURE.md       # System design
│   ├── HYBRID_TRAINING_PLAN.md        # Training strategy
│   └── QUICKSTART_TRAINING.md         # Basic guide
│
└── 📦 OUTPUTS
    ├── models/
    │   ├── production/                # Deployed models
    │   ├── candidates/                # Models being tested
    │   ├── backups/                   # Rollback copies
    │   └── registry.json              # Model metadata
    │
    ├── logs/
    │   ├── tensorboard/               # Training metrics
    │   ├── eval/                      # Evaluation results
    │   └── auto_trainer.log           # Cron job logs
    │
    └── checkpoints/
        ├── best_model/                # Best model from early stopping
        └── phase1/, phase2/           # Training checkpoints
```

---

## 🚀 Quick Start (Production System)

### 1. First Time Setup (5 minutes)

```bash
# Install dependencies
./setup_training.sh

# Activate environment
source training_env/bin/activate
```

### 2. Initial Training (8-12 hours)

```bash
# Run production pipeline
./train_production.sh
```

**What happens:**
- ✅ Loads config from `config/training_config.yaml`
- ✅ Splits data: 80% train, 10% val, 10% test
- ✅ Phase 1: Trains on historical data with early stopping
- ✅ Evaluates on train/val/test sets
- ✅ Checks quality gates (win rate, Sharpe, overtraining)
- ✅ If passed → saves to `models/production/`
- ✅ If failed → explains why and suggests fixes
- ✅ Phase 2: Fine-tunes with paper trading data
- ✅ Registers model with version number
- ✅ Outputs deployment recommendation

### 3. Weekly Retraining (Automated)

**Option A: Manual**
```bash
source training_env/bin/activate
python training_pipeline.py --mode retrain
```

**Option B: Automated (Cron)**
```bash
# Set up weekly retraining (every Monday at 2 AM)
python auto_trainer.py --setup-cron

# Test without training
python auto_trainer.py --dry-run
```

---

## 🛡️ Overtraining Prevention

### How It Works:

```python
# 1. SPLIT DATA
train_data = episodes[0:80%]      # Used for training
val_data = episodes[80%:90%]       # Used to check if overtrained
test_data = episodes[90%:100%]     # NEVER SEEN until final eval

# 2. TRAIN WITH EARLY STOPPING
while training:
    train_on(train_data)
    
    if val_performance_degrades:
        stop_training()  # Model is memorizing train set!
        load_best_model()  # Revert to best checkpoint
        break

# 3. QUALITY GATES
metrics = evaluate_on(train, val, test)

if metrics['train_win_rate'] - metrics['val_win_rate'] > 10%:
    reject_model("Overtrained! Memorizing training data")

if metrics['val_win_rate'] - metrics['test_win_rate'] > 8%:
    reject_model("Validation set may be lucky, test set is reality")
```

### Red Flags:

| Metric | Good ✅ | Overtraining ⚠️ |
|--------|---------|-----------------|
| **Train Win Rate** | 65% | 80% |
| **Val Win Rate** | 62% | 55% |
| **Test Win Rate** | 60% | 50% |
| **Train-Val Gap** | 3% | 25% ← RED FLAG! |
| **Val-Test Gap** | 2% | 5% |

**Diagnosis:** Model memorized training data, performs poorly on new data!

---

## 📊 Quality Gates Explained

Before deploying, model must pass ALL gates:

### Gate 1: Minimum Performance
```
❌ FAIL: val_win_rate = 52% (< 55% minimum)
✅ PASS: val_win_rate = 62% (> 55% minimum)
```

### Gate 2: No Overtraining
```
❌ FAIL: train_win_rate=70%, val_win_rate=55% (gap=15% > 10%)
✅ PASS: train_win_rate=65%, val_win_rate=62% (gap=3% < 10%)
```

### Gate 3: Test Set Validation
```
❌ FAIL: val_win_rate=65%, test_win_rate=52% (gap=13%)
✅ PASS: val_win_rate=62%, test_win_rate=60% (gap=2%)
```

### Gate 4: Risk-Adjusted Returns
```
❌ FAIL: Sharpe ratio = 0.6 (< 0.8 minimum)
✅ PASS: Sharpe ratio = 1.2 (> 0.8 minimum)
```

### Gate 5: Improvement Over Baseline
```
❌ FAIL: new=57%, old=56% (improvement=1% < 2% minimum)
✅ PASS: new=62%, old=56% (improvement=6% > 2% minimum)
```

---

## ⚙️ Configuration (No Code Changes!)

Edit `config/training_config.yaml` to tune everything:

### Common Adjustments:

**Training too slow?**
```yaml
phase1:
  training:
    total_timesteps: 50_000  # Reduce from 100K
```

**Model too conservative?**
```yaml
quality_gates:
  min_val_win_rate: 0.52  # Lower from 0.55
```

**Want more exploration?**
```yaml
phase1:
  hyperparameters:
    ent_coef: 0.02  # Increase from 0.01
```

**Overtraining too easily?**
```yaml
phase1:
  training:
    patience: 10  # Increase from 5
```

---

## 📈 Monitoring & Metrics

### Real-time Training:

```bash
# Terminal 1: Start training
./train_production.sh

# Terminal 2: Watch TensorBoard
tensorboard --logdir ./logs/tensorboard/
# Open: http://localhost:6006
```

### Check Model Registry:

```bash
# View all models
cat models/registry.json | python -m json.tool

# Current production model
python training_pipeline.py --mode evaluate
```

### Automated Reports:

```bash
# Check what auto-trainer would do
python auto_trainer.py --dry-run

# View cron logs
tail -f logs/auto_trainer.log
```

---

## 🔄 Continuous Learning Workflow

```
┌─────────────────────────────────────────┐
│  WEEK 1: Initial Training               │
└─────────────────────────────────────────┘
1. Run: ./train_production.sh
2. Result: Phase 1 model (55-60% win rate)
3. Status: v1.1.0 in production

┌─────────────────────────────────────────┐
│  WEEK 2: First Retraining               │
└─────────────────────────────────────────┘
1. Paper trading collects 20-30 new trades
2. Auto-trainer triggers (Monday 2 AM)
3. Phase 2 fine-tunes with new data
4. Quality gates: PASSED (60% win rate)
5. A/B test: New model wins
6. Deploy: v1.2.0 in production

┌─────────────────────────────────────────┐
│  WEEK 3: Continued Improvement          │
└─────────────────────────────────────────┘
1. More trading data (50+ total trades)
2. Auto-trainer triggers
3. Quality gates: PASSED (63% win rate)
4. Deploy: v1.2.1 in production

┌─────────────────────────────────────────┐
│  WEEK 4: Plateau Detection              │
└─────────────────────────────────────────┘
1. Even more data (80+ trades)
2. Auto-trainer triggers
3. Quality gates: FAILED (62% < 63% + 2%)
4. Keep current model (v1.2.1)
5. Wait for more data

┌─────────────────────────────────────────┐
│  MONTH 2: Breakthrough                  │
└─────────────────────────────────────────┘
1. Enough data (150+ trades)
2. Market conditions changed
3. Retraining captures new patterns
4. Quality gates: PASSED (68% win rate!)
5. Deploy: v1.3.0 in production
```

---

## 🚨 Troubleshooting

### "Training failed quality gates"

**Symptoms:**
```
❌ Gate 2 FAILED: Overtraining detected (gap: 15%)
```

**Solutions:**
1. More data needed (wait for more trades)
2. Lower learning rate: `learning_rate: 0.0001`
3. Add regularization: `ent_coef: 0.02`
4. Early stopping patience: `patience: 10`

### "Model worse than baseline"

**Symptoms:**
```
❌ Gate 5 FAILED: Only 1% improvement (need >2%)
```

**Solutions:**
1. This is NORMAL! Not every retraining improves
2. Keep current model
3. Collect more data
4. Try again next week

### "Early stopping triggered too early"

**Symptoms:**
```
Training stopped at 20K steps (expected 100K)
```

**Solutions:**
1. Good! This prevented overtraining
2. If win rate too low, try:
   - More patience: `patience: 10`
   - More eval freq: `eval_freq: 10000`
   - Check if data quality is good

---

## 🎯 Best Practices

### ✅ DO:
- Use production system for real deployment
- Trust quality gates (they prevent bad deployments)
- Retrain weekly with new data
- Monitor performance over time
- Keep backups before deploying

### ❌ DON'T:
- Train on all data without validation split
- Deploy models that fail quality gates
- Skip A/B testing (unless very confident)
- Overtrain (more timesteps ≠ better model)
- Ignore warnings about data quality

---

## 📊 Expected Performance Timeline

| Week | Trades | Win Rate | Deployment |
|------|--------|----------|------------|
| 1 | 0 (historical only) | 55-60% | Phase 1 only |
| 2 | 20-30 | 58-62% | Phase 2 first run |
| 4 | 50-80 | 60-65% | Improving |
| 8 | 100-150 | 63-68% | Solid |
| 12 | 200+ | 65-72% | Excellent |

---

## 🔧 Advanced: Custom Training

### Train on different crypto:

```bash
python training_pipeline.py --mode initial --crypto ETH --days 180 --timesteps 100000
```

### Adjust hyperparameters:

Edit `config/training_config.yaml`:
```yaml
phase1:
  hyperparameters:
    learning_rate: 0.0005  # Higher LR
    batch_size: 128        # Larger batches
    n_epochs: 15           # More epochs per batch
```

### Debug mode:

```python
# In training_pipeline.py, add:
verbose=2  # More detailed logging
```

---

## 📚 Further Reading

- **Architecture:** `PIPELINE_ARCHITECTURE.md` - System design
- **Training Strategy:** `HYBRID_TRAINING_PLAN.md` - Two-phase approach
- **Basic Guide:** `QUICKSTART_TRAINING.md` - Simple manual training
- **Agent Lightning:** `AGENT_LIGHTNING_PLAN.md` - Microsoft framework details

---

## 🎉 Summary

**Production System = Safe + Automatic + Continuously Improving**

1. ✅ Run `./train_production.sh` once
2. ✅ Set up `auto_trainer.py` for weekly updates
3. ✅ Model improves automatically from experience
4. ✅ Quality gates prevent bad deployments
5. ✅ No overtraining, no manual intervention

**Result:** Trading bot that gets smarter every week! 🚀

---

Questions? Check the docs or review `training_pipeline.py` - it's heavily commented!
