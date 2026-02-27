#!/bin/bash
# Quick episode check - run anytime

cd "$(dirname "$0")"
source venv/bin/activate
python3 episode_monitor.py
