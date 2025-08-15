#!/usr/bin/env python3
"""
Test script for macOS build process
Validates all components before GitHub workflow
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def test_system():
    """Test system requirements"""
    print("🔍 Testing system requirements...")
    
    # Check macOS
    if platform.system() != "Darwin":
        print("❌ This script is for macOS only")
        return False
    
    print(f"✅ macOS {platform.mac_ver()[0]} detected")
    
    # Check Python version
    python_version = sys.version_info
    if python_version.major != 3 or python_version.minor < 11:
        print(f"❌ Python 3.11+ required, found {python_version.major}.{python_version.minor}")
        return False
    
    print(f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    return True

def test_dependencies():
    """Test required dependencies"""
    print("\n📦 Testing dependencies...")
    
    required_packages = [
        'PyQt6', 'fastapi', 'uvicorn', 'sqlalchemy', 
        'psycopg2', 'qdrant_client', 'ollama', 'tavily',
        'sentence_transformers', 'torch', 'numpy'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - missing")
            missing.append(package)
    
    if missing:
        print(f"\n❌ Missing packages: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt")
        return False
    
    return True

def test_project_structure():
    """Test project structure"""
    print("\n📁 Testing project structure...")
    
    required_files = [
        'frontend/main.py',
        'backend/main.py',
        'backend/config.py',
        'shared/models.py',
        'requirements.txt',
        'dist_configs/pyinstaller_macos_complete.spec',
        'scripts/setup_macos_complete.py'
    ]
    
    missing = []
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - missing")
            missing.append(file_path)
    
    if missing:
        print(f"\n❌ Missing files: {', '.join(missing)}")
        return False
    
    return True

def test_pyinstaller():
    """Test PyInstaller installation"""
    print("\n🔨 Testing PyInstaller...")
    
    try:
        import PyInstaller
        print(f"✅ PyInstaller {PyInstaller.__version__}")
        
        # Test basic PyInstaller functionality
        result = subprocess.run([
            sys.executable, "-m", "PyInstaller", "--version"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ PyInstaller command works")
            return True
        else:
            print("❌ PyInstaller command failed")
            return False
            
    except ImportError:
        print("❌ PyInstaller not installed")
        print("Run: pip install pyinstaller==6.2.0")
        return False

def test_spec_file():
    """Test PyInstaller spec file"""
    print("\n📋 Testing spec file...")
    
    spec_file = Path("dist_configs/pyinstaller_macos_complete.spec")
    
    if not spec_file.exists():
        print("❌ Spec file not found")
        return False
    
    # Test spec file syntax
    try:
        with open(spec_file, 'r') as f:
            content = f.read()
        
        # Basic syntax check
        if 'Analysis(' in content and 'BUNDLE(' in content:
            print("✅ Spec file syntax looks good")
            return True
        else:
            print("❌ Spec file missing required components")
            return False
            
    except Exception as e:
        print(f"❌ Error reading spec file: {e}")
        return False

def test_build_process():
    """Test the build process (dry run)"""
    print("\n🚀 Testing build process...")
    
    # Clean previous builds
    for dir_name in ['build', 'dist']:
        if Path(dir_name).exists():
            import shutil
            shutil.rmtree(dir_name)
            print(f"🧹 Cleaned {dir_name}/")
    
    # Test PyInstaller analysis (without building)
    try:
        result = subprocess.run([
            sys.executable, "-m", "PyInstaller",
            "--dry-run",
            "dist_configs/pyinstaller_macos_complete.spec"
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✅ PyInstaller analysis successful")
            return True
        else:
            print(f"❌ PyInstaller analysis failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ PyInstaller analysis timed out")
        return False
    except Exception as e:
        print(f"❌ Build test failed: {e}")
        return False

def test_setup_script():
    """Test setup script"""
    print("\n🛠️ Testing setup script...")
    
    setup_script = Path("scripts/setup_macos_complete.py")
    
    if not setup_script.exists():
        print("❌ Setup script not found")
        return False
    
    # Test script syntax
    try:
        result = subprocess.run([
            sys.executable, "-m", "py_compile", str(setup_script)
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Setup script syntax is valid")
            return True
        else:
            print(f"❌ Setup script syntax error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Setup script test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 RAG Companion AI - macOS Build Test")
    print("=" * 50)
    
    tests = [
        ("System Requirements", test_system),
        ("Dependencies", test_dependencies),
        ("Project Structure", test_project_structure),
        ("PyInstaller", test_pyinstaller),
        ("Spec File", test_spec_file),
        ("Build Process", test_build_process),
        ("Setup Script", test_setup_script),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} test failed")
        except Exception as e:
            print(f"❌ {test_name} test error: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! Ready for GitHub workflow.")
        print("\n📋 Next steps:")
        print("1. Commit and push to GitHub")
        print("2. Check GitHub Actions tab")
        print("3. Monitor build progress")
        print("4. Download artifacts when complete")
        return True
    else:
        print("❌ Some tests failed. Please fix issues before pushing.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
