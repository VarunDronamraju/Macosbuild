#!/usr/bin/env python3
"""
DMG Download Helper for RAG Companion AI
Helps users download the latest DMG file from GitHub Actions
"""

import requests
import json
import sys
from pathlib import Path

def get_latest_workflow_run():
    """Get the latest workflow run from GitHub API"""
    repo = "VarunDronamraju/Macosbuild"
    workflow_id = "build-macos.yml"
    
    # GitHub API URL for workflow runs
    url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_id}/runs"
    
    try:
        response = requests.get(url, headers={
            'Accept': 'application/vnd.github.v3+json'
        })
        response.raise_for_status()
        
        runs = response.json()
        if runs['workflow_runs']:
            latest_run = runs['workflow_runs'][0]
            return latest_run
        else:
            return None
            
    except Exception as e:
        print(f"❌ Error fetching workflow runs: {e}")
        return None

def get_artifacts(run_id):
    """Get artifacts from a specific workflow run"""
    repo = "VarunDronamraju/Macosbuild"
    url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/artifacts"
    
    try:
        response = requests.get(url, headers={
            'Accept': 'application/vnd.github.v3+json'
        })
        response.raise_for_status()
        
        artifacts = response.json()
        return artifacts['artifacts']
        
    except Exception as e:
        print(f"❌ Error fetching artifacts: {e}")
        return []

def main():
    """Main function to help users get the DMG"""
    print("🍎 RAG Companion AI - DMG Download Helper")
    print("=" * 50)
    
    print("🔍 Checking for latest build...")
    latest_run = get_latest_workflow_run()
    
    if not latest_run:
        print("❌ No workflow runs found")
        print("💡 The build might still be in progress or failed")
        return
    
    run_id = latest_run['id']
    status = latest_run['conclusion']
    
    print(f"📋 Latest build status: {status}")
    print(f"🆔 Run ID: {run_id}")
    
    if status != "success":
        print("❌ Latest build was not successful")
        print("💡 Please wait for the build to complete or check for errors")
        return
    
    print("✅ Build completed successfully!")
    print("📥 Getting artifacts...")
    
    artifacts = get_artifacts(run_id)
    dmg_artifact = None
    
    for artifact in artifacts:
        if "DMG" in artifact['name']:
            dmg_artifact = artifact
            break
    
    if not dmg_artifact:
        print("❌ DMG artifact not found")
        return
    
    print(f"📦 Found DMG artifact: {dmg_artifact['name']}")
    print(f"📏 Size: {dmg_artifact['size_in_bytes'] / (1024*1024):.1f} MB")
    
    print("\n" + "=" * 50)
    print("📥 To download the DMG file:")
    print("1. Go to: https://github.com/VarunDronamraju/Macosbuild/actions")
    print("2. Click on the latest successful workflow run")
    print("3. Scroll down to 'Artifacts' section")
    print("4. Click on 'RAGCompanionAI-macOS-DMG' to download")
    print("\n📋 Alternative method:")
    print("1. Go to: https://github.com/VarunDronamraju/Macosbuild/releases")
    print("2. Download the latest release DMG file")
    
    print("\n🔧 To trigger a new build:")
    print("1. Go to: https://github.com/VarunDronamraju/Macosbuild/actions")
    print("2. Click 'Build macOS Application' workflow")
    print("3. Click 'Run workflow' button")
    print("4. Wait for the build to complete")
    
    print("\n📱 Installation instructions:")
    print("1. Download and mount the DMG file")
    print("2. Drag 'RAG Companion AI.app' to Applications folder")
    print("3. Run the installer script to setup dependencies")
    print("4. Launch RAG Companion AI")

if __name__ == "__main__":
    main()
