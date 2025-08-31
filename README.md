# 🚀 Australia Open Data Discovery Hub

An intelligent web application that helps users discover and explore Australian open datasets using natural language AI search. Built with Flask and powered by local AI models. https://youtu.be/UeZW2ft1hg4

> **⚠️ Important Disclaimer**: This project is created for **showcase and demonstration purposes only**. The AI-generated responses and dataset information may not be accurate, complete, or up-to-date. This is not intended for production use or as a reliable source of government data.

## ✨ Features

> **🎭 Demo Project**: This is a showcase application demonstrating modern web development techniques, AI integration, and accessibility best practices.

- **🤖 AI-Powered Search**: Natural language queries to find relevant datasets
- **📊 Dataset Discovery**: Browse curated Australian government datasets
- **🔍 Smart Filtering**: Filter by topic, owner, year, and location
- **💻 Local AI**: Runs completely offline using local language models
- **🎨 Modern UI**: Beautiful, responsive interface with accessibility features
- **⚡ Fast Performance**: Optimized for quick responses
- **🎯 View Modes**: Toggle between grid and list views for datasets
- **🔊 Voice Search**: Hands-free voice input with automatic AI search

- **📱 Responsive Design**: Works perfectly on all devices

## 🏗️ Architecture

- **Backend**: Flask (Python)
- **Frontend**: HTML5, CSS3, JavaScript (Bootstrap 5)
- **AI Engine**: Local LLM using llama-cpp-python
- **Data**: JSON-based dataset storage
- **Styling**: Custom CSS with modern design principles

- **Voice Recognition**: Web Speech API integration
- **Responsive Layout**: CSS Grid and Flexbox for modern layouts

## 📋 Prerequisites

- Python 3.8+
- macOS/Linux/Windows
- At least 2GB free RAM
- 2GB+ free disk space for the AI model
- Python scrapy

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd GovHack
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Download AI Model

**⚠️ Important**: The AI model is not included due to size (~1.7GB). You need to download it manually.

#### Option A: Download Phi-2 (Recommended - Fastest)
```bash
# Create models directory
mkdir -p models

# Download Phi-2 model (1.7GB)
curl -L -o models/phi-2-2.7b.gguf "https://huggingface.co/TheBloke/phi-2-GGUF/resolve/main/phi-2-2.7b.gguf"
```

#### Option B: Download CodeLlama (Alternative)
```bash
# Download CodeLlama-7B-Python (3.8GB)
curl -L -o models/codellama-7b-python.gguf "https://huggingface.co/TheBloke/CodeLlama-7B-Python-GGUF/resolve/main/codellama-7b-python.Q4_K_M.gguf"
```

#### Option C: Use Download Script
```bash
# Make script executable
chmod +x download_model.sh

# Run the script
./download_model.sh
```

### 5. Configure Environment
```bash
# Copy example environment file
cp env.example .env

# Edit .env file with your settings
nano .env
```

**Required .env settings:**
```env
USE_LOCAL_MODEL=true
LOCAL_MODEL_PATH=models/phi-2-2.7b.gguf
FLASK_ENV=development
FLASK_DEBUG=True
```

### 6. Run the Application
```bash
# Start the Flask server
python3 run.py

# Or use the convenience script
./start.sh
```

## 📁 Project Structure

```
GovHack/
├── app.py                 # Main Flask application
├── run.py                 # Application entry point
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (create from env.example)
├── .gitignore            # Git ignore rules
├── models/               # AI model files (not in Git)
│   └── phi-2-2.7b.gguf  # Download manually (1.7GB)
├── static/               # CSS, JS, images
├── templates/            # HTML templates
├── data/                 # Dataset JSON files
└── venv/                 # Virtual environment (not in Git)
```

## 🚫 What's NOT in Git

The following files are intentionally excluded from version control:

- **AI Models**: Large model files (1.7GB+) are not uploaded
- **Virtual Environment**: `venv/` folder is excluded
- **Environment Variables**: `.env` file with sensitive data
- **Cache Files**: Python cache and temporary files
- **IDE Files**: Editor-specific configuration files
- **OS Files**: System-generated files (.DS_Store, Thumbs.db)

## 🔧 Model Management

### Why Models Aren't in Git?
- **Size**: Model files are 1.7GB+ and would make the repo huge
- **Updates**: Models can be updated independently of code
- **Storage**: Git isn't designed for large binary files
- **Performance**: Large repos are slow to clone and manage

### How to Share Models?
1. **Document the download process** (as done in this README)
2. **Use model hosting services** (Hugging Face, etc.)
3. **Create download scripts** (like `download_model.sh`)
4. **Document model requirements** (size, format, etc.)

### 7. Access Your App
Open your browser and go to: **http://localhost:8080**

## 🔧 Configuration

### Model Settings
- **Model Path**: Set `LOCAL_MODEL_PATH` in `.env`
- **Context Window**: Default 2048 tokens (configurable in `app.py`)
- **Temperature**: Adjustable for response creativity

### Dataset Configuration
- Edit `data/datasets.json` to add/modify datasets
- Structure: title, description, owner, topic, year, coverage
- Automatic reload on changes

## 📁 Project Structure

```
GovHack/
├── app.py                 # Main Flask application
├── run.py                 # Application entry point
├── requirements.txt       # Python dependencies
├── .env                   # Environment configuration
├── data/
│   └── datasets.json     # Dataset definitions
├── models/                # AI model storage
├── static/
│   └── css/
│       └── custom.css    # Custom styling
├── templates/
│   ├── base.html         # Base template
│   └── index.html        # Main page
├── start.sh              # Convenience startup script
├── download_model.sh      # Model download script
└── README.md             # This file
```

## 🤖 AI Model Information

### Current Model: Phi-2 (2.7B parameters)
- **Size**: ~1.7GB
- **Performance**: Fast responses (1-3 seconds)
- **Quality**: Good for dataset search and analysis
- **Context**: 2048 tokens
- **Hardware**: Works on CPU, optimized for Apple Silicon

### Alternative Models
- **CodeLlama-7B**: Better code understanding, larger (3.8GB)
- **GPT-OSS-20B**: Higher quality, much larger (40GB+)
- **TinyLlama-1.1B**: Fastest, lower quality (1.1GB)

## 🎯 Usage Examples

### Natural Language Queries
- "Find climate data for Sydney"
- "Show me health datasets from 2024"
- "Transport infrastructure data"
- "Population statistics by state"

### Traditional Search
- Use filters for topic, owner, year
- Browse all datasets
- View detailed dataset information

### Web Scraping with Sitemap
```bash
python run_from_sitemap.py https://example/sitemap.xml --item-limit 100 --page-limit 50 --output datasets.json
```

**Parameters:**
- `--item-limit`: Number of output entries to generate
- `--page-limit`: Number of websites to web scrape
- `--output`: Output file name (should be datasets.json)

**Note:** The `api_links.txt` file contains all the API URLs to be used for data extraction.

## 🛠️ Development

### AI-Powered Development
This project was developed with the assistance of **Generative AI** tools, which provided:
- **Intelligent Code Assistance**: AI-powered code suggestions and improvements
- **Development Guidance**: Best practices and architectural recommendations
- **UI/UX Enhancement**: Accessibility improvements and modern design patterns
- **Problem Solving**: AI-assisted debugging and feature implementation
- **Documentation**: AI-generated documentation and code comments

### Adding New Datasets
1. Edit `data/datasets.json`
2. Add new dataset entries
3. Save file (auto-reload enabled)

### Customizing AI Responses
1. Modify prompts in `app.py`
2. Adjust `find_relevant_datasets()` function
3. Update system prompts for different behaviors

### Styling Changes
1. Edit `static/css/custom.css`
2. Modify `templates/index.html`
3. Refresh browser to see changes

## 🔍 Troubleshooting

### Model Loading Issues
```bash
# Check model file exists
ls -lh models/

# Verify .env configuration
cat .env | grep MODEL

# Check Python dependencies
pip list | grep llama
```

### Port Conflicts
```bash
# Kill process on port 8080
lsof -ti:8080 | xargs kill -9

# Or use different port
export FLASK_RUN_PORT=5000
```

### Memory Issues
- Reduce model context window in `app.py`
- Use smaller models (TinyLlama-1.1B)
- Close other applications

## 📊 Performance Tips

- **Fastest**: Phi-2 (1.7GB) - Best balance
- **Lightweight**: TinyLlama-1.1B (1.1GB) - Fastest
- **Quality**: CodeLlama-7B (3.8GB) - Better responses
- **Best**: GPT-OSS-20B (40GB+) - Highest quality

## 🆕 Recent Updates

### Version 2.0 - Enhanced User Experience
- **🎯 View Toggle**: Grid and list view modes for datasets
- **🔊 Voice Search**: Hands-free voice input with auto-search

- **🎨 UI Redesign**: Modern, professional interface
- **📱 Responsive**: Optimized for all screen sizes
- **🎨 High Contrast**: Enhanced text visibility and readability

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 🚀 Development Methodology

### Project Purpose
This project serves as a **demonstration and learning tool** showcasing:
- **Modern Web Development**: Flask and responsive design
- **AI Integration**: Local language models and natural language processing
- **Best Practices**: Responsive design and modern UI/UX
- **Development Workflow**: AI-assisted development and rapid prototyping

### AI-Assisted Development
This project demonstrates the power of **AI-assisted development**:
- **Rapid Prototyping**: AI tools enabled quick iteration and testing
- **Best Practices**: AI guidance ensured modern development standards

- **Code Quality**: AI suggestions improved code structure and readability
- **User Experience**: AI insights enhanced UI/UX design decisions

### Collaborative Development
- **Human Creativity**: Strategic decisions and project vision
- **AI Assistance**: Technical implementation and optimization
- **Continuous Improvement**: Iterative development with AI feedback
- **Quality Assurance**: AI-assisted testing and validation

## 📝 License

This project is open source. Please check the LICENSE file for details.

## 🙏 Acknowledgments

- **Microsoft** for the Phi-2 model
- **llama.cpp** team for the inference engine
- **Bootstrap** for the UI framework
- **Australian Government** for open data
- **Generative AI** for supporting the development of this project through intelligent code assistance and development guidance

## 📞 Support

If you encounter issues:
1. Check this README
2. Review the troubleshooting section
3. Check GitHub issues
4. Create a new issue with details

---

**Happy Data Discovery! 🎉**
