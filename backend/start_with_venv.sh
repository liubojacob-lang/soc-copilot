#!/bin/bash
# Backend startup script with virtual environment
# Usage: ./start_with_venv.sh

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "Activated virtual environment: Python $(python --version)"
else
    echo "Error: Virtual environment not found. Please run: python3.12 -m venv venv"
    exit 1
fi

# Start backend server
echo "Starting backend server..."
python main.py