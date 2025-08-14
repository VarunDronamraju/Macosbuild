# RAG Companion AI - macOS Application

🤖 **A powerful AI-powered document search and chat application for macOS**

## 🚀 Quick Start

### For macOS Users:
1. **Download the DMG**: Go to [Releases](https://github.com/VarunDronamraju/Macosbuild/releases) and download the latest `RAGCompanionAI-Installer.dmg`
2. **Install**: Mount the DMG and drag the app to Applications
3. **Setup Dependencies**: Run the installer script to setup all required services
4. **Launch**: Start RAG Companion AI and enjoy!

### For Developers:
```bash
# Clone the repository
git clone https://github.com/VarunDronamraju/Macosbuild.git
cd Macosbuild

# Install dependencies
pip install -r requirements.txt

# Run the application
python frontend/main.py
```

## ✨ Features

### 🔍 **Local Document Search**
- Upload and process PDF, DOCX, and TXT files
- AI-powered semantic search through your documents
- Fast vector-based retrieval using Qdrant
- Support for multiple document formats

### 🌐 **Web Search Integration**
- Tavily-powered web search capabilities
- Real-time information retrieval
- Seamless integration with local search results

### 💬 **Intelligent Chat Interface**
- Chat with your documents using AI
- Context-aware responses
- Support for multiple AI models (Ollama integration)

### 🔒 **Secure Authentication**
- Google OAuth integration
- Secure user management
- Protected document access

### 📱 **Native macOS Experience**
- Beautiful PyQt6-based interface
- Native macOS app bundle
- Automatic updates and dependency management

## 🏗️ Architecture

```
RAG Companion AI
├── Frontend (PyQt6)
│   ├── Chat Interface
│   ├── Document Upload
│   └── Search Results
├── Backend (FastAPI)
│   ├── Document Processing
│   ├── Vector Search (Qdrant)
│   ├── AI Integration (Ollama)
│   └── Web Search (Tavily)
└── Database (PostgreSQL)
    ├── User Management
    └── Document Metadata
```

## 🛠️ Technology Stack

- **Frontend**: PyQt6, Python
- **Backend**: FastAPI, SQLAlchemy
- **Database**: PostgreSQL
- **Vector Store**: Qdrant
- **AI Models**: Ollama (Gemma3)
- **Web Search**: Tavily API
- **Authentication**: Google OAuth
- **Document Processing**: PyPDF2, python-docx

## 📦 Installation

### Prerequisites
- macOS 10.15 or later
- Docker Desktop
- Homebrew (will be installed automatically)

### Automatic Installation
The DMG installer includes an automated setup script that will:
1. Install Homebrew (if not present)
2. Install Docker Desktop
3. Install Ollama
4. Download required AI models
5. Start all necessary services

### Manual Installation
If you prefer manual installation:

```bash
# Install Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Docker
brew install --cask docker

# Install Ollama
brew install ollama

# Start services
docker-compose up -d

# Download AI model
ollama pull gemma3:1b-it-qat
```

## 🔧 Development

### Building from Source
```bash
# Clone repository
git clone https://github.com/VarunDronamraju/Macosbuild.git
cd Macosbuild

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run development server
python frontend/main.py
```

### Building macOS DMG
The GitHub Actions workflow automatically builds the DMG file on every push. To trigger a build:

1. Push your changes to the repository
2. Go to Actions tab in GitHub
3. Download the DMG from the latest workflow run

## 📁 Project Structure

```
Macosbuild/
├── frontend/                 # PyQt6 GUI application
│   ├── main.py              # Main application entry point
│   ├── chat_widget.py       # Chat interface
│   ├── auth_dialog.py       # Authentication dialog
│   └── resources/           # UI resources
├── backend/                 # FastAPI backend
│   ├── main.py             # API server
│   ├── auth.py             # Authentication
│   ├── documents.py        # Document processing
│   └── rag.py              # RAG implementation
├── shared/                  # Shared models and utilities
├── dist_configs/           # PyInstaller configurations
├── build_scripts/          # Build automation scripts
├── requirements.txt        # Python dependencies
└── docker-compose.yml      # Docker services
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/VarunDronamraju/Macosbuild/issues)
- **Discussions**: [GitHub Discussions](https://github.com/VarunDronamraju/Macosbuild/discussions)
- **Releases**: [GitHub Releases](https://github.com/VarunDronamraju/Macosbuild/releases)

## 🎯 Roadmap

- [ ] Windows and Linux support
- [ ] Mobile app versions
- [ ] Advanced document analytics
- [ ] Multi-language support
- [ ] Cloud sync capabilities
- [ ] Plugin system

---

**Made with ❤️ for the AI community**
