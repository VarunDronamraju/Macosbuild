# =============================================================================
# FILE 5: build_scripts/build_windows.py
# =============================================================================

#!/usr/bin/env python3
"""
Windows build script for RAG Companion AI
Creates Windows executable and installer
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
    
    # Check if on Windows
    if platform.system() != "Windows":
        print(f"  ⚠️ Building Windows app on {platform.system()}")
    
    # Check NSIS (optional)
    try:
        result = subprocess.run(['makensis', '/VERSION'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  ✅ NSIS available")
        else:
            print(f"  ⚠️ NSIS not found - installer creation will be skipped")
    except FileNotFoundError:
        print(f"  ⚠️ NSIS not found - installer creation will be skipped")
    
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

def build_executable():
    """Build the Windows executable"""
    print("🔨 Building Windows executable...")
    
    spec_file = Path("dist_configs/pyinstaller_windows.spec")
    
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
        print("  ✅ Executable built successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Build failed:")
        print(f"  Error: {e.stderr}")
        return False

def create_installer():
    """Create NSIS installer (if NSIS is available)"""
    print("📦 Creating Windows installer...")
    
    # Check if NSIS is available
    try:
        subprocess.run(['makensis', '/VERSION'], 
                      capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("  ⚠️ NSIS not available - skipping installer creation")
        print("  💡 Install NSIS from https://nsis.sourceforge.io/ to create installer")
        return True  # Not a failure, just skipped
    
    # Create simple NSIS script
    nsis_script = create_nsis_script()
    
    if not nsis_script:
        return False
    
    try:
        result = subprocess.run(['makensis', str(nsis_script)], 
                              check=True, capture_output=True, text=True)
        print("  ✅ Windows installer created")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Installer creation failed:")
        print(f"  Error: {e.stderr}")
        return False

def create_nsis_script():
    """Create NSIS installer script"""
    nsis_content = '''
; RAG Companion AI Windows Installer

!define APP_NAME "RAG Companion AI"
!define APP_VERSION "1.0.0"
!define APP_PUBLISHER "RAG AI"
!define APP_EXE "RAGCompanionAI.exe"

Name "${APP_NAME}"
OutFile "dist\\RAGCompanionAI-Setup.exe"
InstallDir "$PROGRAMFILES64\\${APP_NAME}"
RequestExecutionLevel admin

; Pages
Page directory
Page instfiles

; Installer
Section "Install"
    SetOutPath "$INSTDIR"
    File /r "dist\\RAGCompanionAI\\*"
    
    ; Create shortcuts
    CreateDirectory "$SMPROGRAMS\\${APP_NAME}"
    CreateShortcut "$SMPROGRAMS\\${APP_NAME}\\${APP_NAME}.lnk" "$INSTDIR\\${APP_EXE}"
    CreateShortcut "$DESKTOP\\${APP_NAME}.lnk" "$INSTDIR\\${APP_EXE}"
    
    ; Registry
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}" "DisplayName" "${APP_NAME}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}" "UninstallString" "$INSTDIR\\Uninstall.exe"
    WriteUninstaller "$INSTDIR\\Uninstall.exe"
SectionEnd

; Uninstaller
Section "Uninstall"
    Delete "$INSTDIR\\Uninstall.exe"
    RMDir /r "$INSTDIR"
    Delete "$DESKTOP\\${APP_NAME}.lnk"
    RMDir /r "$SMPROGRAMS\\${APP_NAME}"
    DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}"
SectionEnd
'''
    
    script_path = Path("build_scripts/installer_windows.nsi")
    
    try:
        with open(script_path, 'w') as f:
            f.write(nsis_content)
        return script_path
    except Exception as e:
        print(f"  ❌ Failed to create NSIS script: {e}")
        return None

def main():
    """Main Windows build process"""
    print("🪟 RAG Companion AI - Windows Build")
    print("=" * 50)
    
    # Check prerequisites
    if not check_prerequisites():
        sys.exit(1)
    
    # Clean previous builds
    clean_build_directories()
    
    # Build executable
    if not build_executable():
        sys.exit(1)
    
    # Create installer
    create_installer()
    
    # Summary
    print("\n" + "=" * 50)
    print("🎉 Windows build complete!")
    print("\n📁 Output files:")
    
    dist_dir = Path("dist")
    if (dist_dir / "RAGCompanionAI").exists():
        print(f"  📦 Application folder: {dist_dir / 'RAGCompanionAI'}")
    
    setup_file = dist_dir / "RAGCompanionAI-Setup.exe"
    if setup_file.exists():
        print(f"  💿 Installer: {setup_file}")
        print(f"  📏 Size: {setup_file.stat().st_size // (1024*1024)} MB")
    else:
        print("  ⚠️ No installer created (NSIS not available)")
        print("  💡 You can distribute the RAGCompanionAI folder directly")

if __name__ == "__main__":
    main()
