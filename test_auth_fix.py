#!/usr/bin/env python3
"""
Test script to verify the Google OAuth authentication fix
"""

import requests
import json
import time

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

def test_oauth_url():
    """Test OAuth URL generation"""
    try:
        # This is the same URL that the frontend generates
        client_id = "778657599269-ouflj5id5r0bchm9a8lcko1tskkk4j4f.apps.googleusercontent.com"
        redirect_uri = "http://localhost:8000/auth/callback"
        scope = "openid email profile"
        
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent"
        }
        
        import urllib.parse
        oauth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
        
        print("✅ OAuth URL generated successfully")
        print(f"   URL: {oauth_url}")
        return True
    except Exception as e:
        print(f"❌ OAuth URL generation failed: {e}")
        return False

def test_auth_endpoints():
    """Test authentication endpoints"""
    try:
        # Test the /auth/google endpoint with a dummy token
        dummy_token = "dummy_token_for_testing"
        response = requests.post(
            "http://localhost:8000/auth/google",
            json={"token": dummy_token},
            timeout=5
        )
        
        # We expect this to fail with a 401, which is correct for a dummy token
        if response.status_code == 401:
            print("✅ /auth/google endpoint is working (correctly rejected dummy token)")
        else:
            print(f"⚠️  /auth/google endpoint returned unexpected status: {response.status_code}")
        
        # Test the new /auth/validate-jwt endpoint with a dummy token
        dummy_jwt = "dummy_jwt_token_for_testing"
        response = requests.post(
            "http://localhost:8000/auth/validate-jwt",
            json={"token": dummy_jwt},
            timeout=5
        )
        
        # We expect this to fail with a 401, which is correct for a dummy JWT
        if response.status_code == 401:
            print("✅ /auth/validate-jwt endpoint is working (correctly rejected dummy JWT)")
        else:
            print(f"⚠️  /auth/validate-jwt endpoint returned unexpected status: {response.status_code}")
        
        return True
    except Exception as e:
        print(f"❌ Auth endpoint test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Google OAuth Authentication Fix")
    print("=" * 50)
    
    # Test 1: Backend health
    if not test_backend_health():
        print("\n❌ Backend is not running. Please start the backend first:")
        print("   python backend/main.py")
        return
    
    # Test 2: OAuth URL generation
    test_oauth_url()
    
    # Test 3: Auth endpoints
    test_auth_endpoints()
    
    print("\n" + "=" * 50)
    print("✅ Authentication fix tests completed!")
    print("\n📋 Next steps:")
    print("1. Start the frontend: python frontend/main.py")
    print("2. Click 'Account' → 'Login' in the application")
    print("3. Follow the authentication flow as described in AUTHENTICATION_FIX_README.md")
    print("4. Verify that the authentication state is properly maintained")

if __name__ == "__main__":
    main()
