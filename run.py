#!/usr/bin/env python3
"""
Australia Open Data Discovery Hub - Startup Script
"""

from app import app

if __name__ == '__main__':
    print("🚀 Starting Australia Open Data Discovery Hub...")
    print("📊 Loaded 20 curated Australian datasets")
    print("🤖 AI Assistant powered by OpenAI GPT-3.5-turbo")
    print("🌐 Open your browser to: http://localhost:8080")
    print("💡 Press Ctrl+C to stop the server")
    print("-" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=3000)
