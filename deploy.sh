#!/bin/bash

# Deployment helper script for Xplore Face Auth App
# Usage: ./deploy.sh <platform>
# Platforms: render, railway, fly

set -e

PLATFORM=${1:-"render"}

echo "🚀 Xplore Face Auth App - Deployment Helper"
echo "==========================================="
echo ""

# Check if git is initialized
if [ ! -d .git ]; then
    echo "❌ Git not initialized. Run: git init"
    exit 1
fi

# Check if .env exists locally
if [ -f .env ]; then
    echo "✓ Local .env file found"
    echo "⚠️  Make sure .env is in .gitignore (it is!)"
else
    echo "⚠️  No .env file found locally"
fi

# Verify requirements.txt exists
if [ ! -f requirements.txt ]; then
    echo "❌ requirements.txt not found!"
    exit 1
fi

echo ""
echo "📋 Files that will be deployed:"
git ls-files | head -20
echo "..."
echo ""

case $PLATFORM in
    "render")
        echo "🎯 Deploying to Render"
        echo ""
        echo "Steps:"
        echo "1. Go to https://dashboard.render.com"
        echo "2. Click 'New +' → 'Web Service'"
        echo "3. Connect GitHub repository"
        echo "4. Set Build Command: pip install -r requirements.txt"
        echo "5. Set Start Command: uvicorn app:app --host 0.0.0.0 --port \$PORT"
        echo "6. Click 'Environment' and add:"
        echo "   - S3_BUCKET=xplore-face-auth-refs"
        echo "   - AWS_REGION=us-east-1"
        echo "   - AWS_ACCESS_KEY_ID=<your-key>"
        echo "   - AWS_SECRET_ACCESS_KEY=<your-secret>"
        echo "   - SECRET_KEY=<random-string>"
        echo "7. Deploy!"
        ;;
    
    "railway")
        echo "🎯 Deploying to Railway"
        echo ""
        echo "Steps:"
        echo "1. Go to https://railway.app"
        echo "2. Click 'New Project' → 'Deploy from GitHub'"
        echo "3. Select your repository"
        echo "4. Go to Variables tab and add:"
        echo "   - S3_BUCKET=xplore-face-auth-refs"
        echo "   - AWS_REGION=us-east-1"
        echo "   - AWS_ACCESS_KEY_ID=<your-key>"
        echo "   - AWS_SECRET_ACCESS_KEY=<your-secret>"
        echo "   - SECRET_KEY=<random-string>"
        echo "5. Railway auto-detects Python and deploys!"
        ;;
    
    "fly")
        echo "🎯 Deploying to Fly.io"
        echo ""
        echo "Steps:"
        echo "1. Install Fly CLI: brew install flyctl"
        echo "2. Run: flyctl auth login"
        echo "3. In this directory, run: flyctl launch"
        echo "4. Follow prompts, choose Python region"
        echo "5. Set secrets:"
        echo "   flyctl secrets set S3_BUCKET=xplore-face-auth-refs"
        echo "   flyctl secrets set AWS_REGION=us-east-1"
        echo "   flyctl secrets set AWS_ACCESS_KEY_ID=<your-key>"
        echo "   flyctl secrets set AWS_SECRET_ACCESS_KEY=<your-secret>"
        echo "   flyctl secrets set SECRET_KEY=<random-string>"
        echo "6. Deploy: flyctl deploy"
        ;;
    
    *)
        echo "❌ Unknown platform: $PLATFORM"
        echo "Supported: render, railway, fly"
        exit 1
        ;;
esac

echo ""
echo "📖 For full deployment guide, see: DEPLOYMENT_GUIDE.md"
