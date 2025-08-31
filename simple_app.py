#!/usr/bin/env python3
from flask import Flask, request, jsonify
from llama_cpp import Llama
import os

app = Flask(__name__)

# Simple model loading
MODEL_PATH = 'models/phi-2-2.7b.gguf'
model = None

def load_model():
    global model
    if model is None:
        print(f"🤖 Loading model: {MODEL_PATH}")
        model = Llama(
            model_path=MODEL_PATH,
            n_ctx=1024,
            n_threads=8,
            n_gpu_layers=0
        )
        print("✅ Model loaded!")
    return model

@app.route('/')
def home():
    return "AI Chat App is running! Use /chat to test."

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        message = data.get('message', 'Hello')
        
        print(f"📝 Received message: {message}")
        
        # Load model
        local_model = load_model()
        
        # Simple prompt
        prompt = f"User: {message}\n\nAssistant:"
        
        print("🤖 Generating response...")
        
        # Get response
        response = local_model(
            prompt,
            max_tokens=100,
            temperature=0.5
        )
        
        print(f"📝 Response: {response}")
        
        if response and 'choices' in response and len(response['choices']) > 0:
            ai_response = response['choices'][0]['text'].strip()
            print(f"✅ Success: {ai_response[:100]}...")
        else:
            ai_response = "Sorry, I couldn't generate a response."
            print("⚠️ No response generated")
        
        return jsonify({
            'response': ai_response,
            'status': 'success'
        })
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting simple AI chat app...")
    print(f"📁 Model path: {MODEL_PATH}")
    print(f"📁 Model exists: {os.path.exists(MODEL_PATH)}")
    
    app.run(debug=True, port=5001)
