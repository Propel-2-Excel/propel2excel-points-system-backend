#!/bin/bash

# 🚀 Quick Bot Deployment Script for P2E Server Testing
# Run this script to quickly set up your bot for testing

echo "🤖 P2E Bot Testing Deployment Script"
echo "====================================="
echo ""

# Check if we're in the right directory
if [ ! -f "bot.py" ]; then
    echo "❌ Error: Please run this script from the bot directory"
    echo "   Current directory: $(pwd)"
    exit 1
fi

echo "✅ Bot files found"
echo ""

# Check environment variables
echo "🔍 Checking environment configuration..."

if [ -z "$DISCORD_TOKEN" ]; then
    echo "❌ DISCORD_TOKEN not set"
    echo "   Please set your Discord bot token:"
    echo "   export DISCORD_TOKEN='your_token_here'"
    exit 1
else
    echo "✅ DISCORD_TOKEN is set"
fi

if [ -z "$BACKEND_API_URL" ]; then
    echo "❌ BACKEND_API_URL not set"
    echo "   Please set your backend URL:"
    echo "   export BACKEND_API_URL='https://your-backend.onrender.com'"
    exit 1
else
    echo "✅ BACKEND_API_URL is set: $BACKEND_API_URL"
fi

if [ -z "$BOT_SHARED_SECRET" ]; then
    echo "❌ BOT_SHARED_SECRET not set"
    echo "   Please set your bot secret:"
    echo "   export BOT_SHARED_SECRET='your_secret_here'"
    exit 1
else
    echo "✅ BOT_SHARED_SECRET is set"
fi

echo ""
echo "🚀 Starting bot for testing..."

# Test the environment first
echo "🧪 Running environment tests..."
python test_environment.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Environment tests passed!"
    echo ""
    echo "🤖 Starting bot..."
    echo "   - Bot will connect to Discord"
    echo "   - Check your P2E server for bot presence"
    echo "   - Use !ping to test bot response"
    echo "   - Press Ctrl+C to stop bot"
    echo ""
    
    # Start the bot
    python bot.py
else
    echo ""
    echo "❌ Environment tests failed!"
    echo "   Please fix the issues above before starting the bot"
    exit 1
fi

