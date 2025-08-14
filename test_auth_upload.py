#!/usr/bin/env python3
"""
Test script to verify authentication and upload work together
"""

import requests
import json
import os

def test_auth_and_upload():
    """Test authentication and upload together"""
    print("🧪 Testing Authentication + Upload")
    
    # Create test file
    test_content = "This is a test document for authentication testing."
    with open("test_auth_doc.txt", "w") as f:
        f.write(test_content)
    
    try:
        # Step 1: Test health
        print("\n1. Testing backend health...")
        response = requests.get("http://localhost:8000/health")
        if response.status_code == 200:
            print("✅ Backend is healthy")
        else:
            print(f"❌ Backend health check failed: {response.status_code}")
            return
        
        # Step 2: Test authentication (you need to provide a valid JWT token)
        print("\n2. Testing authentication...")
        print("⚠️  You need to login through the frontend and copy the JWT token")
        print("   The token should be displayed in the OAuth callback page")
        
        # For testing, we'll try without auth first
        print("\n3. Testing upload without authentication (should fail)...")
        with open("test_auth_doc.txt", 'rb') as f:
            files = {'file': ('test_auth_doc.txt', f, 'text/plain')}
            response = requests.post("http://localhost:8000/upload", files=files)
            
            print(f"Response status: {response.status_code}")
            if response.status_code == 401:
                print("✅ Correctly rejected unauthenticated request")
            else:
                print(f"⚠️  Unexpected status: {response.status_code}")
                try:
                    print(f"Response: {response.json()}")
                except:
                    print(f"Response text: {response.text}")
        
        # Step 4: Test with a dummy token (should fail)
        print("\n4. Testing upload with invalid token (should fail)...")
        with open("test_auth_doc.txt", 'rb') as f:
            files = {'file': ('test_auth_doc.txt', f, 'text/plain')}
            headers = {'Authorization': 'Bearer invalid_token'}
            response = requests.post("http://localhost:8000/upload", files=files, headers=headers)
            
            print(f"Response status: {response.status_code}")
            if response.status_code == 401:
                print("✅ Correctly rejected invalid token")
            else:
                print(f"⚠️  Unexpected status: {response.status_code}")
                try:
                    print(f"Response: {response.json()}")
                except:
                    print(f"Response text: {response.text}")
        
        print("\n" + "=" * 60)
        print("📋 Next Steps:")
        print("1. Start the frontend: python frontend/main.py")
        print("2. Login with your Google account")
        print("3. Copy the JWT token from the OAuth callback page")
        print("4. Run this test again with the valid token")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
    finally:
        # Clean up
        if os.path.exists("test_auth_doc.txt"):
            os.remove("test_auth_doc.txt")

if __name__ == "__main__":
    test_auth_and_upload()
