#!/usr/bin/env python3
from flask import Flask
import os
from llama_cpp import Llama

app = Flask(__name__)

# Configure Local Model
LOCAL_MODEL_PATH = 'models/phi-2-2.7b.gguf'
USE_LOCAL_MODEL = True

# Global model instance
_local_model = None

def get_local_model():
    """Initialize and return local LLM model (cached)"""
    global _local_model
    
    if _local_model is not None:
        return _local_model
        
    try:
        if USE_LOCAL_MODEL and os.path.exists(LOCAL_MODEL_PATH):
            print(f"🤖 Loading local model: {LOCAL_MODEL_PATH}")
            _local_model = Llama(
                model_path=LOCAL_MODEL_PATH,
                n_ctx=1024,
                n_threads=8,
                n_gpu_layers=0,
                n_batch=512,
                use_mmap=True,
                use_mlock=False
            )
            print(f"✅ Model loaded and cached successfully!")
            return _local_model
        else:
            print(f"⚠️ Local model not found at: {LOCAL_MODEL_PATH}")
            return None
    except Exception as e:
        print(f"❌ Error loading local model: {e}")
        return None

@app.route('/test')
def test_model():
    try:
        model = get_local_model()
        if model:
            # Test a simple query
            response = model(
                "Hello, how are you?",
                max_tokens=50,
                temperature=0.5
            )
            return f"Model loaded successfully! Response: {response}"
        else:
            return "Model failed to load"
    except Exception as e:
        return f"Error: {e}"

if __name__ == '__main__':
    print("🧪 Testing Flask model loading...")
    model = get_local_model()
    if model:
        print("✅ Model loaded in Flask context!")
    else:
        print("❌ Model failed to load in Flask context!")
    
    app.run(debug=True, port=8081)
