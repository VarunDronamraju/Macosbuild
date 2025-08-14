#!/usr/bin/env python3
"""
macOS Standalone Build Script for RAG Companion AI
Creates a completely self-contained macOS application with DMG installer
"""

import os
import sys
import subprocess
import shutil
import platform
import requests
import zipfile
from pathlib import Path
import json

def check_macos_environment():
    """Check if we're on macOS and have required tools"""
    if platform.system() != "Darwin":
        print("❌ This script must be run on macOS")
        print("💡 For cross-platform building, use the main build script")
        return False
    
    print("✅ Running on macOS")
    
    # Check for required tools
    required_tools = ['python3', 'pip3', 'hdiutil']
    missing_tools = []
    
    for tool in required_tools:
        if shutil.which(tool) is None:
            missing_tools.append(tool)
    
    if missing_tools:
        print(f"❌ Missing required tools: {', '.join(missing_tools)}")
        return False
    
    print("✅ All required tools available")
    return True

def setup_macos_dependencies():
    """Install macOS-specific dependencies"""
    print("📦 Installing macOS dependencies...")
    
    macos_deps = [
        "pyinstaller>=6.2.0",
        "dmgbuild>=1.4.2",
        "create-dmg>=1.0.0",
        "Pillow>=10.0.0",
    ]
    
    for dep in macos_deps:
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", dep], 
                         check=True, capture_output=True)
            print(f"✅ Installed: {dep}")
        except subprocess.CalledProcessError:
            print(f"❌ Failed to install: {dep}")
            return False
    
    return True

def download_macos_binaries():
    """Download macOS-specific binaries"""
    print("⬇️ Downloading macOS binaries...")
    
    # Create directories
    binary_dir = Path("resources/binaries/macos")
    binary_dir.mkdir(parents=True, exist_ok=True)
    
    # Download Qdrant for macOS
    try:
        arch = platform.machine()
        if arch == "arm64":
            qdrant_url = "https://github.com/qdrant/qdrant/releases/latest/download/qdrant-aarch64-apple-darwin"
        else:
            qdrant_url = "https://github.com/qdrant/qdrant/releases/latest/download/qdrant-x86_64-apple-darwin"
        
        print(f"📥 Downloading Qdrant for {arch}...")
        response = requests.get(qdrant_url, timeout=30)
        response.raise_for_status()
        
        qdrant_path = binary_dir / "qdrant"
        with open(qdrant_path, 'wb') as f:
            f.write(response.content)
        
        # Make executable
        os.chmod(qdrant_path, 0o755)
        print("✅ Qdrant binary downloaded")
        
    except Exception as e:
        print(f"⚠️ Failed to download Qdrant: {e}")
        print("💡 Will use Docker-based Qdrant instead")
    
    return True

def create_app_icon():
    """Create macOS app icon"""
    print("🎨 Creating macOS app icon...")
    
    icon_dir = Path("resources/icons")
    icon_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a simple icon if none exists
    if not (icon_dir / "app_icon.icns").exists():
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # Create 512x512 icon
            img = Image.new('RGBA', (512, 512), (41, 128, 185, 255))
            draw = ImageDraw.Draw(img)
            
            # Try to use system font
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 120)
            except:
                font = ImageFont.load_default()
            
            # Draw RAG text
            text = "RAG"
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (512 - text_width) // 2
            y = (512 - text_height) // 2
            
            draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)
            
            # Save as ICNS
            img.save(icon_dir / "app_icon.icns", format='ICNS')
            print("✅ macOS app icon created")
            
        except ImportError:
            print("⚠️ Pillow not available - using default icon")
    
    return True

def build_macos_app():
    """Build the macOS app bundle"""
    print("🔨 Building macOS app bundle...")
    
    spec_file = Path("dist_configs/pyinstaller_macos.spec")
    
    if not spec_file.exists():
        print(f"❌ Spec file not found: {spec_file}")
        return False
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        str(spec_file)
    ]
    
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ macOS app bundle built successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed:")
        print(f"Error: {e.stderr}")
        return False

def create_dmg():
    """Create DMG installer"""
    print("📦 Creating DMG installer...")
    
    app_path = Path("dist/RAG Companion AI.app")
    dmg_path = Path("dist/RAGCompanionAI-Installer.dmg")
    
    if not app_path.exists():
        print(f"❌ App bundle not found: {app_path}")
        return False
    
    # Try create-dmg first
    try:
        cmd = [
            "create-dmg",
            "--volname", "RAG Companion AI",
            "--volicon", "resources/icons/app_icon.icns",
            "--window-pos", "200", "120",
            "--window-size", "600", "400",
            "--icon-size", "100",
            "--icon", "RAG Companion AI.app", "175", "190",
            "--hide-extension", "RAG Companion AI.app",
            "--app-drop-link", "425", "190",
            str(dmg_path),
            str(app_path.parent)
        ]
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ DMG created with create-dmg")
        return True
        
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("⚠️ create-dmg failed, trying hdiutil...")
        
        # Fallback to hdiutil
        try:
            # Calculate size needed
            result = subprocess.run(['du', '-sm', str(app_path)], 
                                  capture_output=True, text=True)
            app_size_mb = int(result.stdout.split()[0])
            dmg_size_mb = app_size_mb + 100  # Add 100MB buffer
            
            temp_dmg = Path("dist/temp.dmg")
            mount_point = Path("/tmp/rag_dmg_mount")
            
            # Create temporary DMG
            cmd = [
                "hdiutil", "create",
                "-size", f"{dmg_size_mb}m",
                "-fs", "HFS+",
                "-volname", "RAG Companion AI",
                str(temp_dmg)
            ]
            subprocess.run(cmd, check=True)
            
            # Mount DMG
            cmd = ["hdiutil", "attach", str(temp_dmg), "-mountpoint", str(mount_point)]
            subprocess.run(cmd, check=True)
            
            try:
                # Copy app to DMG
                shutil.copytree(app_path, mount_point / "RAG Companion AI.app")
                
                # Create Applications symlink
                applications_link = mount_point / "Applications"
                if applications_link.exists():
                    applications_link.unlink()
                applications_link.symlink_to("/Applications")
                
            finally:
                # Unmount DMG
                subprocess.run(["hdiutil", "detach", str(mount_point)], 
                             capture_output=True)
            
            # Convert to compressed DMG
            if dmg_path.exists():
                dmg_path.unlink()
                
            cmd = [
                "hdiutil", "convert", str(temp_dmg),
                "-format", "UDZO",
                "-o", str(dmg_path)
            ]
            subprocess.run(cmd, check=True)
            
            # Clean up
            temp_dmg.unlink()
            
            print("✅ DMG created with hdiutil")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ DMG creation failed: {e}")
            return False

def create_installer_script():
    """Create installation script for dependencies"""
    print("📝 Creating installer script...")
    
    installer_script = '''#!/bin/bash
# RAG Companion AI - macOS Installer Script

echo "🚀 Installing RAG Companion AI dependencies..."

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "📦 Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "🐳 Installing Docker..."
    brew install --cask docker
fi

# Install Ollama if not present
if ! command -v ollama &> /dev/null; then
    echo "🦙 Installing Ollama..."
    brew install ollama
fi

# Start Docker
echo "🐳 Starting Docker..."
open -a Docker

# Wait for Docker to start
echo "⏳ Waiting for Docker to start..."
sleep 30

# Pull required Docker images
echo "📥 Pulling Docker images..."
docker pull postgres:15
docker pull qdrant/qdrant:latest

# Start services
echo "🚀 Starting services..."
docker-compose up -d

# Pull Ollama model
echo "🤖 Downloading AI model..."
ollama pull gemma3:1b-it-qat

echo "✅ Installation complete!"
echo "🎉 RAG Companion AI is ready to use!"
'''
    
    script_path = Path("dist/install_dependencies.sh")
    with open(script_path, 'w') as f:
        f.write(installer_script)
    
    # Make executable
    os.chmod(script_path, 0o755)
    print("✅ Installer script created")
    
    return True

def main():
    """Main macOS build process"""
    print("🍎 RAG Companion AI - macOS Standalone Build")
    print("=" * 60)
    
    # Check environment
    if not check_macos_environment():
        sys.exit(1)
    
    # Setup dependencies
    if not setup_macos_dependencies():
        sys.exit(1)
    
    # Download binaries
    download_macos_binaries()
    
    # Create icons
    create_app_icon()
    
    # Build app
    if not build_macos_app():
        sys.exit(1)
    
    # Create DMG
    create_dmg()
    
    # Create installer script
    create_installer_script()
    
    # Summary
    print("\n" + "=" * 60)
    print("🎉 macOS standalone build complete!")
    print("\n📁 Output files:")
    
    app_path = Path("dist/RAG Companion AI.app")
    if app_path.exists():
        print(f"  📱 App bundle: {app_path}")
    
    dmg_path = Path("dist/RAGCompanionAI-Installer.dmg")
    if dmg_path.exists():
        size_mb = dmg_path.stat().st_size // (1024*1024)
        print(f"  💿 DMG installer: {dmg_path} ({size_mb} MB)")
    
    installer_script = Path("dist/install_dependencies.sh")
    if installer_script.exists():
        print(f"  📝 Installer script: {installer_script}")
    
    print("\n📋 Next steps for users:")
    print("  1. Install the DMG file")
    print("  2. Run the installer script to setup dependencies")
    print("  3. Launch RAG Companion AI")
    
    print("\n✅ Standalone macOS application ready!")

if __name__ == "__main__":
    main()
