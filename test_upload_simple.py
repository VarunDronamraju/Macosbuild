#!/usr/bin/env python3
"""
Simple test script to test file upload directly
"""

import requests
import os

def create_test_file():
    """Create a simple test file"""
    test_content = "This is a test document for upload testing."
    with open("test_document.txt", "w") as f:
        f.write(test_content)
    return "test_document.txt"

def test_upload_with_auth():
    """Test upload with authentication"""
    print("🧪 Testing File Upload with Authentication")
    
    # Create test file
    test_file = create_test_file()
    
    try:
        # First, get a JWT token (you'll need to login first)
        print("⚠️  Note: You need to login first to get a JWT token")
        print("   Please login through the frontend and copy the JWT token")
        
        # For now, test without auth
        with open(test_file, 'rb') as f:
            files = {'file': (test_file, f, 'text/plain')}
            
            print(f"Uploading file: {test_file}")
            response = requests.post("http://localhost:8000/upload", files=files)
            
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
            
            if response.status_code != 200:
                try:
                    error_detail = response.json()
                    print(f"Error response: {error_detail}")
                except:
                    print(f"Response text: {response.text}")
            else:
                print(f"Success response: {response.json()}")
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)

def test_legacy_upload():
    """Test legacy upload (no auth required)"""
    print("\n🧪 Testing Legacy File Upload (No Auth)")
    
    # Create test file
    test_file = create_test_file()
    
    try:
        with open(test_file, 'rb') as f:
            files = {'file': (test_file, f, 'text/plain')}
            data = {'user_id': 'test_user'}
            
            print(f"Uploading file: {test_file}")
            response = requests.post("http://localhost:8000/upload/legacy", files=files, data=data)
            
            print(f"Response status: {response.status_code}")
            
            if response.status_code != 200:
                try:
                    error_detail = response.json()
                    print(f"Error response: {error_detail}")
                except:
                    print(f"Response text: {response.text}")
            else:
                print(f"Success response: {response.json()}")
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)

if __name__ == "__main__":
    test_legacy_upload()
    test_upload_with_auth()
