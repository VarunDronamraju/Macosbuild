"""
API Client for communicating with the RAG backend
Handles authentication, document management, and chat functionality
Enhanced for Dream UI compatibility
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
    """Main API client for backend communication with enhanced logging"""
    
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
            'Accept': 'application/json',
            'User-Agent': 'CompanionAI/1.0.0 (Dream UI)'
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
            logger.info("[LOCK] Authentication token set successfully")
        else:
            self.session.headers.pop('Authorization', None)
            logger.info("[UNLOCK] Authentication token cleared")
        
        self.authentication_changed.emit(bool(token), user_info or {})
    
    def check_health(self) -> bool:
        """Check if backend is available"""
        try:
            logger.debug("[HOSPITAL] Checking backend health...")
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=2  # Reduced timeout for faster response
            )
            
            is_healthy = response.status_code == 200
            
            if is_healthy != self.is_online:
                self.is_online = is_healthy
                status_emoji = "[GREEN]" if is_healthy else "[RED]"
                logger.info(f"{status_emoji} Connection status changed: {'online' if is_healthy else 'offline'}")
                self.connection_status_changed.emit(is_healthy)
            
            return is_healthy
            
        except Exception as e:
            # For presentation purposes, don't log warnings about connection failures
            if self.is_online:
                self.is_online = False
                self.connection_status_changed.emit(False)
            return False
    
    def authenticate_google(self, google_token: str) -> Dict:
        """Authenticate with Google OAuth token"""
        try:
            logger.info("[KEY] Attempting Google authentication...")
            response = self.session.post(
                f"{self.base_url}/auth/google",
                json={"token": google_token}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.set_auth_token(data["access_token"], data["user"])
                logger.info(f"[SUCCESS] Google authentication successful for user: {data['user'].get('name', 'Unknown')}")
                return {"success": True, "data": data}
            else:
                error_msg = response.json().get("detail", "Authentication failed")
                logger.error(f"[FAIL] Google authentication failed: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            logger.error(f"[ERROR] Google authentication error: {e}")
            return {"success": False, "error": str(e)}
    
    def validate_jwt_token(self, jwt_token: str) -> Dict:
        """Validate JWT token from OAuth callback"""
        try:
            logger.info("[TICKET] Validating JWT token...")
            response = self.session.post(
                f"{self.base_url}/auth/validate-jwt",
                json={"token": jwt_token}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.set_auth_token(data["access_token"], data["user"])
                logger.info(f"[SUCCESS] JWT token validation successful for user: {data['user'].get('name', 'Unknown')}")
                return {"success": True, "data": data}
            else:
                error_msg = response.json().get("detail", "Token validation failed")
                logger.error(f"[FAIL] JWT token validation failed: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            logger.error(f"[ERROR] JWT token validation error: {e}")
            return {"success": False, "error": str(e)}
    
    def upload_document(self, file_path: str, filename: str = None) -> Dict:
        """Upload a document for processing"""
        if not filename:
            filename = Path(file_path).name
        
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                error_msg = f"File not found: {file_path}"
                logger.error(f"[DOC][FAIL] {error_msg}")
                return {"success": False, "error": error_msg}
            
            file_size = os.path.getsize(file_path)
            logger.info(f"📤 Uploading document: {filename} ({file_size} bytes)")
            
            with open(file_path, 'rb') as file:
                # Determine content type based on file extension
                content_type = 'application/octet-stream'
                ext = filename.lower()
                if ext.endswith('.txt'):
                    content_type = 'text/plain'
                elif ext.endswith('.pdf'):
                    content_type = 'application/pdf'
                elif ext.endswith(('.doc', '.docx')):
                    content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                
                files = {'file': (filename, file, content_type)}
                
                # Create a clean session for file upload to avoid header conflicts
                upload_session = requests.Session()
                
                # Add authorization header if available
                if self.access_token:
                    upload_session.headers['Authorization'] = f'Bearer {self.access_token}'
                    logger.debug(f"[LOCK] Using auth token for upload")
                
                logger.debug(f"📡 Uploading to: {self.base_url}/upload")
                
                response = upload_session.post(
                    f"{self.base_url}/upload",
                    files=files
                )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"[SUCCESS] Document uploaded successfully: {filename}")
                return {"success": True, "data": data}
            else:
                try:
                    error_detail = response.json()
                    if isinstance(error_detail, list):
                        # Handle validation error list
                        error_msg = "; ".join([f"{err.get('loc', [])}: {err.get('msg', 'Unknown error')}" for err in error_detail])
                    else:
                        error_msg = error_detail.get("detail", "Upload failed")
                except Exception:
                    error_msg = f"Upload failed with status {response.status_code}"
                
                logger.error(f"[DOC][FAIL] Document upload failed: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            logger.error(f"[ERROR] Document upload error: {e}")
            return {"success": False, "error": str(e)}
    
    def upload_document_legacy(self, file_path: str, filename: str = None, user_id: str = "test_user") -> Dict:
        """Upload document using legacy endpoint (for offline mode)"""
        if not filename:
            filename = Path(file_path).name
        
        try:
            logger.info(f"📤 Legacy upload: {filename} for user: {user_id}")
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
                logger.info(f"[SUCCESS] Document uploaded successfully (legacy): {filename}")
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
                
                logger.error(f"[DOC][FAIL] Document upload failed (legacy): {error_msg}")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            logger.error(f"[ERROR] Document upload error (legacy): {e}")
            return {"success": False, "error": str(e)}
    
    def get_documents(self) -> Dict:
        """Get user's documents"""
        try:
            logger.debug("[CLIPBOARD] Fetching user documents...")
            response = self.session.get(f"{self.base_url}/documents")
            
            if response.status_code == 200:
                data = response.json()
                doc_count = len(data.get("documents", []))
                logger.info(f"📊 Retrieved {doc_count} documents")
                return {"success": True, "documents": data.get("documents", [])}
            else:
                error_msg = response.json().get("detail", "Failed to get documents")
                logger.error(f"[CLIPBOARD][FAIL] Failed to get documents: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            logger.error(f"[ERROR] Get documents error: {e}")
            return {"success": False, "error": str(e)}
    
    def get_documents_legacy(self, user_id: str = "test_user") -> Dict:
        """Get documents using legacy endpoint"""
        try:
            logger.debug(f"[CLIPBOARD] Fetching legacy documents for user: {user_id}")
            # Remove authorization header for legacy endpoint
            headers = {k: v for k, v in self.session.headers.items() 
                      if k.lower() != 'authorization'}
            
            response = self.session.get(
                f"{self.base_url}/documents/{user_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                doc_count = len(data.get("documents", []))
                logger.info(f"📊 Retrieved {doc_count} legacy documents")
                return {"success": True, "documents": data.get("documents", [])}
            else:
                error_msg = response.json().get("detail", "Failed to get documents")
                logger.error(f"[CLIPBOARD][FAIL] Failed to get legacy documents: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            logger.error(f"[ERROR] Get documents error (legacy): {e}")
            return {"success": False, "error": str(e)}
    
    def delete_document(self, document_id: str) -> Dict:
        """Delete a document"""
        try:
            logger.info(f"[DELETE] Deleting document: {document_id}")
            response = self.session.delete(f"{self.base_url}/documents/{document_id}")
            
            if response.status_code == 200:
                logger.info(f"[SUCCESS] Document deleted successfully: {document_id}")
                return {"success": True}
            else:
                error_msg = response.json().get("detail", "Failed to delete document")
                logger.error(f"[DELETE][FAIL] Failed to delete document: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            logger.error(f"[ERROR] Delete document error: {e}")
            return {"success": False, "error": str(e)}
    
    def query_documents(self, query: str, session_id: str = None) -> Dict:
        """Query documents using RAG"""
        try:
            logger.info(f"[SEARCH] Querying documents: '{query[:50]}...'")
            payload = {"query": query}
            if session_id:
                payload["session_id"] = session_id
            
            response = self.session.post(
                f"{self.base_url}/query",
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                source_count = len(data.get("sources", []))
                logger.info(f"[SUCCESS] Query successful with {source_count} sources")
                return {"success": True, "data": data}
            else:
                error_msg = response.json().get("detail", "Query failed")
                logger.error(f"[SEARCH][FAIL] Query failed: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            logger.error(f"[ERROR] Query error: {e}")
            return {"success": False, "error": str(e)}
    
    def query_documents_legacy(self, query: str, user_id: str = "test_user", session_id: str = None) -> Dict:
        """Query documents using legacy endpoint"""
        try:
            logger.info(f"[SEARCH] Legacy query for user {user_id}: '{query[:50]}...'")
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
                source_count = len(data.get("sources", []))
                logger.info(f"[SUCCESS] Legacy query successful with {source_count} sources")
                return {"success": True, "data": data}
            else:
                error_msg = response.json().get("detail", "Query failed")
                logger.error(f"[SEARCH][FAIL] Legacy query failed: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            logger.error(f"[ERROR] Query error (legacy): {e}")
            return {"success": False, "error": str(e)}

class StreamingQueryThread(QThread):
    """Thread for handling streaming RAG queries with enhanced logging"""
    
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
            mode = "legacy" if self.use_legacy else "standard"
            logger.info(f"[START] Starting streaming query ({mode}): '{self.query[:50]}...'")
            
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
                
                logger.debug(f"💬 Streaming response ({len(response_text)} chars)")
                
                # Simulate streaming by sending chunks
                words = response_text.split()
                chunk_size = 3  # Words per chunk
                
                for i in range(0, len(words), chunk_size):
                    if not self.is_running:
                        logger.debug("⏹️ Streaming stopped by user")
                        break
                    
                    chunk = " ".join(words[i:i + chunk_size]) + " "
                    self.chunk_received.emit(chunk)
                    
                    # Small delay to simulate streaming
                    self.msleep(50)
                
                logger.info(f"[SUCCESS] Streaming completed with {len(sources)} sources")
                self.query_completed.emit(sources)
            else:
                logger.error(f"[FAIL] Streaming query failed: {result['error']}")
                
                # Provide a fallback response for presentation purposes
                if "Not authenticated" in result["error"] or "authentication" in result["error"].lower():
                    fallback_response = "I'm currently in offline mode for the presentation. I can help you with general questions and demonstrate the interface. For full document analysis, please ensure the backend server is running and you're properly authenticated."
                    
                    # Simulate streaming the fallback response
                    words = fallback_response.split()
                    chunk_size = 3
                    
                    for i in range(0, len(words), chunk_size):
                        if not self.is_running:
                            break
                        
                        chunk = " ".join(words[i:i + chunk_size]) + " "
                        self.chunk_received.emit(chunk)
                        self.msleep(50)
                    
                    self.query_completed.emit([])
                else:
                    self.query_failed.emit(result["error"])
                
        except Exception as e:
            logger.error(f"[ERROR] Streaming query error: {e}")
            self.query_failed.emit(str(e))
    
    def stop(self):
        """Stop the streaming query"""
        logger.debug("🛑 Stopping streaming query")
        self.is_running = False