#!/bin/bash

# Expense Tracker - Local Run Script (Multi-User)
# This script sets up and runs the Expense Tracker app locally

set -e  # Exit on error

echo "🚀 Setting up Expense Tracker (Multi-User)..."
echo ""

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  WARNING: .env file not found!"
    echo ""
    echo "Please create a .env file with the following variables:"
    echo ""
    echo "GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com"
    echo "GOOGLE_APPLICATION_CREDENTIALS=./service-account.json"
    echo "ENVIRONMENT=development"
    echo "DATABASE_URL=sqlite:///./expenses.db"
    echo "PORT=8000"
    echo ""
    echo "See ENVIRONMENT_VARIABLES.md for detailed instructions."
    echo ""
    read -p "Press Enter to continue anyway (app may fail without credentials)..."
fi

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
pip install --upgrade pip -q
pip install -r requirements.txt -q

# Load .env file if it exists
if [ -f ".env" ]; then
    echo "🔐 Loading environment variables from .env..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# Set database URL for local development (default)
export DATABASE_URL="${DATABASE_URL:-sqlite:///./expenses.db}"
export ENVIRONMENT="${ENVIRONMENT:-development}"
export PORT="${PORT:-8000}"

# Check for Google credentials
if [ -z "$GOOGLE_CLIENT_ID" ]; then
    echo "⚠️  WARNING: GOOGLE_CLIENT_ID not set!"
    echo "Google login will not work without this."
fi

if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ] && [ -z "$GOOGLE_SERVICE_ACCOUNT_JSON" ]; then
    echo "⚠️  WARNING: Google Service Account credentials not set!"
    echo "Google Sheets integration will not work."
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "🎯 Starting Expense Tracker on http://localhost:$PORT"
echo "📱 First-time setup:"
echo "   1. Visit the URL above"
echo "   2. Sign in with Google"
echo "   3. Your account will be created with default categories"
echo ""
echo "📱 Press Ctrl+C to stop the server"
echo ""

# Start the server
uvicorn backend.main:app --host 0.0.0.0 --port $PORT --reload

