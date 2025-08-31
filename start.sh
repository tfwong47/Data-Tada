#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "📝 Please create a .env file with your OpenAI API key:"
    echo "   OPENAI_API_KEY=your_actual_api_key_here"
    echo ""
    echo "🔑 Get your API key from: https://platform.openai.com/api-keys"
    echo ""
    echo "📋 You can copy from env.example:"
    echo "   cp env.example .env"
    echo "   # Then edit .env and add your actual API key"
    echo ""
    echo "🚀 Starting application without AI features..."
    echo "   (Chat will show errors until API key is configured)"
    echo ""
fi

# Start the application
echo "🚀 Starting Australia Open Data Discovery Hub..."
echo "📊 Loaded 20 curated Australian datasets"
echo "🤖 AI Assistant powered by OpenAI GPT-3.5-turbo"
echo "🌐 Open your browser to: http://localhost:3000"
echo "💡 Press Ctrl+C to stop the server"
echo "-" * 60

python3 run.py
