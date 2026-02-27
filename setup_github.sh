#!/bin/bash

# Setup GitHub remote repository
# Run this after creating a repository on GitHub

echo "🔗 Setting up GitHub remote..."
echo ""

# Check if we're in a git repo
if [ ! -d ".git" ]; then
    echo "❌ Not a Git repository!"
    echo "   Run: git init"
    exit 1
fi

# Get GitHub username and repo name
echo "📝 Enter your GitHub username:"
read GITHUB_USER

echo "📝 Enter repository name (default: AutoHedge):"
read REPO_NAME
REPO_NAME=${REPO_NAME:-AutoHedge}

# Construct remote URL
REMOTE_URL="https://github.com/${GITHUB_USER}/${REPO_NAME}.git"

echo ""
echo "🔗 Adding remote: $REMOTE_URL"

# Add remote
git remote add origin "$REMOTE_URL" 2>/dev/null || git remote set-url origin "$REMOTE_URL"

# Check remote
git remote -v

echo ""
echo "✅ Remote configured!"
echo ""
echo "📤 Next steps:"
echo ""
echo "1. Create repository on GitHub:"
echo "   https://github.com/new"
echo "   Name: $REPO_NAME"
echo "   Description: AI-powered crypto trading bot with RL + LLM"
echo "   Public or Private: Your choice"
echo "   ❌ DO NOT initialize with README (we have one)"
echo ""
echo "2. Push to GitHub:"
echo "   git push -u origin main"
echo ""
echo "3. (Optional) Set up GitHub Actions for CI/CD"
echo "   Create: .github/workflows/tests.yml"
echo ""
echo "4. (Optional) Add branch protection rules"
echo "   Settings → Branches → Add rule"
echo "   - Require pull request reviews"
echo "   - Require status checks"
echo ""
