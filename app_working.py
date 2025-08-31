from flask import Flask, render_template, request, jsonify
import json
import os
from dotenv import load_dotenv
import openai
from llama_cpp import Llama

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')

# Configure Local Model (hardcoded for now to ensure it works)
LOCAL_MODEL_PATH = 'models/phi-2-2.7b.gguf'
USE_LOCAL_MODEL = True

print(f"🔍 Model configuration:")
print(f"   LOCAL_MODEL_PATH: {LOCAL_MODEL_PATH}")
print(f"   USE_LOCAL_MODEL: {USE_LOCAL_MODEL}")
print(f"   File exists: {os.path.exists(LOCAL_MODEL_PATH)}")

# Global model instance for caching
_local_model = None

# Load dataset store
def load_datasets():
    with open('data/datasets.json', 'r', encoding='utf-8') as f:
        return json.load(f)

# Initialize local model
def get_local_model():
    """Initialize and return local LLM model (cached)"""
    global _local_model
    
    if _local_model is not None:
        return _local_model
        
    try:
        if USE_LOCAL_MODEL and os.path.exists(LOCAL_MODEL_PATH):
            print(f"🤖 Loading local model: {LOCAL_MODEL_PATH}")
            # Optimize for speed with Phi-2
            _local_model = Llama(
                model_path=LOCAL_MODEL_PATH,
                n_ctx=1024,  # Smaller context for speed
                n_threads=8,  # More threads for faster processing
                n_gpu_layers=0,  # Set to higher number if you have GPU
                n_batch=512,  # Larger batch size for speed
                use_mmap=True,  # Memory mapping for faster loading
                use_mlock=False  # Don't lock memory for speed
            )
            print(f"✅ Model loaded and cached successfully!")
            return _local_model
        else:
            print(f"⚠️ Local model not found at: {LOCAL_MODEL_PATH}")
            return None
    except Exception as e:
        print(f"❌ Error loading local model: {e}")
        return None

@app.route('/')
def index():
    """Main page with search and dataset catalogue"""
    datasets = load_datasets()
    return render_template('index.html', datasets=datasets)

@app.route('/search')
def search():
    """Search datasets by keyword and filters"""
    query = request.args.get('q', '').lower()
    owner = request.args.get('owner', '')
    topic = request.args.get('topic', '')
    year = request.args.get('year', '')
    
    datasets = load_datasets()
    results = []
    
    for dataset in datasets:
        # Keyword search
        if query and query not in dataset['title'].lower() and query not in dataset['description'].lower():
            continue
            
        # Filter by owner
        if owner and owner != dataset['owner']:
            continue
            
        # Filter by topic
        if topic and topic != dataset['topic']:
            continue
            
        # Filter by year
        if year and year != str(dataset['year']):
            continue
            
        results.append(dataset)
    
    return jsonify(results)

@app.route('/dataset/<int:dataset_id>')
def dataset_detail(dataset_id):
    """Dataset detail page"""
    datasets = load_datasets()
    dataset = next((d for d in datasets if d['id'] == dataset_id), None)
    
    if not dataset:
        return "Dataset not found", 404
        
    return render_template('dataset_detail.html', dataset=dataset)

@app.route('/chat', methods=['POST'])
def chat():
    """AI chat endpoint"""
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        
        if not user_message:
            return jsonify({'error': 'No message provided'}), 400
            
        # Load datasets for context
        datasets = load_datasets()
        
        # Create context for AI
        dataset_context = "\n\n".join([
            f"Dataset {d['id']}: {d['title']} - {d['description']} "
            f"(Owner: {d['owner']}, Topic: {d['topic']}, Year: {d['year']}, "
            f"License: {d['license']}, Coverage: {d['coverage']})"
            for d in datasets
        ])
        
        # Create system prompt
        system_prompt = f"""You are an AI assistant helping users discover Australian open datasets. 
        You have access to the following {len(datasets)} datasets:
        
        {dataset_context}
        
        Your role is to:
        1. Help users understand what data they need
        2. Recommend relevant datasets from the available inventory
        3. Explain dataset metadata in simple terms
        4. Always cite specific dataset IDs when making recommendations
        
        Keep responses helpful, accurate, and focused on the available datasets."""
        
        # Try local model first
        ai_response = None
        
        if USE_LOCAL_MODEL:
            print(f"🔍 USE_LOCAL_MODEL: {USE_LOCAL_MODEL}")
            local_model = get_local_model()
            print(f"🔍 Local model object: {local_model}")
            
            if local_model:
                try:
                    print("🤖 Using local model for response...")
                    prompt = f"{system_prompt}\n\nUser: {user_message}\n\nAssistant:"
                    print(f"🔍 Prompt length: {len(prompt)} characters")
                    
                    # Use the exact working parameters from our test
                    response = local_model(
                        prompt,
                        max_tokens=100,
                        temperature=0.5
                    )
                    
                    print(f"🔍 Raw response: {response}")
                    
                    if response and 'choices' in response and len(response['choices']) > 0:
                        ai_response = response['choices'][0]['text'].strip()
                        print(f"✅ Local model response successful: {ai_response[:100]}...")
                    else:
                        print("⚠️ Local model returned empty response")
                        ai_response = None
                        
                except Exception as e:
                    print(f"❌ Local model error: {e}")
                    print(f"🔍 Error type: {type(e).__name__}")
                    import traceback
                    traceback.print_exc()
                    ai_response = None
            else:
                print("⚠️ Local model is None")
        
        # Fallback to OpenAI if local model failed or not available
        if not ai_response and openai.api_key:
            try:
                print("🔄 Trying OpenAI as fallback...")
                client = openai.OpenAI(api_key=openai.api_key)
                
                # Try different models in order of preference
                models_to_try = ["gpt-3.5-turbo", "gpt-4o-mini", "gpt-4o"]
                
                for model in models_to_try:
                    try:
                        response = client.chat.completions.create(
                            model=model,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_message}
                            ],
                            max_tokens=500,
                            temperature=0.7
                        )
                        ai_response = response.choices[0].message.content
                        print(f"✅ OpenAI model {model} successful")
                        break
                    except Exception as e:
                        print(f"❌ OpenAI model {model} failed: {str(e)[:100]}...")
                        if "insufficient_quota" in str(e) or "quota" in str(e):
                            continue
                        else:
                            raise e
                            
            except Exception as e:
                print(f"❌ OpenAI fallback failed: {e}")
        
        # Final fallback if both local and OpenAI failed
        if not ai_response:
            ai_response = f"""I'm currently experiencing technical difficulties with my AI service. 

However, I can still help you explore the {len(datasets)} available datasets! Here are some suggestions:

• **Search by topic**: Try filtering by topics like 'Health', 'Environment', 'Economy', or 'Transport'
• **Browse by owner**: Look for datasets from specific sources like 'Australian Bureau of Statistics' or 'Bureau of Meteorology'
• **Use the search bar**: Type keywords related to your research needs

For example, if you're looking for climate data, try filtering by topic 'Environment' and owner 'Bureau of Meteorology'.

Please check back later for AI assistance, or contact support if you need immediate help."""
        
        return jsonify({
            'response': ai_response,
            'datasets': datasets
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/datasets')
def api_datasets():
    """API endpoint to get all datasets"""
    datasets = load_datasets()
    return jsonify(datasets)

if __name__ == '__main__':
    app.run(debug=True)
