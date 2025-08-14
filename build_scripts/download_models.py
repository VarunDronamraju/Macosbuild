# =============================================================================
# FILE 2: build_scripts/download_models.py
# =============================================================================

"""
Download AI models for offline packaging
This ensures the app works without internet
"""

import os
import sys
import shutil
from pathlib import Path
import subprocess

def setup_models_directory():
    """Setup models directory structure"""
    models_dir = Path("resources/models")
    models_dir.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories
    (models_dir / "sentence_transformers").mkdir(exist_ok=True)
    (models_dir / "ollama").mkdir(exist_ok=True)
    
    return models_dir

def download_sentence_transformer():
    """Download sentence transformer model for offline use"""
    print("📥 Downloading Sentence Transformer model...")
    
    try:
        from sentence_transformers import SentenceTransformer
        
        models_dir = Path("resources/models/sentence_transformers")
        model_path = models_dir / "all-MiniLM-L6-v2"
        
        if model_path.exists():
            print("  ✅ Model already exists, skipping download")
            return True
        
        # Download model
        print("  - Downloading all-MiniLM-L6-v2...")
        model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Save to our models directory
        model.save(str(model_path))
        
        print(f"  ✅ Model saved to: {model_path}")
        return True
        
    except ImportError:
        print("  ❌ sentence-transformers not installed")
        print("  Run: pip install sentence-transformers")
        return False
    except Exception as e:
        print(f"  ❌ Failed to download model: {e}")
        return False

def check_ollama_installation():
    """Check if Ollama is installed and download model"""
    print("🦙 Checking Ollama installation...")
    
    try:
        # Check if ollama is installed
        result = subprocess.run(['ollama', '--version'], 
                              capture_output=True, text=True)
        
        if result.returncode != 0:
            print("  ❌ Ollama not installed")
            print("  Please install from: https://ollama.ai")
            return False
        
        print(f"  ✅ Ollama version: {result.stdout.strip()}")
        
        # Check if model is already available
        list_result = subprocess.run(['ollama', 'list'], 
                                   capture_output=True, text=True)
        
        if 'gemma3:1b-it-qat' in list_result.stdout:
            print("  ✅ gemma3:1b-it-qat model already available")
            return True
        
        # Download the model
        print("  - Downloading gemma3:1b-it-qat model...")
        pull_result = subprocess.run(['ollama', 'pull', 'gemma3:1b-it-qat'],
                                   capture_output=True, text=True)
        
        if pull_result.returncode == 0:
            print("  ✅ Ollama model downloaded successfully")
            return True
        else:
            print(f"  ❌ Failed to download model: {pull_result.stderr}")
            return False
            
    except FileNotFoundError:
        print("  ❌ Ollama not found in PATH")
        print("  Please install from: https://ollama.ai")
        return False
    except Exception as e:
        print(f"  ❌ Error checking Ollama: {e}")
        return False

def create_models_info():
    """Create info file about models"""
    models_dir = Path("resources/models")
    
    info_content = """# AI Models for RAG Companion AI

This directory contains the AI models used by the application:

## Sentence Transformer Model
- **Model**: all-MiniLM-L6-v2
- **Purpose**: Document embedding and semantic search
- **Location**: sentence_transformers/all-MiniLM-L6-v2/
- **Size**: ~90MB

## Ollama Language Model  
- **Model**: gemma3:1b-it-qat
- **Purpose**: Local language model for RAG responses
- **Managed by**: Ollama (separate installation)
- **Size**: ~1GB

## Notes
- These models enable offline functionality
- All models are downloaded during build process
- No internet required after installation
"""
    
    with open(models_dir / "README.md", 'w') as f:
        f.write(info_content)

def main():
    """Main model download function"""
    print("🤖 Downloading AI models for RAG Companion AI...")
    print("-" * 60)
    
    # Setup directory
    setup_models_directory()
    
    # Download models
    sentence_success = download_sentence_transformer()
    ollama_success = check_ollama_installation()
    
    # Create info file
    create_models_info()
    
    print("-" * 60)
    if sentence_success and ollama_success:
        print("🎉 All models downloaded successfully!")
        print("✅ Ready for packaging")
    else:
        print("⚠️ Some models failed to download")
        if not sentence_success:
            print("❌ Sentence transformer model missing")
        if not ollama_success:
            print("❌ Ollama model missing")
        print("📝 Check errors above and retry")

if __name__ == "__main__":
    main()