#!/usr/bin/env python3
"""
Setup script for RAG Desktop Application Frontend
Installs required dependencies and sets up the frontend environment
"""

import subprocess
import sys
import os
from pathlib import Path

def install_package(package):
    """Install a package using pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except subprocess.CalledProcessError:
        return False

def main():
    """Main setup function"""
    print("Setting up RAG Desktop Application Frontend...")
    print("=" * 50)
    
    # Essential packages
    essential_packages = [
        "PyQt6>=6.4.0",
        "requests>=2.28.0",
        "urllib3>=1.26.0"
    ]
    
    # Optional packages
    optional_packages = [
        "markdown>=3.4.0",
        "Pygments>=2.14.0",
        "PyQt6-WebEngine>=6.4.0"
    ]
    
    # Install essential packages
    print("\nInstalling essential packages...")
    for package in essential_packages:
        print(f"Installing {package}...")
        if install_package(package):
            print(f"✅ {package} installed successfully")
        else:
            print(f"❌ Failed to install {package}")
            print("This is a critical dependency. Please install manually.")
            return False
    
    # Install optional packages
    print("\nInstalling optional packages...")
    for package in optional_packages:
        print(f"Installing {package}...")
        if install_package(package):
            print(f"✅ {package} installed successfully")
        else:
            print(f"⚠️  Failed to install {package} (optional)")
            if "WebEngine" in package:
                print("  Note: WebEngine is optional but recommended for full OAuth support")
            elif "markdown" in package:
                print("  Note: Markdown is optional but recommended for rich text chat")
    
    # Create frontend directory structure
    print("\nSetting up directory structure...")
    frontend_dir = Path("frontend")
    frontend_dir.mkdir(exist_ok=True)
    
    resources_dir = frontend_dir / "resources"
    resources_dir.mkdir(exist_ok=True)
    
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    print("✅ Directory structure created")
    
    print("\n" + "=" * 50)
    print("✅ Frontend setup completed!")
    print("\nNext steps:")
    print("1. Copy the frontend files to the frontend/ directory")
    print("2. Start your backend: python backend/main.py")
    print("3. Run the frontend: python frontend/main.py")
    print("\nIf you encounter any issues:")
    print("- Make sure your backend is running on http://localhost:8000")
    print("- Check that all frontend files are in the frontend/ directory")
    print("- For OAuth support, install PyQt6-WebEngine: pip install PyQt6-WebEngine")

if __name__ == "__main__":
    main()