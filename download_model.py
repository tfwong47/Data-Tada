#!/usr/bin/env python3
import requests
import os
from tqdm import tqdm

def download_file(url, filename):
    """Download a file with progress bar"""
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    
    with open(filename, 'wb') as file, tqdm(
        desc=filename,
        total=total_size,
        unit='iB',
        unit_scale=True,
        unit_divisor=1024,
    ) as pbar:
        for data in response.iter_content(chunk_size=1024):
            size = file.write(data)
            pbar.update(size)

def main():
    print("🚀 GPT-OSS-7B Model Downloader")
    print("=================================")
    print("")
    
    # Create models directory if it doesn't exist
    if not os.path.exists('models'):
        os.makedirs('models')
        print("📁 Created models directory")
    
    # Model URL and filename
    model_url = "https://huggingface.co/TheBloke/gpt-oss-7B-GGUF/resolve/main/gpt-oss-7b.Q4_K_M.gguf"
    model_filename = "models/gpt-oss-7b.gguf"
    
    print(f"📥 Downloading GPT-OSS-7B model...")
    print(f"🔗 URL: {model_url}")
    print(f"💾 Expected size: ~15GB")
    print("")
    
    try:
        download_file(model_url, model_filename)
        print("")
        print("✅ Download completed successfully!")
        print(f"📁 Model saved to: {model_filename}")
        
        # Update .env file
        env_file = '.env'
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                content = f.read()
            
            # Update the LOCAL_MODEL_PATH
            content = content.replace(
                'LOCAL_MODEL_PATH=models/gpt-oss-20b.gguf',
                'LOCAL_MODEL_PATH=models/gpt-oss-7b.gguf'
            )
            
            with open(env_file, 'w') as f:
                f.write(content)
            
            print("✅ .env file updated!")
        
        print("")
        print("🚀 You can now start your application with:")
        print("   ./start.sh")
        print("")
        print("🤖 The AI assistant will use your local GPT-OSS-7B model!")
        
    except Exception as e:
        print(f"❌ Download failed: {e}")
        print("💡 Try downloading manually from Hugging Face")

if __name__ == "__main__":
    main()
