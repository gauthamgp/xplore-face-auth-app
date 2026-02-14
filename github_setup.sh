#!/bin/bash

# Quick setup script for GitHub + Render deployment
# Usage: bash github_setup.sh

set -e

echo "🚀 Xplore Face Auth - GitHub & Render Setup"
echo "==========================================="
echo ""

# Step 1: Check if git is initialized
if [ -d .git ]; then
    echo "✓ Git already initialized"
else
    echo "📦 Initializing git..."
    git init
    git config user.name "Your Name"
    git config user.email "your.email@example.com"
fi

# Step 2: Check .env security
echo ""
echo "🔒 Security Check:"
if [ -f .env ]; then
    echo "✓ .env file exists"
    if grep -q ".env" .gitignore; then
        echo "✓ .env is in .gitignore (safe!)"
    else
        echo "⚠️  WARNING: .env not in .gitignore!"
        echo "Adding .env to .gitignore..."
        echo ".env" >> .gitignore
    fi
else
    echo "⚠️  .env file not found"
fi

# Step 3: Check staged files
echo ""
echo "📋 Files to be committed:"
git add -A
git status --short | head -20

echo ""
echo "✓ Checking that .env is NOT staged..."
if git ls-files --cached | grep -q "^\.env$"; then
    echo "⚠️  WARNING: .env is staged! Unstaging..."
    git reset .env
else
    echo "✓ .env not staged (good!)"
fi

# Step 4: Show what will be committed
echo ""
echo "📦 Files that WILL be pushed:"
git ls-files | wc -l
echo "files total"

echo ""
echo "⏭️  Next steps:"
echo ""
echo "1. COMMIT & PUSH:"
echo "   git commit -m 'Initial commit: Face auth app with S3 and caching'"
echo "   git branch -M main"
echo "   git remote add origin https://github.com/YOUR_USERNAME/xplore-face-auth.git"
echo "   git push -u origin main"
echo ""
echo "2. CREATE RENDER ACCOUNT at https://render.com"
echo ""
echo "3. DEPLOY:"
echo "   - Click 'New Web Service'"
echo "   - Connect GitHub repository"
echo "   - Build Command: pip install -r requirements.txt"
echo "   - Start Command: uvicorn app:app --host 0.0.0.0 --port \$PORT"
echo ""
echo "4. ADD ENVIRONMENT VARIABLES in Render:"
echo "   - S3_BUCKET=xplore-face-auth-refs"
echo "   - AWS_REGION=us-east-1"
echo "   - AWS_ACCESS_KEY_ID=your-key"
echo "   - AWS_SECRET_ACCESS_KEY=your-secret"
echo "   - SECRET_KEY=generate-random-string"
echo ""
echo "ℹ️  For full guide, see: GITHUB_RENDER_SETUP.md"
