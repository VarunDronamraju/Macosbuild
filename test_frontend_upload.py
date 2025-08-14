#!/usr/bin/env python3
"""
Test script to simulate frontend upload process
"""

import requests
import os
from pathlib import Path

def simulate_frontend_upload():
    """Simulate the exact frontend upload process"""
    print("🧪 Simulating Frontend Upload Process")
    
    # Create a test file in the uploads directory (like the frontend would)
    uploads_dir = "uploads"
    if not os.path.exists(uploads_dir):
        os.makedirs(uploads_dir)
    
    test_file_path = os.path.join(uploads_dir, "test_frontend_doc.txt")
    test_content = "This is a test document for frontend upload simulation."
    
    with open(test_file_path, "w") as f:
        f.write(test_content)
    
    print(f"Created test file: {test_file_path}")
    print(f"File size: {os.path.getsize(test_file_path)} bytes")
    
    try:
        # Simulate the exact API client upload process
        filename = Path(test_file_path).name
        print(f"Uploading filename: {filename}")
        
        # Check if file exists (like the API client does)
        if not os.path.exists(test_file_path):
            print(f"❌ File not found: {test_file_path}")
            return
        
        print(f"✅ File exists: {test_file_path}")
        print(f"File size: {os.path.getsize(test_file_path)} bytes")
        
        # Simulate the upload (without authentication for now)
        with open(test_file_path, 'rb') as file:
            # Determine content type based on file extension
            content_type = 'application/octet-stream'
            if filename.lower().endswith('.txt'):
                content_type = 'text/plain'
            elif filename.lower().endswith('.pdf'):
                content_type = 'application/pdf'
            elif filename.lower().endswith(('.doc', '.docx')):
                content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            
            files = {'file': (filename, file, content_type)}
            
            print(f"Content type: {content_type}")
            print(f"Files dict: {files}")
            
            # Create a clean session for file upload
            upload_session = requests.Session()
            
            print(f"Uploading to: http://localhost:8000/upload")
            response = upload_session.post(
                "http://localhost:8000/upload",
                files=files
            )
            
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
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
        print(f"Cleaned up test file: {test_file_path}")

if __name__ == "__main__":
    simulate_frontend_upload()
