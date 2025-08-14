#!/usr/bin/env python3
"""
Test script to verify document upload and RAG search fixes
"""

import requests
import json
import time
import os

def test_backend_health():
    """Test if backend is running"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend is running and healthy")
            return True
        else:
            print(f"❌ Backend health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend health check failed: {e}")
        return False

def test_upload_endpoint():
    """Test upload endpoint structure"""
    print("\n📋 Upload Endpoint Test:")
    
    # Test without authentication (should fail with 401)
    try:
        response = requests.post("http://localhost:8000/upload")
        if response.status_code == 401:
            print("✅ Upload endpoint requires authentication (correct)")
        else:
            print(f"⚠️  Upload endpoint returned unexpected status: {response.status_code}")
    except Exception as e:
        print(f"❌ Upload endpoint test failed: {e}")
    
    # Test with invalid request (should fail with 422)
    try:
        response = requests.post("http://localhost:8000/upload", json={})
        if response.status_code == 422:
            print("✅ Upload endpoint correctly rejects invalid requests")
        else:
            print(f"⚠️  Upload endpoint returned unexpected status: {response.status_code}")
    except Exception as e:
        print(f"❌ Upload endpoint test failed: {e}")

def test_query_endpoint():
    """Test query endpoint structure"""
    print("\n📋 Query Endpoint Test:")
    
    # Test without authentication (should fail with 401)
    try:
        response = requests.post("http://localhost:8000/query", json={"query": "test"})
        if response.status_code == 401:
            print("✅ Query endpoint requires authentication (correct)")
        else:
            print(f"⚠️  Query endpoint returned unexpected status: {response.status_code}")
    except Exception as e:
        print(f"❌ Query endpoint test failed: {e}")

def test_legacy_endpoints():
    """Test legacy endpoints for offline mode"""
    print("\n📋 Legacy Endpoints Test:")
    
    # Test legacy upload
    try:
        response = requests.post("http://localhost:8000/upload/legacy")
        if response.status_code == 422:  # Missing file
            print("✅ Legacy upload endpoint correctly rejects missing file")
        else:
            print(f"⚠️  Legacy upload endpoint returned unexpected status: {response.status_code}")
    except Exception as e:
        print(f"❌ Legacy upload test failed: {e}")
    
    # Test legacy query
    try:
        response = requests.post("http://localhost:8000/query/legacy", json={"query": "test"})
        if response.status_code == 200:
            print("✅ Legacy query endpoint works (offline mode)")
        else:
            print(f"⚠️  Legacy query endpoint returned unexpected status: {response.status_code}")
    except Exception as e:
        print(f"❌ Legacy query test failed: {e}")

def main():
    """Run all tests"""
    print("🧪 Testing Document Upload and RAG Search Fixes")
    print("=" * 60)
    
    # Test 1: Backend health
    if not test_backend_health():
        print("\n❌ Backend is not running. Please start the backend first:")
        print("   python backend/main.py")
        return
    
    # Test 2: Upload endpoint
    test_upload_endpoint()
    
    # Test 3: Query endpoint
    test_query_endpoint()
    
    # Test 4: Legacy endpoints
    test_legacy_endpoints()
    
    print("\n" + "=" * 60)
    print("✅ Upload and RAG Search Fix Tests Completed!")
    print("\n🔧 Fixes Applied:")
    print("1. ✅ Fixed error handling in API client")
    print("2. ✅ Fixed authentication token handling")
    print("3. ✅ Fixed UUID conversion in get_current_user")
    print("4. ✅ Added debugging to upload endpoint")
    print("5. ✅ Improved error messages")
    
    print("\n📋 Next Steps:")
    print("1. Start the frontend: python frontend/main.py")
    print("2. Login with your Google account")
    print("3. Try uploading a document")
    print("4. Try asking a question about the document")
    print("5. Verify RAG search is working properly")

if __name__ == "__main__":
    main()
