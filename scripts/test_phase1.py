import requests
import json
import time
from pathlib import Path

API_BASE = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("Testing health endpoint...")
    try:
        response = requests.get(f"{API_BASE}/health")
        if response.status_code == 200:
            data = response.json()
            print("✓ Health check passed")
            print(f"  Services: {data.get('services', {})}")
            return True
        else:
            print(f"✗ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False

def test_document_upload():
    """Test document upload"""
    print("\nTesting document upload...")
    
    # Create a test document
    test_content = """This is a test document for the RAG system.
It contains information about artificial intelligence and machine learning.
Machine learning is a subset of artificial intelligence.
Natural language processing is another important field in AI."""
    
    test_file = Path("test_document.txt")
    with open(test_file, 'w') as f:
        f.write(test_content)
    
    try:
        with open(test_file, 'rb') as f:
            files = {'file': ('test_document.txt', f, 'text/plain')}
            data = {'user_id': 'test_user'}
            response = requests.post(f"{API_BASE}/upload", files=files, data=data)
        
        if response.status_code == 200:
            result = response.json()
            print("✓ Document upload successful")
            print(f"  Document ID: {result.get('document_id')}")
            return True
        else:
            print(f"✗ Document upload failed: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Document upload failed: {e}")
        return False
    finally:
        # Clean up
        if test_file.exists():
            test_file.unlink()

def test_query():
    """Test RAG query"""
    print("\nTesting RAG query...")
    
    # Wait a moment for document processing
    time.sleep(2)
    
    try:
        query_data = {
            "query": "What is machine learning?",
            "user_id": "test_user"
        }
        response = requests.post(f"{API_BASE}/query", json=query_data)
        
        if response.status_code == 200:
            result = response.json()
            print("✓ RAG query successful")
            print(f"  Response: {result.get('response')[:200]}...")
            return True
        else:
            print(f"✗ RAG query failed: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
    except Exception as e:
        print(f"✗ RAG query failed: {e}")
        return False

def test_document_list():
    """Test document listing"""
    print("\nTesting document listing...")
    try:
        response = requests.get(f"{API_BASE}/documents/test_user")
        
        if response.status_code == 200:
            result = response.json()
            documents = result.get('documents', [])
            print("✓ Document listing successful")
            print(f"  Found {len(documents)} documents")
            return True
        else:
            print(f"✗ Document listing failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Document listing failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Running Phase 1 integration tests...\n")
    
    tests = [
        test_health,
        test_document_upload,
        test_query,
        test_document_list
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n{'='*50}")
    print(f"Test Results: {passed}/{total} tests passed")
    print(f"{'='*50}")
    
    if passed == total:
        print("🎉 All tests passed! Phase 1 is working correctly.")
    else:
        print("⚠ Some tests failed. Please check the errors above.")

if __name__ == "__main__":
    main()