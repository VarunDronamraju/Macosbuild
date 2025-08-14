from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

# Authentication Models
class GoogleTokenRequest(BaseModel):
    token: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

# Document Models
class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size: int
    upload_date: datetime
    processing_status: str
    chunk_count: int

class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]

# RAG Models
class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

class QueryResponse(BaseModel):
    response: str
    sources: List[Dict[str, Any]] = []
    session_id: Optional[str] = None

# Chat Models
class ChatSessionResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

class ChatSessionListResponse(BaseModel):
    sessions: List[ChatSessionResponse]

class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    timestamp: datetime

class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: List[ChatMessageResponse]

class SendMessageRequest(BaseModel):
    message: str

class SendMessageResponse(BaseModel):
    message: ChatMessageResponse
    session_id: str

# System Models
class HealthResponse(BaseModel):
    status: str
    services: Dict[str, bool]
    timestamp: datetime

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    created_at: datetime