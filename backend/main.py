import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
import uvicorn
import uuid
import logging
from datetime import datetime

logging.basicConfig(level=logging.DEBUG)

from backend.database import create_tables, get_db, User, SessionLocal
from backend.documents import DocumentProcessor, save_uploaded_file
from backend.llm import RAGService
from backend.auth import auth_service, get_current_user
from shared.models import *

app = FastAPI(title="RAG Companion API", version="1.0.0")

# Initialize services
doc_processor = DocumentProcessor()
rag_service = RAGService()

# Pydantic models for backward compatibility
class QueryRequest(BaseModel):
    query: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None

class QueryResponse(BaseModel):
    response: str
    sources: List[dict] = []
    session_id: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    services: dict
    timestamp: datetime

# Initialize database on startup
@app.on_event("startup")
async def startup():
    create_tables()

# Authentication endpoints
@app.post("/auth/google", response_model=TokenResponse)
async def google_auth(request: GoogleTokenRequest):
    """Authenticate with Google OAuth token (direct token)"""
    try:
        google_user_data = auth_service.verify_google_token(request.token)
        user_data = auth_service.get_or_create_user(google_user_data)
        
        token = auth_service.create_jwt_token({
            "user_id": user_data['id'],
            "email": user_data['email'],
            "name": user_data['name'],
            "picture": google_user_data.get("picture", "")
        })
        
        return TokenResponse(
            access_token=token,
            user={
                "id": str(user_data['id']),
                "email": user_data['email'],
                "name": user_data['name'],
                "picture": google_user_data.get("picture", ""),
                "created_at": user_data['created_at'].isoformat()
            }
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

@app.post("/auth/validate-jwt", response_model=TokenResponse)
async def validate_jwt_token(request: GoogleTokenRequest):
    """Validate JWT token and return user info"""
    try:
        # Validate the JWT token
        payload = auth_service.validate_jwt_token(request.token)
        
        # Get user from database
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == payload["sub"]).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Update last login
            user.last_login = datetime.utcnow()
            db.commit()
            
            return TokenResponse(
                access_token=request.token,  # Return the same token
                user={
                    "id": str(user.id),
                    "email": user.email,
                    "name": user.name,
                    "picture": payload.get("picture", ""),
                    "created_at": user.created_at.isoformat()
                }
            )
        finally:
            db.close()
            
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token validation failed: {str(e)}")

@app.get("/auth/callback")
async def oauth_callback(code: str = None, error: str = None):
    """Handle OAuth callback from Google - PROFESSIONAL VERSION"""
    if error:
        # Redirect to frontend with error
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authentication Failed - RAG Companion AI</title>
            <style>
                body {{ 
                    font-family: 'Segoe UI', Arial, sans-serif; 
                    margin: 0; 
                    padding: 40px;
                    text-align: center; 
                    background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }}
                .container {{
                    background: white;
                    padding: 40px;
                    border-radius: 12px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                    max-width: 500px;
                }}
                .error {{ color: #dc3545; font-size: 28px; margin-bottom: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="error">âŒ Authentication Failed</div>
                <p><strong>Error:</strong> {error}</p>
                <p>Please try again or contact support if the issue persists.</p>
                <button onclick="window.close()">Close Window</button>
            </div>
        </body>
        </html>
        """)
    
    if not code:
        raise HTTPException(status_code=400, detail="No authorization code provided")
    
    try:
        # Exchange code for user data
        google_user_data = auth_service.exchange_code_for_token(code)
        user_data = auth_service.get_or_create_user(google_user_data)
        
        # Create JWT token
        token = auth_service.create_jwt_token({
            "user_id": user_data['id'],
            "email": user_data['email'],
            "name": user_data['name'],
            "picture": google_user_data.get("picture", "")
        })
        
        # Return success page with token for the frontend to capture
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authentication Successful - RAG Companion AI</title>
            <style>
                body {{ 
                    font-family: 'Segoe UI', Arial, sans-serif; 
                    margin: 0; 
                    padding: 40px;
                    text-align: center; 
                    background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }}
                .container {{
                    background: white;
                    padding: 40px;
                    border-radius: 12px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                    max-width: 500px;
                }}
                .success {{ color: #28a745; font-size: 28px; margin-bottom: 20px; }}
                .user-info {{
                    background: #f8f9fa;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                    border-left: 4px solid #28a745;
                }}
                .token-section {{
                    margin: 20px 0;
                    padding: 20px;
                    background: #f8f9fa;
                    border-radius: 8px;
                    border: 2px solid #0078d4;
                }}
                .token-display {{
                    display: flex;
                    align-items: center;
                    margin: 10px 0;
                }}
                .token-display code {{
                    background: #e9ecef;
                    padding: 10px;
                    border-radius: 4px;
                    font-family: monospace;
                    font-size: 12px;
                    word-break: break-all;
                    flex: 1;
                    margin-right: 10px;
                }}
                .countdown {{ 
                    margin-top: 20px; 
                    padding: 10px; 
                    background: #e9ecef; 
                    border-radius: 4px; 
                    font-weight: bold;
                }}
                .hidden {{ display: none; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success">âœ… Login Successful!</div>
                <p><strong>Welcome to RAG Companion AI!</strong></p>
                
                <div class="user-info">
                    <h4>Logged in as:</h4>
                    <p><strong>{user_data['name']}</strong></p>
                    <p>{user_data['email']}</p>
                </div>
                
                <p>ðŸŽ‰ Authentication completed successfully!</p>
                <p>The application will now have access to your personal documents and cloud features.</p>
                
                <div class="token-section">
                    <h4>🔑 Authentication Token:</h4>
                    <div class="token-display" id="token-display">
                        <code>{token}</code>
                        <button onclick="copyToken()" style="margin-left: 10px; padding: 5px 10px; background: #0078d4; color: white; border: none; border-radius: 4px; cursor: pointer;">Copy Token</button>
                    </div>
                    <p style="font-size: 12px; color: #666; margin-top: 10px;">
                        Copy this token and paste it in the RAG Companion AI application to complete your login.
                    </p>
                </div>
                
                <div class="countdown" id="countdown">
                    This window will close automatically in <span id="timer">30</span> seconds...
                </div>
                
                <!-- Hidden data for frontend to access -->
                <div id="auth-data" class="hidden" 
                     data-token="{token}"
                     data-user-id="{user_data['id']}"
                     data-user-name="{user_data['name']}"
                     data-user-email="{user_data['email']}"
                     data-user-picture="{google_user_data.get('picture', '')}">
                </div>
            </div>
            <script>
                // Store auth data in localStorage for the main app to pick up
                const authData = {{
                    token: "{token}",
                    user: {{
                        id: "{user_data['id']}",
                        name: "{user_data['name']}",
                        email: "{user_data['email']}",
                        picture: "{google_user_data.get('picture', '')}"
                    }}
                }};
                
                try {{
                    localStorage.setItem('rag_auth_data', JSON.stringify(authData));
                    console.log('Auth data stored successfully');
                }} catch(e) {{
                    console.error('Failed to store auth data:', e);
                }}
                
                // Copy token function
                function copyToken() {{
                    const token = "{token}";
                    navigator.clipboard.writeText(token).then(() => {{
                        const button = document.querySelector('#token-display button');
                        button.textContent = 'Copied!';
                        button.style.background = '#28a745';
                        setTimeout(() => {{
                            button.textContent = 'Copy Token';
                            button.style.background = '#0078d4';
                        }}, 2000);
                    }}).catch(err => {{
                        console.error('Failed to copy token:', err);
                        alert('Failed to copy token. Please copy it manually.');
                    }});
                }}
                
                // Countdown timer
                let timeLeft = 30;
                const timer = document.getElementById('timer');
                const countdown = setInterval(() => {{
                    timeLeft--;
                    timer.textContent = timeLeft;
                    if (timeLeft <= 0) {{
                        clearInterval(countdown);
                        window.close();
                    }}
                }}, 1000);
                
                // Also try to communicate with parent window
                if (window.opener) {{
                    try {{
                        window.opener.postMessage({{
                            type: 'RAG_AUTH_SUCCESS',
                            data: authData
                        }}, '*');
                    }} catch(e) {{
                        console.log('Could not post message to opener');
                    }}
                }}
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth callback error: {str(e)}")

@app.post("/auth/refresh")
async def refresh_token(token: str):
    """Refresh JWT token"""
    try:
        new_token = auth_service.refresh_token(token)
        return {"access_token": new_token, "token_type": "bearer"}
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token refresh failed: {str(e)}")

@app.get("/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "name": current_user.name,
        "created_at": current_user.created_at.isoformat(),
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None
    }

# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    status = rag_service.get_service_status()
    return HealthResponse(
        status="healthy",
        services=status,
        timestamp=datetime.utcnow()
    )

# Legacy health endpoint for backward compatibility
@app.get("/health/simple")
async def health_check_simple():
    """Simple health check endpoint - legacy"""
    status = rag_service.get_service_status()
    return {
        "status": "healthy",
        "services": status
    }

# Document upload endpoints
@app.post("/upload", response_model=Dict[str, str])
async def upload_document(
    file: UploadFile = File(...), 
    current_user: User = Depends(get_current_user)
):
    """Upload and process document (authenticated)"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    try:
        file_content = await file.read()
        file_path = save_uploaded_file(file_content, file.filename)
        document_id = doc_processor.process_document(file_path, file.filename, str(current_user.id))
        
        return {
            "message": "Document uploaded and processed successfully",
            "document_id": document_id,
            "filename": file.filename
        }
    except Exception as e:
        import traceback
        print(f"Upload error: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

# Legacy upload endpoint for backward compatibility
@app.post("/upload/legacy")
async def upload_document_legacy(file: UploadFile = File(...), user_id: str = "test_user"):
    """Upload and process document (legacy - no authentication)"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    try:
        # Save file
        file_content = await file.read()
        file_path = save_uploaded_file(file_content, file.filename)
        
        # Process document
        document_id = doc_processor.process_document(file_path, file.filename, user_id)
        
        return {
            "message": "Document uploaded and processed successfully",
            "document_id": document_id,
            "filename": file.filename
        }
        
    except Exception as e:
        import traceback
        print(f"Upload error: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

# Document listing endpoints
@app.get("/documents", response_model=DocumentListResponse)
async def list_user_documents(current_user: User = Depends(get_current_user)):
    """List current user's documents (authenticated)"""
    try:
        from backend.documents import get_user_documents
        documents = get_user_documents(str(current_user.id))
        return DocumentListResponse(documents=documents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

# Legacy document listing endpoint
@app.get("/documents/{user_id}")
async def list_documents(user_id: str):
    """List user documents - legacy endpoint"""
    try:
        from backend.documents import get_user_documents
        documents = get_user_documents(user_id)
        return {"documents": documents}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

# Document deletion endpoint
@app.delete("/documents/{document_id}")
async def delete_document(
    document_id: str, 
    current_user: User = Depends(get_current_user)
):
    """Delete a document"""
    try:
        from backend.documents import delete_user_document
        success = delete_user_document(document_id, str(current_user.id))
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        return {"message": "Document deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

# Query endpoints
@app.post("/query", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest, 
    current_user: User = Depends(get_current_user)
):
    """Query documents using RAG (authenticated)"""
    try:
        response_parts = []
        for chunk in rag_service.query_documents(request.query, str(current_user.id), stream=False):
            response_parts.append(chunk)
        
        return QueryResponse(
            response="".join(response_parts),
            sources=[],
            session_id=request.session_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

# Legacy query endpoint for backward compatibility
@app.post("/query/legacy")
async def query_documents_legacy(request: QueryRequest):
    """Query documents using RAG (legacy - no authentication)"""
    try:
        # Use user_id from request or default
        user_id = request.user_id or "test_user"
        
        response_parts = []
        for chunk in rag_service.query_documents(request.query, user_id, stream=False):
            response_parts.append(chunk)
        
        return QueryResponse(
            response="".join(response_parts),
            sources=[],  # TODO: Add source information
            session_id=request.session_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)