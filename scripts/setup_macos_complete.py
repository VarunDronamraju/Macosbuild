#!/usr/bin/env python3
"""
Complete macOS Setup Script for RAG Companion AI
One-step installation with all dependencies and services
"""

import os
import sys
import subprocess
import shutil
import json
import time
import requests
from pathlib import Path
import platform

class MacOSSetup:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.home_dir = Path.home()
        self.app_support = self.home_dir / "Library" / "Application Support" / "RAG Companion AI"
        self.logs_dir = self.home_dir / "Library" / "Logs" / "RAG Companion AI"
        
        # Create necessary directories
        self.app_support.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Configuration
        self.config = {
            'postgresql_port': 5432,
            'qdrant_port': 6333,
            'ollama_port': 11434,
            'app_port': 8000
        }
    
    def log(self, message, level="INFO"):
        """Log messages to file and console"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {level}: {message}"
        print(log_message)
        
        # Write to log file
        log_file = self.logs_dir / "setup.log"
        with open(log_file, "a") as f:
            f.write(log_message + "\n")
    
    def run_command(self, command, check=True, capture_output=True):
        """Run shell command with logging"""
        self.log(f"Running: {command}")
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                check=check, 
                capture_output=capture_output,
                text=True
            )
            if result.stdout:
                self.log(f"Output: {result.stdout.strip()}")
            return result
        except subprocess.CalledProcessError as e:
            self.log(f"Error: {e.stderr}", "ERROR")
            if check:
                raise
            return e
    
    def check_system_requirements(self):
        """Check if system meets requirements"""
        self.log("Checking system requirements...")
        
        # Check macOS version
        macos_version = platform.mac_ver()[0]
        self.log(f"macOS Version: {macos_version}")
        
        if float(macos_version.split('.')[0]) < 10.15:
            raise SystemError("macOS 10.15 (Catalina) or later is required")
        
        # Check available disk space
        statvfs = os.statvfs(self.home_dir)
        free_space_gb = (statvfs.f_frsize * statvfs.f_bavail) / (1024**3)
        self.log(f"Available disk space: {free_space_gb:.1f} GB")
        
        if free_space_gb < 10:
            raise SystemError("At least 10GB free disk space is required")
        
        # Check RAM
        try:
            result = self.run_command("sysctl hw.memsize", check=False)
            if result.returncode == 0:
                ram_gb = int(result.stdout.split()[-1]) / (1024**3)
                self.log(f"Total RAM: {ram_gb:.1f} GB")
                if ram_gb < 8:
                    self.log("Warning: Less than 8GB RAM detected", "WARNING")
        except:
            self.log("Could not determine RAM size", "WARNING")
        
        self.log("System requirements check passed")
    
    def install_homebrew(self):
        """Install Homebrew if not present"""
        self.log("Checking for Homebrew...")
        
        if shutil.which("brew"):
            self.log("Homebrew is already installed")
            return
        
        self.log("Installing Homebrew...")
        install_script = '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
        self.run_command(install_script)
        
        # Add Homebrew to PATH
        brew_path = "/opt/homebrew/bin" if platform.machine() == "arm64" else "/usr/local/bin"
        if brew_path not in os.environ["PATH"]:
            os.environ["PATH"] = f"{brew_path}:{os.environ['PATH']}"
    
    def install_postgresql(self):
        """Install and configure PostgreSQL"""
        self.log("Installing PostgreSQL...")
        
        # Install PostgreSQL
        self.run_command("brew install postgresql@14")
        
        # Start PostgreSQL service
        self.run_command("brew services start postgresql@14")
        
        # Wait for service to start
        time.sleep(5)
        
        # Create database
        self.run_command("createdb ragbot", check=False)
        
        # Create user if needed
        self.run_command("createuser -s postgres", check=False)
        
        self.log("PostgreSQL installed and configured")
    
    def install_qdrant(self):
        """Install and configure Qdrant"""
        self.log("Installing Qdrant...")
        
        # Install Qdrant directly from official source
        self.run_command("curl -fsSL https://github.com/qdrant/qdrant/releases/download/v1.7.4/qdrant-v1.7.4-x86_64-apple-darwin.tar.gz -o qdrant.tar.gz")
        self.run_command("tar -xzf qdrant.tar.gz")
        self.run_command("sudo mv qdrant /usr/local/bin/")
        self.run_command("chmod +x /usr/local/bin/qdrant")
        self.run_command("rm qdrant.tar.gz")
        
        # Create Qdrant data directory
        qdrant_data = self.app_support / "qdrant"
        qdrant_data.mkdir(exist_ok=True)
        
        # Start Qdrant
        qdrant_cmd = f"qdrant --storage-path {qdrant_data} --http-port {self.config['qdrant_port']}"
        self.run_command(f"nohup {qdrant_cmd} > {self.logs_dir}/qdrant.log 2>&1 &")
        
        # Wait for Qdrant to start
        time.sleep(5)
        
        # Create collections
        self.create_qdrant_collections()
        
        self.log("Qdrant installed and configured")
    
    def create_qdrant_collections(self):
        """Create Qdrant collections"""
        self.log("Creating Qdrant collections...")
        
        collections = [
            {
                "name": "documents",
                "vector_size": 384,
                "distance": "Cosine"
            },
            {
                "name": "chunks",
                "vector_size": 384,
                "distance": "Cosine"
            }
        ]
        
        for collection in collections:
            url = f"http://localhost:{self.config['qdrant_port']}/collections/{collection['name']}"
            data = {
                "vectors": {
                    "size": collection["vector_size"],
                    "distance": collection["distance"]
                }
            }
            
            try:
                response = requests.put(url, json=data, timeout=10)
                if response.status_code in [200, 201]:
                    self.log(f"Created collection: {collection['name']}")
                else:
                    self.log(f"Collection {collection['name']} already exists or error: {response.status_code}")
            except Exception as e:
                self.log(f"Error creating collection {collection['name']}: {e}", "WARNING")
    
    def install_ollama(self):
        """Install and configure Ollama"""
        self.log("Installing Ollama...")
        
        # Download Ollama
        ollama_url = "https://ollama.ai/download/ollama-darwin-amd64"
        ollama_path = "/usr/local/bin/ollama"
        
        self.run_command(f"curl -fsSL {ollama_url} -o {ollama_path}")
        self.run_command(f"chmod +x {ollama_path}")
        
        # Start Ollama service
        self.run_command(f"nohup ollama serve > {self.logs_dir}/ollama.log 2>&1 &")
        
        # Wait for service to start
        time.sleep(10)
        
        # Pull required models
        models = ["gemma3:1b-it-qat", "all-MiniLM-L6-v2"]
        for model in models:
            self.log(f"Downloading model: {model}")
            self.run_command(f"ollama pull {model}")
        
        self.log("Ollama installed and configured")
    
    def create_environment_file(self):
        """Create environment configuration file"""
        self.log("Creating environment configuration...")
        
        env_content = f"""# RAG Companion AI Environment Configuration
# Generated on {time.strftime("%Y-%m-%d %H:%M:%S")}

# Database
DATABASE_URL=postgresql://postgres@localhost:{self.config['postgresql_port']}/ragbot

# Vector Database
QDRANT_URL=http://localhost:{self.config['qdrant_port']}
QDRANT_API_KEY=

# AI Models
EMBEDDING_MODEL=all-MiniLM-L6-v2
LLM_MODEL=gemma3:1b-it-qat
OLLAMA_URL=http://localhost:{self.config['ollama_port']}

# External APIs
TAVILY_API_KEY=${TAVILY_API_KEY:-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}
GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID:-778657599269-ouflj5id5r0bchm9a8lcko1tskkk4j4f.apps.googleusercontent.com}
GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET:-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}

# Application
SECRET_KEY=${SECRET_KEY:-kJ8mN2pQ5sT9vY3wZ6aD1fH4jL7nR0uX8bE5hK2mP9sV6yB3eG1iL4oR7tA0cF3h}
UPLOAD_DIR={self.app_support}/uploads
CHUNK_SIZE=512
CHUNK_OVERLAP=50
MAX_CONTEXT_LENGTH=4000

# Logging
LOG_LEVEL=INFO
LOG_FILE={self.logs_dir}/app.log
"""
        
        env_file = self.project_root / ".env"
        with open(env_file, "w") as f:
            f.write(env_content)
        
        self.log("Environment configuration created")
    
    def create_launch_script(self):
        """Create application launch script"""
        self.log("Creating launch script...")
        
        launch_script = f"""#!/bin/bash
# RAG Companion AI Launch Script

# Set environment variables
export RAG_COMPANION_HOME="{self.app_support}"
export RAG_COMPANION_LOGS="{self.logs_dir}"

# Check if services are running
echo "Checking services..."

# Check PostgreSQL
if ! pg_isready -h localhost -p {self.config['postgresql_port']} > /dev/null 2>&1; then
    echo "Starting PostgreSQL..."
    brew services start postgresql@14
    sleep 5
fi

# Check Qdrant
if ! curl -s http://localhost:{self.config['qdrant_port']}/health > /dev/null; then
    echo "Starting Qdrant..."
    qdrant --storage-path "{self.app_support}/qdrant" --http-port {self.config['qdrant_port']} &
    sleep 5
fi

# Check Ollama
if ! curl -s http://localhost:{self.config['ollama_port']}/api/tags > /dev/null; then
    echo "Starting Ollama..."
    ollama serve &
    sleep 10
fi

echo "All services are running"
echo "Launching RAG Companion AI..."

# Launch the application
cd "{self.project_root}"
python frontend/main.py
"""
        
        launch_file = self.app_support / "launch.sh"
        with open(launch_file, "w") as f:
            f.write(launch_script)
        
        # Make executable
        self.run_command(f"chmod +x {launch_file}")
        
        self.log("Launch script created")
    
    def create_plist_file(self):
        """Create LaunchAgent plist file for auto-start"""
        self.log("Creating LaunchAgent configuration...")
        
        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>ai.ragcompanion.desktop</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>{self.app_support}/launch.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{self.logs_dir}/launch.log</string>
    <key>StandardErrorPath</key>
    <string>{self.logs_dir}/launch_error.log</string>
</dict>
</plist>
"""
        
        plist_file = self.home_dir / "Library" / "LaunchAgents" / "ai.ragcompanion.desktop.plist"
        plist_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(plist_file, "w") as f:
            f.write(plist_content)
        
        # Load the LaunchAgent
        self.run_command(f"launchctl load {plist_file}")
        
        self.log("LaunchAgent configured")
    
    def test_services(self):
        """Test all services"""
        self.log("Testing services...")
        
        # Test PostgreSQL
        try:
            result = self.run_command(f"pg_isready -h localhost -p {self.config['postgresql_port']}", check=False)
            if result.returncode == 0:
                self.log("✅ PostgreSQL is running")
            else:
                self.log("❌ PostgreSQL is not responding", "ERROR")
        except:
            self.log("❌ PostgreSQL test failed", "ERROR")
        
        # Test Qdrant
        try:
            response = requests.get(f"http://localhost:{self.config['qdrant_port']}/health", timeout=5)
            if response.status_code == 200:
                self.log("✅ Qdrant is running")
            else:
                self.log("❌ Qdrant is not responding", "ERROR")
        except:
            self.log("❌ Qdrant test failed", "ERROR")
        
        # Test Ollama
        try:
            response = requests.get(f"http://localhost:{self.config['ollama_port']}/api/tags", timeout=5)
            if response.status_code == 200:
                self.log("✅ Ollama is running")
            else:
                self.log("❌ Ollama is not responding", "ERROR")
        except:
            self.log("❌ Ollama test failed", "ERROR")
    
    def setup_complete(self):
        """Final setup completion"""
        self.log("Setup completed successfully!")
        
        summary = f"""
🎉 RAG Companion AI Setup Complete!

📁 Application Support: {self.app_support}
📋 Logs Directory: {self.logs_dir}
🚀 Launch Script: {self.app_support}/launch.sh

🔧 Services Running:
   - PostgreSQL (port {self.config['postgresql_port']})
   - Qdrant (port {self.config['qdrant_port']})
   - Ollama (port {self.config['ollama_port']})

📱 To launch the application:
   - Double-click the app bundle, or
   - Run: {self.app_support}/launch.sh

🔧 To stop services:
   brew services stop postgresql@14
   pkill qdrant
   pkill ollama

📋 For logs and troubleshooting:
   tail -f {self.logs_dir}/setup.log
"""
        
        print(summary)
        
        # Save setup summary
        summary_file = self.app_support / "setup_summary.txt"
        with open(summary_file, "w") as f:
            f.write(summary)
    
    def run_setup(self):
        """Run complete setup process"""
        try:
            self.log("Starting RAG Companion AI setup...")
            
            self.check_system_requirements()
            self.install_homebrew()
            self.install_postgresql()
            self.install_qdrant()
            self.install_ollama()
            self.create_environment_file()
            self.create_launch_script()
            self.create_plist_file()
            self.test_services()
            self.setup_complete()
            
        except Exception as e:
            self.log(f"Setup failed: {e}", "ERROR")
            raise

def main():
    """Main setup function"""
    print("🚀 RAG Companion AI - macOS Complete Setup")
    print("=" * 50)
    
    setup = MacOSSetup()
    setup.run_setup()

if __name__ == "__main__":
    main()
