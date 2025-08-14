# FILE 1: build_scripts/setup_packaging.py
"""
Initial setup script to prepare packaging environment
Run this first to set up everything needed for packaging
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import platform
import requests
import zipfile

def create_directory_structure():
    """Create all necessary directories for packaging"""
    directories = [
        "build_scripts",
        "resources/icons",
        "resources/binaries/windows",
        "resources/binaries/macos", 
        "resources/models",
        "resources/databases",
        "dist_configs",
        "packaging/windows",
        "packaging/macos",
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created directory: {directory}")

def install_packaging_dependencies():
    """Install all dependencies needed for packaging"""
    print("📦 Installing packaging dependencies...")
    
    dependencies = [
        "pyinstaller>=5.0.0",
        "requests",
        "Pillow",  # For icon processing
    ]
    
    # macOS specific
    if platform.system() == "Darwin":
        dependencies.extend([
            "dmgbuild",  # For creating DMG files
            "create-dmg"  # Alternative DMG creator
        ])
    
    for dep in dependencies:
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", dep], 
                         check=True, capture_output=True)
            print(f"✅ Installed: {dep}")
        except subprocess.CalledProcessError:
            print(f"❌ Failed to install: {dep}")

def download_binaries():
    """Download platform-specific binaries"""
    print("⬇️ Downloading platform binaries...")
    
    current_platform = platform.system()
    
    if current_platform == "Windows" or True:  # Download for both platforms
        download_windows_binaries()
    
    if current_platform == "Darwin" or True:  # Download for both platforms  
        download_macos_binaries()

def download_windows_binaries():
    """Download Windows-specific binaries"""
    print("📥 Downloading Windows binaries...")
    
    # Download Qdrant for Windows
    qdrant_dir = Path("resources/binaries/windows")
    try:
        qdrant_url = "https://github.com/qdrant/qdrant/releases/latest/download/qdrant-x86_64-pc-windows-msvc.zip"
        
        print("  - Downloading Qdrant...")
        response = requests.get(qdrant_url, timeout=30)
        response.raise_for_status()
        
        zip_path = qdrant_dir / "qdrant.zip"
        with open(zip_path, 'wb') as f:
            f.write(response.content)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extract("qdrant.exe", qdrant_dir)
        
        zip_path.unlink()
        print("  ✅ Qdrant for Windows downloaded")
        
    except Exception as e:
        print(f"  ❌ Failed to download Windows binaries: {e}")

def download_macos_binaries():
    """Download macOS-specific binaries"""
    print("📥 Downloading macOS binaries...")
    
    qdrant_dir = Path("resources/binaries/macos")
    
    try:
        # Detect architecture
        arch = platform.machine()
        if arch == "arm64":
            qdrant_url = "https://github.com/qdrant/qdrant/releases/latest/download/qdrant-aarch64-apple-darwin"
        else:
            qdrant_url = "https://github.com/qdrant/qdrant/releases/latest/download/qdrant-x86_64-apple-darwin"
        
        print(f"  - Downloading Qdrant for {arch}...")
        response = requests.get(qdrant_url, timeout=30)
        response.raise_for_status()
        
        binary_path = qdrant_dir / "qdrant"
        with open(binary_path, 'wb') as f:
            f.write(response.content)
        
        # Make executable
        os.chmod(binary_path, 0o755)
        print("  ✅ Qdrant for macOS downloaded")
        
    except Exception as e:
        print(f"  ❌ Failed to download macOS binaries: {e}")

def create_app_icon():
    """Create application icon if it doesn't exist"""
    icon_dir = Path("resources/icons")
    
    # Create a simple icon if none exists
    if not (icon_dir / "app_icon.png").exists():
        print("🎨 Creating default app icon...")
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # Create a simple 512x512 icon
            img = Image.new('RGBA', (512, 512), (41, 128, 185, 255))
            draw = ImageDraw.Draw(img)
            
            # Draw RAG text
            try:
                font = ImageFont.truetype("arial.ttf", 120)
            except:
                font = ImageFont.load_default()
            
            # Draw text
            text = "RAG"
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (512 - text_width) // 2
            y = (512 - text_height) // 2
            
            draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)
            
            # Save PNG
            img.save(icon_dir / "app_icon.png")
            
            # Convert to ICO for Windows
            img.save(icon_dir / "app_icon.ico", format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
            
            # Convert to ICNS for macOS (requires Pillow with ICNS support)
            try:
                img.save(icon_dir / "app_icon.icns", format='ICNS')
            except:
                print("  ⚠️ Could not create ICNS file - install Pillow with ICNS support")
            
            print("  ✅ Default icons created")
            
        except ImportError:
            print("  ⚠️ Pillow not available - using text placeholder")
            # Create a simple text file as placeholder
            with open(icon_dir / "app_icon.txt", 'w') as f:
                f.write("Replace this with your app icon files:\n")
                f.write("- app_icon.png (512x512)\n")
                f.write("- app_icon.ico (Windows)\n")
                f.write("- app_icon.icns (macOS)\n")

def main():
    """Main setup function"""
    print("🚀 Setting up RAG Companion AI packaging environment...")
    print(f"Platform: {platform.system()} {platform.machine()}")
    print("-" * 60)
    
    # Step 1: Create directories
    create_directory_structure()
    print()
    
    # Step 2: Install dependencies
    install_packaging_dependencies()
    print()
    
    # Step 3: Download binaries
    download_binaries()
    print()
    
    # Step 4: Create icons
    create_app_icon()
    print()
    
    print("🎉 Packaging environment setup complete!")
    print("-" * 60)
    print("Next steps:")
    print("1. Run: python build_scripts/download_models.py")
    print("2. Run: python build_scripts/build_windows.py  (for Windows)")
    print("3. Run: python build_scripts/build_macos.py    (for macOS)")

if __name__ == "__main__":
    main()

