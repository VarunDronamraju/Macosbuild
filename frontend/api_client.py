"""
API Client for communicating with the RAG backend
Handles authentication, document management, and chat functionality
"""

import requests
import json
import os
from typing import Dict, List, Optional, Iterator, Any
from pathlib import Path
import logging
from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class APIClient(QObject):
    """Main API client for backend communication"""
    
    # Signals
    connection_status_changed = pyqtSignal(bool)
    authentication_changed = pyqtSignal(bool, dict)
    upload_progress = pyqtSignal(str, int)  # filename, percentage
    upload_completed = pyqtSignal(str, dict)  # filename, result
    upload_failed = pyqtSignal(str, str)  # filename, error
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        super().__init__()
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.access_token = None
        self.user_info = None
        self.is_online = False
        
        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        logger.info(f"API Client initialized with base URL: {self.base_url}")
    
    def set_auth_token(self, token: str, user_info: Dict = None):
        """Set authentication token"""
        self.access_token = token
        self.user_info = user_info
        
        if token:
            self.session.headers.update({
                'Authorization': f'Bearer {token}'
            })
        else:
            self.session.headers.pop('Authorization', None)
        
        self.authentication_changed.emit(bool(token), user_info or {})
        logger.info(f"Authentication token {'set' if token else 'cleared'}")
    
    def check_health(self) -> bool:
        """Check if backend is available"""
        try:
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=5
            )
            
            is_healthy = response.status_code == 200
            
            if is_healthy != self.is_online:
                self.is_online = is_healthy
                self.connection_status_changed.emit(is_healthy)
                logger.info(f"Connection status changed: {'online' if is_healthy else 'offline'}")
            
            return is_healthy
            
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            if self.is_online:
                self.is_online = False
                self.connection_status_changed.emit(False)
            return False
    
    def authenticate_google(self, google_token: str) -> Dict:
        """Authenticate with Google OAuth token"""
        try:
            response = self.session.post(
                f"{self.base_url}/auth/google",
                json={"token": google_token}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.set_auth_token(data["access_token"], data["user"])
                return {"success": True, "data": data}
            else:
                error_msg = response.json().get("detail", "Authentication failed")
                logger.error(f"Google authentication failed: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            logger.error(f"Google authentication error: {e}")
            return {"success": False, "error": str(e)}
    
    def validate_jwt_token(self, jwt_token: str) -> Dict:
        """Validate JWT token from OAuth callback"""
        try:
            response = self.session.post(
                f"{self.base_url}/auth/validate-jwt",
                json={"token": jwt_token}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.set_auth_token(data["access_token"], data["user"])
                return {"success": True, "data": data}
            else:
                error_msg = response.json().get("detail", "Token validation failed")
                logger.error(f"JWT token validation failed: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            logger.error(f"JWT token validation error: {e}")
            return {"success": False, "error": str(e)}
    
    def upload_document(self, file_path: str, filename: str = None) -> Dict:
        """Upload a document for processing"""
        if not filename:
            filename = Path(file_path).name
        
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                error_msg = f"File not found: {file_path}"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}
            
            print(f"File exists: {file_path}")
            print(f"File size: {os.path.getsize(file_path)} bytes")
            
            with open(file_path, 'rb') as file:
                # Determine content type based on file extension
                content_type = 'application/octet-stream'
                if filename.lower().endswith('.txt'):
                    content_type = 'text/plain'
                elif filename.lower().endswith('.pdf'):
                    content_type = 'application/pdf'
                elif filename.lower().endswith(('.doc', '.docx')):
                    content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                
                files = {'file': (filename, file, content_type)}
                
                # Create a clean session for file upload to avoid header conflicts
                upload_session = requests.Session()
                
                # Add authorization header if available
                if self.access_token:
                    upload_session.headers['Authorization'] = f'Bearer {self.access_token}'
                    print(f"✅ Using auth token: {self.access_token[:20]}...")
                else:
                    print("❌ No auth token available")
                
                print(f"Uploading file: {filename}")
                print(f"Content type: {content_type}")
                print(f"Headers: {upload_session.headers}")
                print(f"Files dict: {files}")
                
                response = upload_session.post(
                    f"{self.base_url}/upload",
                    files=files
                )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Document uploaded successfully: {filename}")
                return {"success": True, "data": data}
            else:
                try:
                    error_detail = response.json()
                    print(f"Error response: {error_detail}")
                    
                    if isinstance(error_detail, list):
                        # Handle validation error list
                        error_msg = "; ".join([f"{err.get('loc', [])}: {err.get('msg', 'Unknown error')}" for err in error_detail])
                    else:
                        error_msg = error_detail.get("detail", "Upload failed")
                except Exception as parse_error:
                    print(f"Error parsing response: {parse_error}")
                    error_msg = f"Upload failed with status {response.status_code}"
                
                logger.error(f"Document upload failed: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            logger.error(f"Document upload error: {e}")
            return {"success": False, "error": str(e)}
    
    def upload_document_legacy(self, file_path: str, filename: str = None, user_id: str = "test_user") -> Dict:
        """Upload document using legacy endpoint (for offline mode)"""
        if not filename:
            filename = Path(file_path).name
        
        try:
            with open(file_path, 'rb') as file:
                files = {'file': (filename, file, 'application/octet-stream')}
                data = {'user_id': user_id}
                
                # Create a new session for this request to avoid header conflicts
                temp_session = requests.Session()
                
                response = temp_session.post(
                    f"{self.base_url}/upload/legacy",
                    files=files,
                    data=data
                )
            
            if response.status_code == 200:
                result_data = response.json()
                logger.info(f"Document uploaded successfully (legacy): {filename}")
                return {"success": True, "data": result_data}
            else:
                try:
                    error_detail = response.json()
                    if isinstance(error_detail, list):
                        error_msg = str(error_detail)
                    else:
                        error_msg = error_detail.get("detail", "Upload failed")
                except:
                    error_msg = f"Upload failed with status {response.status_code}"
                
                logger.error(f"Document upload failed (legacy): {error_msg}")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            logger.error(f"Document upload error (legacy): {e}")
            return {"success": False, "error": str(e)}
    
    def get_documents(self) -> Dict:
        """Get user's documents"""
        try:
            response = self.session.get(f"{self.base_url}/documents")
            
            if response.status_code == 200:
                data = response.json()
                return {"success": True, "documents": data.get("documents", [])}
            else:
                error_msg = response.json().get("detail", "Failed to get documents")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            logger.error(f"Get documents error: {e}")
            return {"success": False, "error": str(e)}
    
    def get_documents_legacy(self, user_id: str = "test_user") -> Dict:
        """Get documents using legacy endpoint"""
        try:
            # Remove authorization header for legacy endpoint
            headers = {k: v for k, v in self.session.headers.items() 
                      if k.lower() != 'authorization'}
            
            response = self.session.get(
                f"{self.base_url}/documents/{user_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                return {"success": True, "documents": data.get("documents", [])}
            else:
                error_msg = response.json().get("detail", "Failed to get documents")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            logger.error(f"Get documents error (legacy): {e}")
            return {"success": False, "error": str(e)}
    
    def delete_document(self, document_id: str) -> Dict:
        """Delete a document"""
        try:
            response = self.session.delete(f"{self.base_url}/documents/{document_id}")
            
            if response.status_code == 200:
                logger.info(f"Document deleted successfully: {document_id}")
                return {"success": True}
            else:
                error_msg = response.json().get("detail", "Failed to delete document")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            logger.error(f"Delete document error: {e}")
            return {"success": False, "error": str(e)}
    
    def query_documents(self, query: str, session_id: str = None) -> Dict:
        """Query documents using RAG"""
        try:
            payload = {"query": query}
            if session_id:
                payload["session_id"] = session_id
            
            response = self.session.post(
                f"{self.base_url}/query",
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                return {"success": True, "data": data}
            else:
                error_msg = response.json().get("detail", "Query failed")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            logger.error(f"Query error: {e}")
            return {"success": False, "error": str(e)}
    
    def query_documents_legacy(self, query: str, user_id: str = "test_user", session_id: str = None) -> Dict:
        """Query documents using legacy endpoint"""
        try:
            payload = {
                "query": query,
                "user_id": user_id
            }
            if session_id:
                payload["session_id"] = session_id
            
            # Remove authorization header for legacy endpoint
            headers = {k: v for k, v in self.session.headers.items() 
                      if k.lower() != 'authorization'}
            
            response = self.session.post(
                f"{self.base_url}/query/legacy",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                return {"success": True, "data": data}
            else:
                error_msg = response.json().get("detail", "Query failed")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            logger.error(f"Query error (legacy): {e}")
            return {"success": False, "error": str(e)}

class StreamingQueryThread(QThread):
    """Thread for handling streaming RAG queries"""
    
    chunk_received = pyqtSignal(str)
    query_completed = pyqtSignal(list)  # Now includes sources
    query_failed = pyqtSignal(str)
    
    def __init__(self, api_client: APIClient, query: str, session_id: str = None, use_legacy: bool = False, user_id: str = "test_user"):
        super().__init__()
        self.api_client = api_client
        self.query = query
        self.session_id = session_id
        self.use_legacy = use_legacy
        self.user_id = user_id
        self.is_running = True
    
    def run(self):
        """Run streaming query"""
        try:
            # For now, use regular query since streaming is not implemented in backend
            if self.use_legacy:
                result = self.api_client.query_documents_legacy(
                    self.query, self.user_id, self.session_id
                )
            else:
                result = self.api_client.query_documents(self.query, self.session_id)
            
            if result["success"]:
                response_text = result["data"]["response"]
                sources = result["data"].get("sources", [])
                
                # Simulate streaming by sending chunks
                words = response_text.split()
                chunk_size = 3  # Words per chunk
                
                for i in range(0, len(words), chunk_size):
                    if not self.is_running:
                        break
                    
                    chunk = " ".join(words[i:i + chunk_size]) + " "
                    self.chunk_received.emit(chunk)
                    
                    # Small delay to simulate streaming
                    self.msleep(50)
                
                self.query_completed.emit(sources)
            else:
                self.query_failed.emit(result["error"])
                
        except Exception as e:
            self.query_failed.emit(str(e))
    
    def stop(self):
        """Stop the streaming query"""
        self.is_running = False