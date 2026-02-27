#!/bin/bash

# Quick setup script for hybrid RL training

echo "🚀 Setting up Hybrid RL Training Environment..."
echo ""

cd ~/.openclaw/workspace/AutoHedge

# Create virtual environment for training
echo "📦 Creating training environment..."
python3 -m venv training_env
source training_env/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install stable-baselines3[extra]
pip install gymnasium
pip install yfinance ta pandas numpy matplotlib
pip install torch torchvision torchaudio  # For M4 Mac
pip install tensorboard

# Install Agent Lightning
echo "📥 Installing Agent Lightning..."
pip install agentlightning

# Create directories
echo "📁 Creating directories..."
mkdir -p models
mkdir -p checkpoints/phase1
mkdir -p checkpoints/phase2
mkdir -p logs/phase1
mkdir -p logs/phase2
mkdir -p training_data

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Run: source training_env/bin/activate"
echo "2. Start training: python phase1_historical_training.py"
echo ""
