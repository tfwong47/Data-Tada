#!/bin/bash

echo "🚀 GPT-OSS-20B Model Downloader"
echo "================================="
echo ""

# Check if models directory exists
if [ ! -d "models" ]; then
    echo "Creating models directory..."
    mkdir -p models
fi

cd models

echo "📥 Available model options:"
echo "1. GPT-OSS-20B (Recommended - ~40GB)"
echo "2. GPT-OSS-15B (Medium - ~30GB)"
echo "3. GPT-OSS-7B (Small - ~15GB)"
echo ""

read -p "Which model would you like to download? (1-3): " choice

case $choice in
    1)
        MODEL_URL="https://huggingface.co/TheBloke/gpt-oss-20B-GGUF/resolve/main/gpt-oss-20b.Q4_K_M.gguf"
        MODEL_NAME="gpt-oss-20b.gguf"
        ;;
    2)
        MODEL_URL="https://huggingface.co/TheBloke/gpt-oss-15B-GGUF/resolve/main/gpt-oss-15b.Q4_K_M.gguf"
        MODEL_NAME="gpt-oss-15b.gguf"
        ;;
    3)
        MODEL_URL="https://huggingface.co/TheBloke/gpt-oss-7B-GGUF/resolve/main/gpt-oss-7b.Q4_K_M.gguf"
        MODEL_NAME="gpt-oss-7b.gguf"
        ;;
    *)
        echo "Invalid choice. Using default GPT-OSS-20B."
        MODEL_URL="https://huggingface.co/TheBloke/gpt-oss-20B-GGUF/resolve/main/gpt-oss-20b.Q4_K_M.gguf"
        MODEL_NAME="gpt-oss-20b.gguf"
        ;;
esac

echo ""
echo "📥 Downloading $MODEL_NAME..."
echo "🔗 URL: $MODEL_URL"
echo "💾 This may take a while depending on your internet speed..."
echo ""

# Download the model
curl -L -o "$MODEL_NAME" "$MODEL_URL"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Download completed successfully!"
    echo "📁 Model saved to: models/$MODEL_NAME"
    echo ""
    echo "🔄 Updating .env file..."
    
    # Update .env file with the correct model path
    cd ..
    sed -i.bak "s|LOCAL_MODEL_PATH=.*|LOCAL_MODEL_PATH=models/$MODEL_NAME|" .env
    
    echo "✅ .env file updated!"
    echo ""
    echo "🚀 You can now start your application with:"
    echo "   ./start.sh"
    echo ""
    echo "🤖 The AI assistant will use your local model!"
else
    echo ""
    echo "❌ Download failed. Please check your internet connection and try again."
    echo "💡 Alternative: Download manually from Hugging Face and place in models/ directory"
fi
