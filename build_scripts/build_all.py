# =============================================================================
# FILE 7: build_scripts/build_all.py
# =============================================================================

#!/usr/bin/env python3
"""
Master build script - builds for all platforms
Your sister can run this to build everything automatically
"""

import sys
import subprocess
import platform
from pathlib import Path

def print_banner():
    """Print application banner"""
    banner = """
╔══════════════════════════════════════════════════════════╗
║                RAG Companion AI                          ║
║              Complete Build System                       ║
║                                                          ║
║  🚀 Automated packaging for Windows and macOS           ║
╚══════════════════════════════════════════════════════════╝
"""
    print(banner)

def run_setup():
    """Run initial setup"""
    print("🛠️ STEP 1: Setting up packaging environment...")
    print("-" * 60)
    
    try:
        result = subprocess.run([
            sys.executable, "build_scripts/setup_packaging.py"
        ], check=True)
        print("✅ Setup completed successfully\n")
        return True
    except subprocess.CalledProcessError:
        print("❌ Setup failed\n")
        return False

def download_models():
    """Download AI models"""
    print("🤖 STEP 2: Downloading AI models...")
    print("-" * 60)
    
    try:
        result = subprocess.run([
            sys.executable, "build_scripts/download_models.py"
        ], check=True)
        print("✅ Models downloaded successfully\n")
        return True
    except subprocess.CalledProcessError:
        print("❌ Model download failed\n")
        return False

def build_windows():
    """Build Windows version"""
    print("🪟 STEP 3a: Building Windows version...")
    print("-" * 60)
    
    try:
        result = subprocess.run([
            sys.executable, "build_scripts/build_windows.py"
        ], check=True)
        print("✅ Windows build completed\n")
        return True
    except subprocess.CalledProcessError:
        print("❌ Windows build failed\n")
        return False

def build_macos():
    """Build macOS version"""
    print("🍎 STEP 3b: Building macOS version...")
    print("-" * 60)
    
    try:
        result = subprocess.run([
            sys.executable, "build_scripts/build_macos.py"
        ], check=True)
        print("✅ macOS build completed\n")
        return True
    except subprocess.CalledProcessError:
        print("❌ macOS build failed\n")
        return False

def show_results():
    """Show build results"""
    print("📋 BUILD RESULTS")
    print("=" * 60)
    
    dist_dir = Path("dist")
    if not dist_dir.exists():
        print("❌ No dist directory found")
        return
    
    # Check Windows builds
    windows_folder = dist_dir / "RAGCompanionAI"
    windows_installer = dist_dir / "RAGCompanionAI-Setup.exe"
    
    if windows_folder.exists():
        print("🪟 Windows Build:")
        print(f"  📦 Application: {windows_folder}")
        if windows_installer.exists():
            size_mb = windows_installer.stat().st_size // (1024*1024)
            print(f"  💿 Installer: {windows_installer} ({size_mb} MB)")
    
    # Check macOS builds
    macos_app = dist_dir / "RAG Companion AI.app"
    macos_dmg = dist_dir / "RAGCompanionAI-Installer.dmg"
    
    if macos_app.exists():
        print("🍎 macOS Build:")
        print(f"  📱 App Bundle: {macos_app}")
        if macos_dmg.exists():
            size_mb = macos_dmg.stat().st_size // (1024*1024)
            print(f"  💿 DMG Installer: {macos_dmg} ({size_mb} MB)")
    
    print("\n🎉 Build process complete!")
    print("\n📧 Next steps:")
    print("  1. Test the applications on clean machines")
    print("  2. Upload to distribution platforms")
    print("  3. Create release notes")

def main():
    """Main build orchestration"""
    print_banner()
    
    current_platform = platform.system()
    print(f"🖥️ Running on: {current_platform} {platform.machine()}")
    print(f"🐍 Python: {sys.version}")
    print()
    
    # Determine what to build
    if len(sys.argv) > 1:
        target = sys.argv[1].lower()
    else:
        target = "current"  # Build for current platform
    
    # Step 1: Setup
    if not run_setup():
        sys.exit(1)
    
    # Step 2: Download models
    if not download_models():
        sys.exit(1)
    
    # Step 3: Build applications
    success = True
    
    if target in ["windows", "win", "all"]:
        success &= build_windows()
    
    if target in ["macos", "darwin", "all"]:
        success &= build_macos()
    
    if target == "current":
        if current_platform == "Windows":
            success &= build_windows()
        elif current_platform == "Darwin":
            success &= build_macos()
        else:
            print(f"❌ Unsupported platform for building: {current_platform}")
            sys.exit(1)
    
    # Show results
    show_results()
    
    if not success:
        print("⚠️ Some builds failed - check logs above")
        sys.exit(1)

if __name__ == "__main__":
    main()
