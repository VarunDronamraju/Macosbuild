# =============================================================================
# FILE 6: build_scripts/build_macos.py
# =============================================================================

#!/usr/bin/env python3
"""
macOS build script for RAG Companion AI  
Creates macOS .app bundle and .dmg installer
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import platform

def check_prerequisites():
    """Check if all prerequisites are installed"""
    print("🔍 Checking prerequisites...")
    
    missing = []
    
    # Check PyInstaller
    try:
        import PyInstaller
        print(f"  ✅ PyInstaller {PyInstaller.__version__}")
    except ImportError:
        missing.append("pyinstaller")
    
    # Check if on macOS
    if platform.system() != "Darwin":
        print(f"  ⚠️ Building macOS app on {platform.system()}")
    
    # Check create-dmg (optional)
    try:
        result = subprocess.run(['create-dmg', '--version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  ✅ create-dmg available")
        else:
            print(f"  ⚠️ create-dmg not found - will use hdiutil")
    except FileNotFoundError:
        print(f"  ⚠️ create-dmg not found - will use hdiutil")
    
    if missing:
        print(f"  ❌ Missing: {', '.join(missing)}")
        print("  Run: pip install " + " ".join(missing))
        return False
    
    return True

def clean_build_directories():
    """Clean previous build artifacts"""
    print("🧹 Cleaning build directories...")
    
    dirs_to_clean = ['build', 'dist']
    
    for dir_name in dirs_to_clean:
        if Path(dir_name).exists():
            shutil.rmtree(dir_name)
            print(f"  ✅ Cleaned {dir_name}/")

def build_app():
    """Build the macOS .app bundle"""
    print("🔨 Building macOS app bundle...")
    
    spec_file = Path("dist_configs/pyinstaller_macos.spec")
    
    if not spec_file.exists():
        print(f"  ❌ Spec file not found: {spec_file}")
        return False
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        str(spec_file)
    ]
    
    print(f"  Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("  ✅ App bundle built successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Build failed:")
        print(f"  Error: {e.stderr}")
        return False

def create_dmg():
    """Create DMG installer"""
    print("📦 Creating DMG installer...")
    
    app_path = Path("dist/RAG Companion AI.app")
    dmg_path = Path("dist/RAGCompanionAI-Installer.dmg")
    
    if not app_path.exists():
        print(f"  ❌ App bundle not found: {app_path}")
        return False
    
    # Try create-dmg first, fall back to hdiutil
    if create_dmg_with_create_dmg(app_path, dmg_path):
        return True
    else:
        return create_dmg_with_hdiutil(app_path, dmg_path)

def create_dmg_with_create_dmg(app_path, dmg_path):
    """Create DMG using create-dmg tool"""
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
        print("  ✅ DMG created with create-dmg")
        return True
        
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("  ⚠️ create-dmg failed, trying hdiutil...")
        return False

def create_dmg_with_hdiutil(app_path, dmg_path):
    """Create DMG using built-in hdiutil"""
    try:
        print("  📦 Using hdiutil to create DMG...")
        
        # Calculate size needed
        result = subprocess.run(['du', '-sm', str(app_path)], 
                              capture_output=True, text=True)
        app_size_mb = int(result.stdout.split()[0])
        dmg_size_mb = app_size_mb + 50  # Add 50MB buffer
        
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
        
        print("  ✅ DMG created with hdiutil")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"  ❌ DMG creation failed: {e}")
        return False

def main():
    """Main macOS build process"""
    print("🍎 RAG Companion AI - macOS Build")
    print("=" * 50)
    
    # Check prerequisites
    if not check_prerequisites():
        sys.exit(1)
    
    # Clean previous builds
    clean_build_directories()
    
    # Build app bundle
    if not build_app():
        sys.exit(1)
    
    # Create DMG
    create_dmg()
    
    # Summary
    print("\n" + "=" * 50)
    print("🎉 macOS build complete!")
    print("\n📁 Output files:")
    
    app_path = Path("dist/RAG Companion AI.app")
    if app_path.exists():
        print(f"  📱 App bundle: {app_path}")
    
    dmg_path = Path("dist/RAGCompanionAI-Installer.dmg")
    if dmg_path.exists():
        print(f"  💿 DMG installer: {dmg_path}")
        print(f"  📏 Size: {dmg_path.stat().st_size // (1024*1024)} MB")
    else:
        print("  ⚠️ No DMG created")
        print("  💡 You can distribute the .app bundle directly")

if __name__ == "__main__":
    main()

