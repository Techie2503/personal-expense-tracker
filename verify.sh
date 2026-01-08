#!/bin/bash

# Expense Tracker - Verification Script
# Run this to verify the repository is complete and ready

echo "🔍 Verifying Expense Tracker Repository..."
echo ""

# Check Python version
echo "✓ Checking Python version..."
python3 --version || { echo "❌ Python 3 not found"; exit 1; }

# Check required files
echo "✓ Checking required files..."
required_files=(
    "backend/main.py"
    "backend/models.py"
    "backend/database.py"
    "backend/seed.py"
    "frontend/index.html"
    "frontend/app.js"
    "frontend/styles.css"
    "frontend/manifest.json"
    "frontend/service-worker.js"
    "requirements.txt"
    "Dockerfile"
    "Procfile"
    "README.md"
    "LICENSE"
    "run_local.sh"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ Missing file: $file"
        exit 1
    fi
done

echo "✓ All required files present"

# Check Python syntax
echo "✓ Checking Python syntax..."
python3 -m py_compile backend/*.py || { echo "❌ Python syntax errors"; exit 1; }

# Check run_local.sh is executable
echo "✓ Checking run_local.sh permissions..."
if [ ! -x "run_local.sh" ]; then
    echo "⚠️  run_local.sh not executable, fixing..."
    chmod +x run_local.sh
fi

# Count lines of code
echo ""
echo "📊 Repository Statistics:"
echo "------------------------"
echo "Python files: $(find backend -name "*.py" | wc -l | tr -d ' ')"
echo "Frontend files: $(find frontend -type f | wc -l | tr -d ' ')"
echo "Total lines (Python): $(find backend -name "*.py" -exec wc -l {} + | tail -1 | awk '{print $1}')"
echo "Total lines (JS): $(cat frontend/app.js | wc -l | tr -d ' ')"
echo "Total lines (CSS): $(cat frontend/styles.css | wc -l | tr -d ' ')"
echo "Total lines (HTML): $(cat frontend/index.html | wc -l | tr -d ' ')"

echo ""
echo "✅ All checks passed!"
echo ""
echo "📝 Next steps:"
echo "1. Run: ./run_local.sh"
echo "2. Open: http://localhost:8000"
echo "3. Seed: curl -X POST http://localhost:8000/api/seed"
echo ""
echo "📱 For deployment to Render, see README.md"
echo ""

