#!/usr/bin/env python3
"""
Cross-Platform macOS Build Script for RAG Companion AI
Can build macOS applications from Windows/Linux using Docker
"""

import os
import sys
import subprocess
import platform
from pathlib import Path
import json

def check_environment():
    """Check current environment and available tools"""
    current_platform = platform.system()
    print(f"🖥️ Running on: {current_platform} {platform.machine()}")
    
    if current_platform == "Darwin":
        print("✅ Already on macOS - use build_macos_standalone.py instead")
        return "native"
    
    # Check for Docker
    try:
        result = subprocess.run(['docker', '--version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Docker available")
            return "docker"
    except FileNotFoundError:
        pass
    
    print("❌ Docker not available")
    print("💡 Options:")
    print("  1. Install Docker and run this script")
    print("  2. Use a macOS machine to build")
    print("  3. Use GitHub Actions for automated builds")
    
    return None

def create_dockerfile():
    """Create Dockerfile for macOS build environment"""
    print("🐳 Creating Dockerfile for macOS build...")
    
    dockerfile_content = '''# macOS build environment for RAG Companion AI
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    git \\
    curl \\
    wget \\
    build-essential \\
    libssl-dev \\
    libffi-dev \\
    python3-dev \\
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install PyInstaller
RUN pip install pyinstaller>=6.2.0

# Set working directory
WORKDIR /app

# Copy application code
COPY . .

# Build command
CMD ["python", "build_scripts/build_macos_standalone.py"]
'''
    
    with open("Dockerfile.macos", 'w') as f:
        f.write(dockerfile_content)
    
    print("✅ Dockerfile created")

def build_with_docker():
    """Build macOS app using Docker"""
    print("🐳 Building with Docker...")
    
    # Create Dockerfile
    create_dockerfile()
    
    # Build Docker image
    try:
        cmd = [
            "docker", "build",
            "-f", "Dockerfile.macos",
            "-t", "rag-macos-builder",
            "."
        ]
        
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True)
        print("✅ Docker image built")
        
        # Run build in container
        cmd = [
            "docker", "run",
            "--rm",
            "-v", f"{Path.cwd()}:/app",
            "rag-macos-builder"
        ]
        
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True)
        print("✅ macOS build completed in Docker")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Docker build failed: {e}")
        return False

def create_github_workflow():
    """Create GitHub Actions workflow for automated builds"""
    print("📝 Creating GitHub Actions workflow...")
    
    workflow_dir = Path(".github/workflows")
    workflow_dir.mkdir(parents=True, exist_ok=True)
    
    workflow_content = '''name: Build macOS Application

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  release:
    types: [ published ]

jobs:
  build-macos:
    runs-on: macos-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pyinstaller>=6.2.0 dmgbuild create-dmg Pillow
    
    - name: Build macOS application
      run: python build_scripts/build_macos_standalone.py
    
    - name: Upload DMG artifact
      uses: actions/upload-artifact@v3
      with:
        name: RAGCompanionAI-macOS
        path: dist/RAGCompanionAI-Installer.dmg
    
    - name: Create Release
      if: github.event_name == 'release'
      uses: softprops/action-gh-release@v1
      with:
        files: dist/RAGCompanionAI-Installer.dmg
        tag_name: ${{ github.ref }}
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
'''
    
    workflow_file = workflow_dir / "build-macos.yml"
    with open(workflow_file, 'w') as f:
        f.write(workflow_content)
    
    print("✅ GitHub Actions workflow created")
    print(f"📁 Workflow file: {workflow_file}")

def create_build_instructions():
    """Create build instructions for users"""
    print("📝 Creating build instructions...")
    
    instructions = '''# RAG Companion AI - macOS Build Instructions

## Option 1: Build on macOS (Recommended)

1. Clone the repository on a macOS machine
2. Install Python 3.11+
3. Run: `python build_scripts/build_macos_standalone.py`

## Option 2: Build with Docker

1. Install Docker on your system
2. Run: `python build_scripts/build_macos_cross_platform.py`
3. This will create a Docker container and build the app

## Option 3: Automated Build with GitHub Actions

1. Push your code to GitHub
2. Create a release to trigger automated build
3. Download the DMG from the release artifacts

## Prerequisites

- macOS 10.15+ (for native building)
- Python 3.11+
- Docker (for cross-platform building)
- Homebrew (will be installed automatically)

## Output

The build process will create:
- `dist/RAG Companion AI.app` - macOS application bundle
- `dist/RAGCompanionAI-Installer.dmg` - DMG installer
- `dist/install_dependencies.sh` - Dependency installer script

## Installation for End Users

1. Download and mount the DMG file
2. Drag the app to Applications folder
3. Run the installer script to setup dependencies
4. Launch RAG Companion AI
'''
    
    with open("BUILD_INSTRUCTIONS.md", 'w') as f:
        f.write(instructions)
    
    print("✅ Build instructions created")

def main():
    """Main cross-platform build process"""
    print("🍎 RAG Companion AI - Cross-Platform macOS Build")
    print("=" * 60)
    
    # Check environment
    build_method = check_environment()
    
    if build_method == "native":
        print("💡 Use build_macos_standalone.py for native macOS builds")
        return
    
    if build_method == "docker":
        print("🐳 Using Docker for cross-platform build...")
        if build_with_docker():
            print("✅ Build completed successfully!")
        else:
            print("❌ Build failed")
            return
    
    # Create alternative build methods
    print("📝 Creating alternative build methods...")
    create_github_workflow()
    create_build_instructions()
    
    print("\n" + "=" * 60)
    print("📋 Build options created:")
    print("  1. GitHub Actions workflow: .github/workflows/build-macos.yml")
    print("  2. Build instructions: BUILD_INSTRUCTIONS.md")
    print("  3. Docker build: Dockerfile.macos")
    
    print("\n💡 To build on macOS:")
    print("  python build_scripts/build_macos_standalone.py")
    
    print("\n💡 To use GitHub Actions:")
    print("  1. Push to GitHub")
    print("  2. Create a release")
    print("  3. Download DMG from artifacts")

if __name__ == "__main__":
    main()
