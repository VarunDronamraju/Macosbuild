import os
from pathlib import Path
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://postgres:qwerty12345@localhost:5433/ragbot"
    
    # Vector Database - Updated port
    QDRANT_URL: str = "http://localhost:6340"
    QDRANT_API_KEY: str = ""
    
    # AI Models
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    LLM_MODEL: str = "gemma3:1b-it-qat"
    OLLAMA_URL: str = "http://localhost:11434"
    
    # External APIs
    TAVILY_API_KEY: str = "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"
    GOOGLE_CLIENT_ID: str = "778657599269-ouflj5id5r0bchm9a8lcko1tskkk4j4f.apps.googleusercontent.com"
    GOOGLE_CLIENT_SECRET: str = "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"
    
    # Application
    SECRET_KEY: str = "kJ8mN2pQ5sT9vY3wZ6aD1fH4jL7nR0uX8bE5hK2mP9sV6yB3eG1iL4oR7tA0cF3h"
    UPLOAD_DIR: Path = Path("uploads")
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50
    MAX_CONTEXT_LENGTH: int = 4000
    
    class Config:
        env_file = ".env"

settings = Settings()

# Ensure upload directory exists
settings.UPLOAD_DIR.mkdir(exist_ok=True)