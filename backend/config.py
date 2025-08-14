import os
from pathlib import Path
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5433/ragbot"
    
    # Vector Database - Updated port
    QDRANT_URL: str = "http://localhost:6340"
    QDRANT_API_KEY: str = ""
    
    # AI Models
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    LLM_MODEL: str = "gemma3:1b-it-qat"
    OLLAMA_URL: str = "http://localhost:11434"
    
    # External APIs
    TAVILY_API_KEY: str = ""
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    
    # Application
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    UPLOAD_DIR: Path = Path("uploads")
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50
    MAX_CONTEXT_LENGTH: int = 4000
    
    class Config:
        env_file = ".env"

settings = Settings()

# Ensure upload directory exists
settings.UPLOAD_DIR.mkdir(exist_ok=True)