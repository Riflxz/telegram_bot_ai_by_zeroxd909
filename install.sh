#!/bin/bash

# Alya Telegram Bot v2.0 Installation Script
# Enhanced security and anti-spam features

echo "🚀 Installing Alya Telegram Bot v2.0..."
echo "==============================================="

# Check Python version
python_version=$(python3 --version 2>&1)
echo "✓ Python version: $python_version"

# Install requirements
echo "📦 Installing Python dependencies..."
pip install -r bot_requirements.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p backups
mkdir -p logs

# Set permissions
chmod +x main.py

echo ""
echo "✅ Installation completed!"
echo ""
echo "📋 Next steps:"
echo "1. Set your Telegram bot token:"
echo "   export TELEGRAM_TOKEN='your_bot_token_here'"
echo ""
echo "2. Start the bot:"
echo "   python main.py"
echo ""
echo "3. Available admin commands:"
echo "   /start /help /status /on /off /ban /unban"
echo "   /mute /unmute /backup /resetlimit /marksafe"
echo ""
echo "🛡️  Security features active:"
echo "   ✓ Anti-spam detection"
echo "   ✓ Rate limiting per user" 
echo "   ✓ Automatic moderation"
echo "   ✓ User verification"
echo "   ✓ Automated backups"
echo ""
echo "Happy botting! 🤖"