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

# Load dataset store
def load_datasets():
    """Load datasets from JSON file"""
    try:
        with open('data/datasets.json', 'r', encoding='utf-8') as f:
            datasets = json.load(f)
        print(f"📊 Loaded {len(datasets)} consolidated datasets")
        return datasets
    except FileNotFoundError:
        print("❌ Error: datasets.json not found in data folder")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in datasets.json: {e}")
        return []

# Global model instance for caching
_local_model = None

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
                n_ctx=2048,  # Increased context for longer prompts
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
    query = request.args.get('q', '').lower()
    owner_filter = request.args.get('owner', '').lower()
    topic_filter = request.args.get('topic', '').lower()
    year_filter = request.args.get('year', '').lower()
    data_type_filter = request.args.get('data_type', '').lower()
    
    # Pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)  # Show 20 datasets per page
    
    print(f"🔍 Search request - Query: '{query}', Owner: '{owner_filter}', Topic: '{topic_filter}', Year: '{year_filter}', Data Type: '{data_type_filter}', Page: {page}, Per Page: {per_page}")
    
    datasets = load_datasets()
    filtered_datasets = []
    
    for dataset in datasets:
        # Apply filters
        if query and query not in dataset.get('title', '').lower() and query not in dataset.get('description', '').lower():
            continue
        if owner_filter and owner_filter not in dataset.get('owner', '').lower():
            continue
        if topic_filter and topic_filter not in dataset.get('topic', '').lower():
            continue
        if year_filter and year_filter not in str(dataset.get('year', '')).lower():
            continue
        if data_type_filter and data_type_filter not in str(dataset.get('data_type', '')).lower():
            continue
        
        filtered_datasets.append(dataset)
    
    # Apply description truncation
    for dataset in filtered_datasets:
        if 'description' in dataset:
            dataset['description'] = truncate_description(dataset['description'], max_length=150)
    
    # Calculate pagination
    total_datasets = len(filtered_datasets)
    total_pages = (total_datasets + per_page - 1) // per_page
    
    # Ensure page is within valid range
    if page < 1:
        page = 1
    elif page > total_pages and total_pages > 0:
        page = total_pages
    
    # Get datasets for current page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_datasets = filtered_datasets[start_idx:end_idx]
    
    # Prepare pagination info
    pagination_info = {
        'current_page': page,
        'total_pages': total_pages,
        'total_datasets': total_datasets,
        'per_page': per_page,
        'start_idx': start_idx + 1 if total_datasets > 0 else 0,
        'end_idx': min(end_idx, total_datasets),
        'has_prev': page > 1,
        'has_next': page < total_pages
    }
    
    return jsonify({
        'datasets': page_datasets,
        'pagination': pagination_info
    })

@app.route('/dataset/<int:dataset_id>')
def dataset_detail(dataset_id):
    """Dataset detail page"""
    datasets = load_datasets()
    dataset = next((d for d in datasets if d['id'] == dataset_id), None)
    
    if not dataset:
        return "Dataset not found", 404
        
    return render_template('dataset_detail.html', dataset=dataset)

def truncate_description(description, max_length=150):
    """Truncate description to reasonable length while keeping it readable"""
    if len(description) <= max_length:
        return description
    
    # Find the last complete word within the limit
    truncated = description[:max_length]
    last_space = truncated.rfind(' ')
    
    if last_space > max_length * 0.8:  # If we can find a good break point
        return truncated[:last_space] + "..."
    else:
        return truncated + "..."


def find_relevant_datasets(query, datasets, top_n=15):
    """Find datasets relevant to the user's query with improved scoring"""
    query_lower = query.lower()
    relevant = []
    
    # Enhanced keywords that might indicate specific topics
    topic_keywords = {
        # Weather and Climate (highest specificity)
        'weather': ['Weather', 'Climate', 'Meteorology'],
        'climate': ['Weather', 'Climate', 'Meteorology'],
        'temperature': ['Weather', 'Climate', 'Meteorology'],
        'rainfall': ['Weather', 'Climate', 'Meteorology'],
        'precipitation': ['Weather', 'Climate', 'Meteorology'],
        'humidity': ['Weather', 'Climate', 'Meteorology'],
        'wind': ['Weather', 'Climate', 'Meteorology'],
        'solar': ['Weather', 'Climate', 'Meteorology'],
        'meteorology': ['Weather', 'Climate', 'Meteorology'],
        'bom': ['Weather', 'Climate', 'Meteorology'],
        'bureau of meteorology': ['Weather', 'Climate', 'Meteorology'],
        
        # Environment (but more specific)
        'environment': ['Environment', 'Weather'],
        'environmental': ['Environment', 'Weather'],
        'pollution': ['Environment', 'Weather'],
        'air quality': ['Environment', 'Weather'],
        'emissions': ['Environment', 'Weather'],
        
        # Health and Medical
        'health': ['Health', 'Medical'],
        'medical': ['Health', 'Medical'],
        'hospital': ['Health', 'Medical'],
        'disease': ['Health', 'Medical'],
        'mortality': ['Health', 'Medical'],
        
        # Economy and Business
        'economy': ['Economy', 'Business'],
        'economic': ['Economy', 'Business'],
        'financial': ['Economy', 'Business'],
        'business': ['Economy', 'Business'],
        'trade': ['Economy', 'Business'],
        'gdp': ['Economy', 'Business'],
        
        # Transport and Infrastructure
        'transport': ['Transport', 'Infrastructure'],
        'infrastructure': ['Transport', 'Infrastructure'],
        'roads': ['Transport', 'Infrastructure'],
        'railway': ['Transport', 'Infrastructure'],
        'aviation': ['Transport', 'Infrastructure'],
        
        # Demographics and Population
        'population': ['Demographics', 'Population'],
        'demographics': ['Demographics', 'Population'],
        'census': ['Demographics', 'Population'],
        'birth': ['Demographics', 'Population'],
        'death': ['Demographics', 'Population'],
        'migration': ['Demographics', 'Population'],
        
        # Education
        'education': ['Education', 'School'],
        'school': ['Education', 'School'],
        'university': ['Education', 'School'],
        'student': ['Education', 'School'],
        
        # Housing and Property
        'housing': ['Housing', 'Property'],
        'property': ['Housing', 'Property'],
        'real estate': ['Housing', 'Property'],
        'construction': ['Housing', 'Property'],
        
        # Justice and Crime
        'crime': ['Justice', 'Crime'],
        'justice': ['Justice', 'Crime'],
        'police': ['Justice', 'Crime'],
        'court': ['Justice', 'Crime'],
        
        # Agriculture and Farming
        'agriculture': ['Agriculture', 'Farming'],
        'farming': ['Agriculture', 'Farming'],
        'crop': ['Agriculture', 'Farming'],
        'livestock': ['Agriculture', 'Farming'],
        
        # Tourism and Travel
        'tourism': ['Tourism', 'Travel'],
        'travel': ['Tourism', 'Travel'],
        'hotel': ['Tourism', 'Travel'],
        
        # Technology and Innovation
        'technology': ['Technology', 'Innovation'],
        'innovation': ['Technology', 'Innovation'],
        'digital': ['Technology', 'Innovation'],
        
        # Taxation and Finance
        'tax': ['Economy', 'Taxation'],
        'taxation': ['Economy', 'Taxation'],
        'superannuation': ['Economy', 'Taxation'],
        'ato': ['Economy', 'Taxation'],
        
        # Employment and Labour
        'employment': ['Employment', 'Labour'],
        'labour': ['Employment', 'Labour'],
        'unemployment': ['Employment', 'Labour'],
        'job': ['Employment', 'Labour'],
        'workforce': ['Employment', 'Labour']
    }
    
    # Enhanced location keywords
    location_keywords = ['sydney', 'melbourne', 'brisbane', 'perth', 'adelaide', 'canberra', 'darwin', 'hobart', 'australia', 'national', 'state', 'victoria', 'nsw', 'queensland', 'wa', 'sa', 'tas', 'nt', 'act']
    
    # Enhanced year keywords
    year_keywords = ['2024', '2023', '2022', '2021', '2020', 'recent', 'latest', 'current', 'new', 'old', 'historical']
    
    # Enhanced owner keywords
    owner_keywords = ['abs', 'bureau', 'statistics', 'ato', 'taxation', 'education', 'health', 'transport', 'environment', 'bom', 'meteorology']
    
    # Score each dataset based on relevance
    scored_datasets = []
    for dataset in datasets:
        score = 0
        
        # Topic matching (highest priority) - but more specific
        for keyword, topics in topic_keywords.items():
            if keyword in query_lower and dataset['topic'] in topics:
                # Give higher score for weather/climate specific queries
                if keyword in ['weather', 'climate', 'temperature', 'rainfall', 'precipitation', 'humidity', 'wind', 'solar', 'meteorology', 'bom']:
                    if dataset['topic'] in ['Weather', 'Climate', 'Meteorology']:
                        score += 8  # Very high score for exact weather matches
                    else:
                        score += 2  # Lower score for generic environmental matches
                else:
                    score += 5  # Standard score for other topic matches
        
        # Title matching (very high priority) - but smarter
        title_lower = dataset['title'].lower()
        query_words = query_lower.split()
        
        # Check for exact phrase matches first
        if query_lower in title_lower:
            score += 10  # Very high score for exact phrase match
        
        # Check for important word matches
        important_words = [word for word in query_words if len(word) > 3 and word not in ['some', 'data', 'please', 'help', 'find', 'need', 'want']]
        for word in important_words:
            if word in title_lower:
                score += 3  # Good score for important word matches
        
        # Description matching (high priority) - but more selective
        desc_lower = dataset['description'].lower()
        
        # Check for exact phrase matches in description
        if query_lower in desc_lower:
            score += 8  # Very high score for exact phrase in description
        
        # Check for important word matches in description
        for word in important_words:
            if word in desc_lower:
                score += 2  # Good score for important words in description
        
        # Owner matching - but more specific
        if any(owner in query_lower for owner in owner_keywords):
            if any(owner in dataset['owner'].lower() for owner in owner_keywords):
                # Give bonus for weather-specific owners
                if any(weather_term in query_lower for weather_term in ['weather', 'climate', 'temperature', 'rainfall']):
                    if 'meteorology' in dataset['owner'].lower() or 'bom' in dataset['owner'].lower():
                        score += 5  # High bonus for weather data from BOM
                    else:
                        score += 2  # Standard bonus for other owners
                else:
                    score += 3  # Standard owner bonus
        
        # Year matching
        if any(year in query_lower for year in year_keywords):
            if str(dataset['year']) in query_lower:
                score += 2
            elif any(year in query_lower for year in ['recent', 'latest', 'current', 'new']):
                if dataset['year'] >= 2020:  # Consider recent years
                    score += 1
        
        # Location matching - skip for now since coverage field doesn't exist
        # if any(loc in query_lower for loc in location_keywords):
        #     if 'coverage' in dataset and any(loc in dataset['coverage'].lower() for loc in location_keywords):
        #         score += 2
        
        # Penalize generic environmental terms for weather queries
        if any(weather_term in query_lower for weather_term in ['weather', 'climate', 'temperature', 'rainfall']):
            if dataset['topic'] == 'Environment' and 'land' in title_lower.lower():
                score -= 2  # Penalize land cover/use datasets for weather queries
            if 'land cover' in title_lower or 'land use' in title_lower:
                score -= 3  # Further penalize land datasets for weather queries
        
        # Bonus for datasets that are clearly weather-related
        weather_indicators = ['weather', 'climate', 'temperature', 'rainfall', 'precipitation', 'humidity', 'wind', 'solar', 'meteorology', 'bom', 'bureau of meteorology']
        if any(indicator in title_lower for indicator in weather_indicators):
            if any(weather_term in query_lower for weather_term in ['weather', 'climate', 'temperature', 'rainfall']):
                score += 6  # High bonus for clearly weather-related datasets
        
        # Add to scored list if score > 0
        if score > 0:
            scored_datasets.append((dataset, score))
    
    # Sort by score (highest first) and return top results
    scored_datasets.sort(key=lambda x: x[1], reverse=True)
    
    # Return top relevant datasets with truncated descriptions
    relevant_datasets = []
    for dataset, score in sorted(scored_datasets, key=lambda x: x[1], reverse=True)[:top_n]:
        # Create a copy of the dataset with truncated description
        truncated_dataset = dataset.copy()
        truncated_dataset['description'] = truncate_description(dataset['description'], max_length=150)
        relevant_datasets.append(truncated_dataset)
    
    print(f"🔍 Query: '{query}' - Found {len(relevant_datasets)} relevant datasets out of {len(datasets)} total")
    if relevant_datasets:
        print(f"🔍 Top matches: {[f'{d['id']}:{d['title'][:30]}...' for d in relevant_datasets[:3]]}")
    
    return relevant_datasets

@app.route('/chat', methods=['POST'])
def chat():
    """AI chat endpoint"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({'error': 'No message provided'}), 400
        
        print(f"🔍 Chat request: {user_message}")
        
        datasets = load_datasets()
        
        # SMART DATASET SELECTION: Only include most relevant datasets to avoid context overflow
        relevant_datasets_for_context = find_relevant_datasets(user_message, datasets)
        
        # Limit context to top 15 most relevant datasets to stay within token limits
        context_datasets = relevant_datasets_for_context[:15]
        
        # If no relevant datasets found, include a few general ones
        if not context_datasets:
            context_datasets = datasets[:5]
        
        # Create focused dataset context (much shorter)
        dataset_summary = []
        for d in context_datasets:
            dataset_summary.append(f"{d['id']}: {d['title']} ({d['topic']}, {d['owner']})")
        
        # Create system prompt (much shorter and focused)
        system_prompt = f"""You are an AI assistant for Australian open datasets. 

Available datasets for this query: {', '.join(dataset_summary)}

Help users find relevant data and cite dataset IDs. Be specific about which datasets match their needs.

Rules:
- Only recommend datasets that are actually available in the list above
- Cite dataset IDs when making recommendations
- If no exact match, suggest the closest alternatives
- Be concise and helpful"""
        
        print(f"🔍 Context datasets: {len(context_datasets)} (out of {len(datasets)} total)")
        print(f"🔍 System prompt length: {len(system_prompt)} characters")
        
        # Try local model first, then OpenAI as fallback
        ai_response = None
        
        # Try local model - using the exact working code from our test
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
                        max_tokens=150,  # Increased slightly for better responses
                        temperature=0.3   # Lower temperature for more focused responses
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
                    print(f"�� Error type: {type(e).__name__}")
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
        
        # Find relevant datasets based on the query (for display)
        relevant_datasets = find_relevant_datasets(user_message, datasets)
        
        # Limit displayed results to top 10 most relevant
        relevant_datasets = relevant_datasets[:10]
        
        return jsonify({
            'response': ai_response,
            'relevant_datasets': relevant_datasets
        })
        
    except Exception as e:
        print(f"❌ Chat error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/datasets')
def api_datasets():
    """API endpoint to get all datasets"""
    datasets = load_datasets()
    return jsonify(datasets)

if __name__ == '__main__':
    app.run(debug=True)
