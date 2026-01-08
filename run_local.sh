#!/bin/bash

# Expense Tracker - Local Run Script
# This script sets up and runs the Expense Tracker app locally

set -e  # Exit on error

echo "🚀 Setting up Expense Tracker..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Set database URL for local development
export DATABASE_URL="sqlite:///./expenses.db"

# Check if database exists, if not, seed it
if [ ! -f "expenses.db" ]; then
    echo "🌱 Database not found. It will be created on first run."
    echo "💡 Visit http://localhost:8000/api/seed after starting to populate sample data."
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "🎯 Starting Expense Tracker on http://localhost:8000"
echo "📱 Press Ctrl+C to stop the server"
echo ""

# Start the server
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

