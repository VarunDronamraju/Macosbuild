#!/usr/bin/env python3
"""
Setup script for GitHub secrets
Helps configure API keys for the macOS build workflow
"""

import os
import subprocess
import sys

def run_command(command):
    """Run a command and return the result"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def check_gh_cli():
    """Check if GitHub CLI is installed"""
    success, stdout, stderr = run_command("gh --version")
    if not success:
        print("❌ GitHub CLI (gh) is not installed")
        print("Please install it from: https://cli.github.com/")
        return False
    print("✅ GitHub CLI is installed")
    return True

def check_authentication():
    """Check if user is authenticated with GitHub"""
    success, stdout, stderr = run_command("gh auth status")
    if not success:
        print("❌ Not authenticated with GitHub")
        print("Please run: gh auth login")
        return False
    print("✅ Authenticated with GitHub")
    return True

def set_secret(secret_name, secret_value, repo):
    """Set a GitHub secret"""
    print(f"Setting {secret_name}...")
    success, stdout, stderr = run_command(f'gh secret set {secret_name} --body "{secret_value}" --repo {repo}')
    if success:
        print(f"✅ {secret_name} set successfully")
        return True
    else:
        print(f"❌ Failed to set {secret_name}: {stderr}")
        return False

def main():
    """Main setup function"""
    print("🔧 GitHub Secrets Setup for RAG Companion AI")
    print("=" * 50)
    
    # Check prerequisites
    if not check_gh_cli():
        return False
    
    if not check_authentication():
        return False
    
    # Get repository name
    repo = input("Enter your GitHub repository (e.g., username/repo): ").strip()
    if not repo:
        print("❌ Repository name is required")
        return False
    
    # API Keys to set
    secrets = {
        'TAVILY_API_KEY': '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',
        'GOOGLE_CLIENT_ID': '778657599269-ouflj5id5r0bchm9a8lcko1tskkk4j4f.apps.googleusercontent.com',
        'GOOGLE_CLIENT_SECRET': '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',
        'SECRET_KEY': 'kJ8mN2pQ5sT9vY3wZ6aD1fH4jL7nR0uX8bE5hK2mP9sV6yB3eG1iL4oR7tA0cF3h'
    }
    
    print(f"\n📋 Setting up secrets for repository: {repo}")
    print("These are the development API keys that will be included in the build.")
    
    # Confirm with user
    response = input("\nDo you want to proceed? (y/N): ").strip().lower()
    if response != 'y':
        print("Setup cancelled.")
        return False
    
    # Set secrets
    success_count = 0
    for secret_name, secret_value in secrets.items():
        if set_secret(secret_name, secret_value, repo):
            success_count += 1
    
    print(f"\n📊 Results: {success_count}/{len(secrets)} secrets set successfully")
    
    if success_count == len(secrets):
        print("\n🎉 All secrets configured successfully!")
        print("\n📋 Next steps:")
        print("1. Commit and push your changes")
        print("2. The GitHub workflow will now use these secrets")
        print("3. Check the Actions tab to monitor the build")
        return True
    else:
        print("\n❌ Some secrets failed to set. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
