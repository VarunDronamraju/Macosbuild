#!/usr/bin/env python3
"""
Fix Google OAuth Dependencies
Installs the missing google-auth packages needed for OAuth
"""

import subprocess
import sys

def install_package(package):
    """Install a package using pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except subprocess.CalledProcessError:
        return False

def main():
    """Install missing Google OAuth dependencies"""
    print("Installing Google OAuth dependencies...")
    
    packages = [
        "google-auth>=2.0.0",
        "google-auth-oauthlib>=0.5.0", 
        "google-auth-httplib2>=0.1.0"
    ]
    
    for package in packages:
        print(f"Installing {package}...")
        if install_package(package):
            print(f"✅ {package} installed successfully")
        else:
            print(f"❌ Failed to install {package}")
    
    print("\n✅ Google OAuth dependencies installed!")
    print("You can now use Google authentication in the app.")

if __name__ == "__main__":
    main()