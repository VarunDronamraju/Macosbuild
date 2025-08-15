# RAG Companion AI - macOS Build & Installation Guide

## 🍎 Complete macOS Application with One-Step Installation

This guide covers building a complete macOS application with all dependencies, services, and API keys included for a seamless user experience.

## 🚀 Quick Start

### For Users (One-Step Installation)

1. **Download the DMG file** from GitHub Releases
2. **Double-click** `RAGCompanionAI-Installer.dmg`
3. **Drag** the app to Applications folder
4. **Run** the installation script: `./install.sh`
5. **Launch** RAG Companion AI from Applications

### For Developers (Build from Source)

```bash
# Clone the repository
git clone https://github.com/yourusername/RAGCompanionAI.git
cd RAGCompanionAI

# Run the complete build
python build_scripts/build_all.py macos
```

## 📋 What's Included

### ✅ Complete Application Bundle
- **RAG Companion AI Desktop App** (PyQt6-based)
- **FastAPI Backend** (embedded)
- **All Python Dependencies** (packaged with PyInstaller)
- **Pre-configured API Keys** (Tavily, Google OAuth)
- **Local AI Models** (Ollama integration)

### ✅ System Services (Auto-installed)
- **PostgreSQL Database** (port 5432)
- **Qdrant Vector Database** (port 6333)
- **Ollama AI Service** (port 11434)
- **Homebrew Package Manager** (if needed)

### ✅ Pre-configured Components
- **Database Schema** (auto-created)
- **Vector Collections** (documents, chunks)
- **AI Models** (gemma3:1b-it-qat, all-MiniLM-L6-v2)
- **Environment Configuration** (.env file)
- **Launch Scripts** (auto-start capability)

## 🔧 GitHub Workflow

### Automated Build Process

The GitHub workflow (`.github/workflows/build-macos.yml`) automatically:

1. **Sets up macOS environment** with Python 3.11
2. **Installs system dependencies** (Homebrew, PostgreSQL, Qdrant)
3. **Downloads AI models** (Ollama models)
4. **Builds application bundle** with PyInstaller
5. **Creates DMG installer** with create-dmg
6. **Generates installation scripts** for one-step setup
7. **Uploads artifacts** for distribution

### Workflow Triggers

- **Push to main/develop** - Automatic build
- **Pull requests** - Build validation
- **Manual dispatch** - Custom version builds
- **Tags** - Release creation

### Build Artifacts

- `RAG Companion AI.app` - Application bundle
- `RAGCompanionAI-Installer.dmg` - DMG installer
- `install.sh` - One-step installation script
- `README.md` - Installation instructions

## 🛠️ Build Configuration

### PyInstaller Spec File

The enhanced spec file (`dist_configs/pyinstaller_macos_complete.spec`) includes:

```python
# Comprehensive data files
datas = [
    ('frontend/resources', 'frontend/resources'),
    ('backend', 'backend'),
    ('shared', 'shared'),
    ('resources/models', 'resources/models'),
    ('resources/icons', 'resources/icons'),
    ('.env', '.'),
    ('requirements.txt', '.'),
]

# All required imports
hiddenimports = [
    'sentence_transformers', 'transformers', 'torch',
    'qdrant_client', 'psycopg2', 'sqlalchemy',
    'fastapi', 'uvicorn', 'starlette',
    'PyQt6', 'PyQt6.QtCore', 'PyQt6.QtWidgets',
    'ollama', 'tavily', 'google.auth',
    # ... and many more
]

# macOS-specific configuration
info_plist = {
    'CFBundleName': 'RAG Companion AI',
    'CFBundleIdentifier': 'ai.ragcompanion.desktop',
    'LSMinimumSystemVersion': '10.15.0',
    'NSHighResolutionCapable': True,
    # ... comprehensive macOS integration
}
```

### Setup Script

The complete setup script (`scripts/setup_macos_complete.py`) handles:

```python
class MacOSSetup:
    def check_system_requirements(self):
        # macOS version, disk space, RAM
    
    def install_homebrew(self):
        # Package manager installation
    
    def install_postgresql(self):
        # Database setup and configuration
    
    def install_qdrant(self):
        # Vector database setup
    
    def install_ollama(self):
        # AI models download and setup
    
    def create_environment_file(self):
        # Configuration with API keys
    
    def create_launch_script(self):
        # Application startup script
    
    def create_plist_file(self):
        # macOS LaunchAgent for auto-start
```

## 🔑 Pre-configured API Keys

The application includes these API keys for immediate use:

```bash
# External APIs
TAVILY_API_KEY=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
GOOGLE_CLIENT_ID=778657599269-ouflj5id5r0bchm9a8lcko1tskkk4j4f.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=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

# Local Services
OLLAMA_URL=http://localhost:11434
QDRANT_URL=http://localhost:6333
DATABASE_URL=postgresql://postgres@localhost:5432/ragbot
```

## 📱 Installation Process

### Step 1: System Requirements Check

```bash
# macOS 10.15+ required
# 8GB RAM minimum (16GB recommended)
# 10GB free disk space
# Internet connection for initial setup
```

### Step 2: Automated Installation

```bash
# The install.sh script automatically:
./install.sh

# 1. Installs Homebrew (if needed)
# 2. Installs PostgreSQL and starts service
# 3. Installs Qdrant vector database
# 4. Downloads and installs Ollama
# 5. Downloads AI models (gemma3:1b-it-qat, all-MiniLM-L6-v2)
# 6. Creates database and collections
# 7. Configures environment
# 8. Installs application to /Applications
```

### Step 3: Launch Application

```bash
# Option 1: Double-click from Applications
# Option 2: Use Spotlight (Cmd+Space)
# Option 3: Run from terminal
open "/Applications/RAG Companion AI.app"
```

## 🔧 Service Management

### Check Service Status

```bash
# PostgreSQL
brew services list | grep postgresql

# Qdrant
curl http://localhost:6333/health

# Ollama
curl http://localhost:11434/api/tags
```

### Start/Stop Services

```bash
# Start all services
brew services start postgresql@14
qdrant &
ollama serve &

# Stop all services
brew services stop postgresql@14
pkill qdrant
pkill ollama
```

### View Logs

```bash
# Application logs
tail -f ~/Library/Logs/RAG\ Companion\ AI/app.log

# Setup logs
tail -f ~/Library/Logs/RAG\ Companion\ AI/setup.log

# Service logs
tail -f ~/Library/Logs/RAG\ Companion\ AI/qdrant.log
tail -f ~/Library/Logs/RAG\ Companion\ AI/ollama.log
```

## 🐛 Troubleshooting

### Common Issues

1. **Services not starting**
   ```bash
   # Check if ports are in use
   lsof -i :5432  # PostgreSQL
   lsof -i :6333  # Qdrant
   lsof -i :11434 # Ollama
   ```

2. **Permission issues**
   ```bash
   # Fix Homebrew permissions
   sudo chown -R $(whoami) /usr/local/bin /usr/local/lib
   ```

3. **Model download failures**
   ```bash
   # Manual model download
   ollama pull gemma3:1b-it-qat
   ollama pull all-MiniLM-L6-v2
   ```

4. **Database connection issues**
   ```bash
   # Reset PostgreSQL
   brew services stop postgresql@14
   brew services start postgresql@14
   createdb ragbot
   ```

### Debug Mode

```bash
# Run with console output
cd "/Applications/RAG Companion AI.app/Contents/MacOS"
./RAGCompanionAI --debug
```

## 📦 Distribution

### Creating Releases

1. **Tag a release** in GitHub
2. **Workflow automatically** creates release
3. **Uploads artifacts** (DMG, scripts, docs)
4. **Generates release notes** with changelog

### Manual Distribution

```bash
# Build artifacts are in dist/
ls -la dist/
# RAG Companion AI.app
# RAGCompanionAI-Installer.dmg
# install.sh
# README.md
```

## 🔄 Continuous Integration

### GitHub Actions Features

- **Automatic builds** on push/PR
- **Cross-platform testing** (macOS runners)
- **Dependency caching** for faster builds
- **Artifact storage** for 30 days
- **Release automation** on tags

### Build Matrix

```yaml
# Supports multiple configurations
- macOS 12 (latest)
- Python 3.11
- PyInstaller 6.2.0
- All dependencies included
```

## 📊 Performance Optimization

### Bundle Size Optimization

- **Excluded unnecessary modules** (tkinter, matplotlib, etc.)
- **Compressed resources** where possible
- **Minimal dependencies** included
- **UPX disabled** for macOS compatibility

### Runtime Performance

- **Local AI models** (no external API calls)
- **Embedded vector database** (Qdrant)
- **Local PostgreSQL** (no cloud dependencies)
- **Optimized imports** and lazy loading

## 🔒 Security Considerations

### API Key Management

- **Keys embedded** in application bundle
- **Environment variables** for configuration
- **Local-only services** (no external dependencies)
- **Secure storage** using macOS keychain

### Permissions

- **Minimal permissions** requested
- **Local file access** only
- **Network access** for model downloads only
- **No system-wide changes** beyond services

## 📈 Future Enhancements

### Planned Features

- **Universal binary** (Intel + Apple Silicon)
- **App Store distribution** (sandboxed)
- **Auto-updates** mechanism
- **Cloud sync** options
- **Advanced security** features

### Build Improvements

- **Multi-stage builds** for smaller artifacts
- **Differential updates** for releases
- **Automated testing** in CI/CD
- **Performance profiling** integration

---

## 🎉 Success!

Your RAG Companion AI macOS application is now ready for distribution with:

- ✅ **One-step installation** for end users
- ✅ **All dependencies included** (no external setup)
- ✅ **Pre-configured API keys** (immediate use)
- ✅ **Local AI models** (offline capability)
- ✅ **Professional packaging** (DMG installer)
- ✅ **Automated builds** (GitHub Actions)

The application provides a complete RAG (Retrieval-Augmented Generation) experience with document processing, semantic search, and AI-powered conversations, all packaged as a native macOS application.
