import os
import subprocess
import sys
from pathlib import Path

def create_env_file():
    """Create .env file from template"""
    env_template = """DATABASE_URL=postgresql://postgres:qwerty12345@localhost:5433/ragbot
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
TAVILY_API_KEY=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
GOOGLE_CLIENT_ID=778657599269-ouflj5id5r0bchm9a8lcko1tskkk4j4f.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=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
SECRET_KEY=kJ8mN2pQ5sT9vY3wZ6aD1fH4jL7nR0uX8bE5hK2mP9sV6yB3eG1iL4oR7tA0cF3h
EMBEDDING_MODEL=all-MiniLM-L6-v2
LLM_MODEL=gemma3:1b-it-qat
OLLAMA_URL=http://localhost:11434
CHUNK_SIZE=512
CHUNK_OVERLAP=50
MAX_CONTEXT_LENGTH=4000
"""
    
    env_path = Path(".env")
    if not env_path.exists():
        with open(env_path, 'w') as f:
            f.write(env_template)
        print("✓ Created .env file with your credentials")
    else:
        print("✓ .env file already exists")

def start_docker_services():
    """Start PostgreSQL and Qdrant containers"""
    print("Starting Docker services...")
    try:
        subprocess.run(["docker-compose", "up", "-d"], check=True)
        print("✓ Docker services started successfully")
        return True
    except subprocess.CalledProcessError:
        print("✗ Failed to start Docker services")
        print("Please ensure Docker is installed and running")
        return False
    except FileNotFoundError:
        print("✗ Docker Compose not found")
        print("Please install Docker and Docker Compose")
        return False

def install_python_dependencies():
    """Install Python dependencies"""
    print("Installing Python dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        print("✓ Python dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("✗ Failed to install Python dependencies")
        return False

def create_directories():
    """Create necessary directories"""
    directories = ["uploads", "logs", "models"]
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    print("✓ Created necessary directories")

def main():
    """Main setup function"""
    print("Setting up RAG Companion AI development environment...\n")
    
    # Step 1: Create directories
    create_directories()
    
    # Step 2: Create .env file
    create_env_file()
    
    # Step 3: Install Python dependencies
    if not install_python_dependencies():
        return
    
    # Step 4: Start Docker services
    if not start_docker_services():
        return
    
    print("\n" + "="*50)
    print("✓ Environment setup completed successfully!")
    print("="*50)
    print("\nNext steps:")
    print("1. Update .env file with your API keys")
    print("2. Run: python scripts/init_models.py")
    print("3. Run: python -m pytest tests/ -v")
    print("4. Run: python backend/main.py")
    print("\nThe API will be available at: http://localhost:8000")
    print("API documentation: http://localhost:8000/docs")

if __name__ == "__main__":
    main()