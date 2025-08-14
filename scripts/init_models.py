import os
import subprocess
import sys
from pathlib import Path
from sentence_transformers import SentenceTransformer

def download_sentence_transformer():
    """Download and cache Sentence Transformer model"""
    print("Downloading Sentence Transformer model...")
    try:
        model = SentenceTransformer('all-MiniLM-L6-v2')
        print("✓ Sentence Transformer model downloaded successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to download Sentence Transformer: {e}")
        return False

def install_ollama():
    """Install Ollama (platform-specific)"""
    print("Installing Ollama...")
    
    import platform
    system = platform.system().lower()
    
    if system == "windows":
        print("Please download and install Ollama from: https://ollama.ai/download/windows")
        return False
    elif system == "darwin":  # macOS
        try:
            subprocess.run(["brew", "install", "ollama"], check=True)
            print("✓ Ollama installed successfully")
            return True
        except:
            print("Please install Homebrew and run: brew install ollama")
            return False
    else:  # Linux
        try:
            subprocess.run(["curl", "-fsSL", "https://ollama.ai/install.sh", "|", "sh"], shell=True, check=True)
            print("✓ Ollama installed successfully")
            return True
        except:
            print("Please install Ollama manually from: https://ollama.ai/download")
            return False

def pull_llm_model():
    """Pull Gemma model"""
    print("Pulling Gemma model...")
    try:
        subprocess.run(["ollama", "pull", "gemma3:1b-it-qat"], check=True)
        print("✓ Gemma model pulled successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to pull Gemma model: {e}")
        print("Please ensure Ollama is installed and running")
        return False

def start_ollama_service():
    """Start Ollama service"""
    print("Starting Ollama service...")
    try:
        subprocess.Popen(["ollama", "serve"])
        print("✓ Ollama service started")
        return True
    except Exception as e:
        print(f"✗ Failed to start Ollama: {e}")
        return False

def main():
    print("Setting up RAG Companion AI models...\n")
    
    success_count = 0
    total_steps = 3
    
    # Step 1: Download Sentence Transformer
    if download_sentence_transformer():
        success_count += 1
    
    # Step 2: Setup Ollama
    if install_ollama():
        if start_ollama_service():
            if pull_llm_model():
                success_count += 2
    
    print(f"\nSetup completed: {success_count}/{total_steps} steps successful")
    
    if success_count == total_steps:
        print("✓ All models are ready!")
    else:
        print("⚠ Some steps failed. Please check the errors above.")

if __name__ == "__main__":
    main()