#!/usr/bin/env python3
import os
from llama_cpp import Llama

def test_model():
    model_path = "models/phi-2-2.7b.gguf"
    
    print(f"🔍 Testing model: {model_path}")
    print(f"📁 File exists: {os.path.exists(model_path)}")
    
    if os.path.exists(model_path):
        print(f"📏 File size: {os.path.getsize(model_path) / (1024**3):.2f} GB")
        
        try:
            print("🤖 Loading model...")
            model = Llama(
                model_path=model_path,
                n_ctx=1024,
                n_threads=8,
                n_gpu_layers=0,
                n_batch=512,
                use_mmap=True,
                use_mlock=False
            )
            print("✅ Model loaded successfully!")
            
            # Test a simple query
            print("🧪 Testing response...")
            response = model(
                "Hello, how are you?",
                max_tokens=50,
                temperature=0.5
            )
            print(f"📝 Response: {response}")
            
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            print(f"🔍 Error type: {type(e).__name__}")
    else:
        print("❌ Model file not found!")

if __name__ == "__main__":
    test_model()
