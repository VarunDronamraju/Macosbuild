#!/usr/bin/env python3
"""
GitHub Setup Script for RAG Companion AI
Helps set up the repository and push to GitHub
"""

import os
import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def check_git_status():
    """Check if git is initialized and has remote"""
    try:
        # Check if git is initialized
        result = subprocess.run("git status", shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Git repository not initialized")
            return False
        
        # Check if remote exists
        result = subprocess.run("git remote -v", shell=True, capture_output=True, text=True)
        if "origin" not in result.stdout:
            print("❌ No remote origin found")
            return False
            
        print("✅ Git repository is properly configured")
        return True
        
    except Exception as e:
        print(f"❌ Error checking git status: {e}")
        return False

def setup_git():
    """Set up git repository"""
    print("🔧 Setting up Git repository...")
    
    # Initialize git if not already done
    if not Path(".git").exists():
        if not run_command("git init", "Initializing git repository"):
            return False
    
    # Add remote origin
    remote_url = "https://github.com/VarunDronamraju/Macosbuild.git"
    if not run_command(f'git remote add origin "{remote_url}"', "Adding remote origin"):
        # Try to set URL if remote already exists
        run_command(f'git remote set-url origin "{remote_url}"', "Updating remote URL")
    
    return True

def create_gitignore():
    """Create .gitignore file"""
    gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual environments
venv/
env/
ENV/
env.bak/
venv.bak/

# PyInstaller
*.manifest
*.spec

# Logs
*.log
logs/

# Environment variables
.env
.env.local
.env.production

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Build artifacts
dist/
build/
*.dmg
*.exe
*.app

# Temporary files
*.tmp
*.temp
temp/
tmp/

# Database
*.db
*.sqlite
*.sqlite3

# Models (large files)
models/
*.bin
*.safetensors

# Docker
.dockerignore
"""
    
    with open(".gitignore", "w") as f:
        f.write(gitignore_content)
    
    print("✅ .gitignore created")

def commit_and_push():
    """Commit and push changes"""
    print("📤 Committing and pushing changes...")
    
    # Add all files
    if not run_command("git add .", "Adding files to git"):
        return False
    
    # Commit
    commit_message = "Initial commit: RAG Companion AI macOS application"
    if not run_command(f'git commit -m "{commit_message}"', "Committing changes"):
        return False
    
    # Push to main branch
    if not run_command("git push -u origin main", "Pushing to GitHub"):
        return False
    
    return True

def create_initial_release():
    """Create initial release instructions"""
    print("\n" + "="*60)
    print("🎉 Repository setup complete!")
    print("\n📋 Next steps to create your first DMG:")
    print("1. Go to your GitHub repository: https://github.com/VarunDronamraju/Macosbuild")
    print("2. Check the Actions tab to see the build progress")
    print("3. Once the build completes, download the DMG from the Actions artifacts")
    print("4. To create a proper release:")
    print("   - Go to Releases tab")
    print("   - Click 'Create a new release'")
    print("   - Tag version: v1.0.0")
    print("   - Title: RAG Companion AI v1.0.0")
    print("   - Upload the DMG file from Actions artifacts")
    print("   - Publish the release")
    print("\n🔗 Your repository will be available at:")
    print("   https://github.com/VarunDronamraju/Macosbuild")
    print("\n📱 Users can download the DMG from:")
    print("   https://github.com/VarunDronamraju/Macosbuild/releases")

def main():
    """Main setup process"""
    print("🚀 RAG Companion AI - GitHub Setup")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not Path("frontend").exists() or not Path("backend").exists():
        print("❌ Please run this script from the project root directory")
        sys.exit(1)
    
    # Create .gitignore
    create_gitignore()
    
    # Setup git
    if not setup_git():
        print("❌ Failed to setup git repository")
        sys.exit(1)
    
    # Check git status
    if not check_git_status():
        print("❌ Git repository not properly configured")
        sys.exit(1)
    
    # Commit and push
    if not commit_and_push():
        print("❌ Failed to push to GitHub")
        sys.exit(1)
    
    # Create release instructions
    create_initial_release()

if __name__ == "__main__":
    main()
