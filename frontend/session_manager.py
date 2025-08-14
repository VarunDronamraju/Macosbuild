"""
Session Manager for handling local session persistence and chat history
Manages user sessions, chat history, and application state
"""

import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

class ChatSession:
    """Represents a chat session"""
    
    def __init__(self, session_id: str = None, title: str = "New Chat", messages: List = None):
        self.id = session_id or str(uuid.uuid4())
        self.title = title
        self.messages = messages or []
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def add_message(self, role: str, content: str, metadata: Dict = None):
        """Add a message to the session"""
        message = {
            "id": str(uuid.uuid4()),
            "role": role,  # "user" or "assistant"
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        self.messages.append(message)
        self.updated_at = datetime.now()
        
        # Update title if this is the first user message
        if role == "user" and len([m for m in self.messages if m["role"] == "user"]) == 1:
            self.title = content[:50] + "..." if len(content) > 50 else content
    
    def get_message_count(self) -> int:
        """Get total message count"""
        return len(self.messages)
    
    def get_last_message(self) -> Optional[Dict]:
        """Get the last message"""
        return self.messages[-1] if self.messages else None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "title": self.title,
            "messages": self.messages,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ChatSession':
        """Create from dictionary"""
        session = cls(
            session_id=data["id"],
            title=data["title"],
            messages=data["messages"]
        )
        session.created_at = datetime.fromisoformat(data["created_at"])
        session.updated_at = datetime.fromisoformat(data["updated_at"])
        return session

class SessionManager(QObject):
    """Manages user sessions and application state"""
    
    # Signals
    session_created = pyqtSignal(str)  # session_id
    session_updated = pyqtSignal(str)  # session_id
    session_deleted = pyqtSignal(str)  # session_id
    sessions_loaded = pyqtSignal()
    
    def __init__(self, data_dir: Path = None):
        super().__init__()
        
        # Setup data directory
        self.data_dir = data_dir or Path.home() / ".rag_companion"
        self.data_dir.mkdir(exist_ok=True)
        
        # Files
        self.sessions_file = self.data_dir / "sessions.json"
        self.user_file = self.data_dir / "user.json"
        self.settings_file = self.data_dir / "settings.json"
        
        # User-specific session file (will be set when user logs in)
        self.user_sessions_file = None
        
        # Data
        self.sessions: Dict[str, ChatSession] = {}
        self.current_session_id: Optional[str] = None
        self.user_info: Dict = {}
        self.settings: Dict = self.load_default_settings()
        
        # Load existing data
        self.load_data()
        
        logger.info(f"Session manager initialized with data directory: {self.data_dir}")
    
    def load_default_settings(self) -> Dict:
        """Load default application settings"""
        return {
            "window_geometry": None,
            "window_state": None,
            "theme": "dark",
            "auto_save": True,
            "offline_mode": False,
            "last_user_id": None,
            "remember_login": True
        }
    
    def load_data(self):
        """Load all data from disk"""
        self.load_sessions()
        self.load_user_info()
        self.load_settings()
    
    def save_data(self):
        """Save all data to disk"""
        self.save_sessions()
        self.save_user_info()
        self.save_settings()
    
    def cleanup_offline_data(self):
        """Clean up offline/temporary data when app closes"""
        if not self.user_info or not self.user_info.get('email'):
            # Clear all temporary sessions for offline users
            self.sessions = {}
            self.current_session_id = None
            logger.info("Cleaned up offline session data")
            
            # Also clear any anonymous session files
            try:
                anonymous_file = self.data_dir / "sessions_anonymous.json"
                if anonymous_file.exists():
                    anonymous_file.unlink()
                    logger.info("Removed anonymous session file")
            except Exception as e:
                logger.warning(f"Failed to remove anonymous session file: {e}")
    
    def load_sessions(self):
        """Load chat sessions from disk"""
        # For offline mode (no user), don't load any sessions
        if not self.user_sessions_file:
            logger.info("Offline mode - no sessions loaded (temporary only)")
            self.sessions = {}
            self.current_session_id = None
            self.sessions_loaded.emit()
            return
        
        # Use user-specific sessions file
        if not self.user_sessions_file.exists():
            logger.info(f"No existing sessions file for user: {self.user_info.get('email', 'unknown')}")
            self.sessions = {}
            self.current_session_id = None
            self.sessions_loaded.emit()
            return
        
        try:
            with open(self.user_sessions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.sessions = {}
            for session_data in data.get("sessions", []):
                session = ChatSession.from_dict(session_data)
                self.sessions[session.id] = session
            
            self.current_session_id = data.get("current_session_id")
            
            logger.info(f"Loaded {len(self.sessions)} chat sessions for user: {self.user_info.get('email', 'anonymous')}")
            self.sessions_loaded.emit()
            
        except Exception as e:
            logger.error(f"Failed to load sessions: {e}")
            # On error, start with empty sessions
            self.sessions = {}
            self.current_session_id = None
            self.sessions_loaded.emit()
    
    def save_sessions(self):
        """Save chat sessions to disk"""
        # Don't save sessions in offline mode (no user)
        if not self.user_sessions_file:
            logger.debug("Offline mode - sessions not saved (temporary only)")
            return
        
        try:
            data = {
                "sessions": [session.to_dict() for session in self.sessions.values()],
                "current_session_id": self.current_session_id
            }
            
            with open(self.user_sessions_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Saved {len(self.sessions)} chat sessions for user: {self.user_info.get('email', 'anonymous')}")
            
        except Exception as e:
            logger.error(f"Failed to save sessions: {e}")
    
    def load_user_info(self):
        """Load user information from disk"""
        if not self.user_file.exists():
            return
        
        try:
            with open(self.user_file, 'r', encoding='utf-8') as f:
                self.user_info = json.load(f)
            
            logger.info(f"Loaded user info for: {self.user_info.get('email', 'unknown')}")
            
        except Exception as e:
            logger.error(f"Failed to load user info: {e}")
    
    def save_user_info(self):
        """Save user information to disk"""
        try:
            with open(self.user_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_info, f, indent=2)
            
            logger.debug("Saved user info")
            
        except Exception as e:
            logger.error(f"Failed to save user info: {e}")
    
    def load_settings(self):
        """Load application settings from disk"""
        if not self.settings_file.exists():
            return
        
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                saved_settings = json.load(f)
            
            # Merge with defaults
            self.settings.update(saved_settings)
            
            logger.info("Loaded application settings")
            
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
    
    def save_settings(self):
        """Save application settings to disk"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2)
            
            logger.debug("Saved application settings")
            
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
    
    def set_user_info(self, user_info: Dict):
        """Set user information"""
        self.user_info = user_info
        
        # Set user-specific sessions file
        if user_info and user_info.get('email'):
            user_email = user_info['email']
            # Create safe filename from email
            safe_email = user_email.replace('@', '_at_').replace('.', '_')
            self.user_sessions_file = self.data_dir / f"sessions_{safe_email}.json"
            logger.info(f"Switching to user-specific sessions: {self.user_sessions_file}")
        else:
            # For anonymous/offline users, use temporary sessions that won't persist
            self.user_sessions_file = None
            logger.info("Switching to temporary sessions (offline mode)")
        
        # Clear current sessions and load user-specific sessions
        self.sessions = {}
        self.current_session_id = None
        self.load_sessions()
        
        self.save_user_info()
    
    def get_user_info(self) -> Dict:
        """Get user information"""
        return self.user_info
    
    def set_setting(self, key: str, value: Any):
        """Set a setting value"""
        # Convert QByteArray to base64 string for JSON serialization
        if hasattr(value, 'toBase64'):
            value = value.toBase64().data().decode('utf-8')
        
        self.settings[key] = value
        if self.settings.get("auto_save", True):
            self.save_settings()
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value"""
        value = self.settings.get(key, default)
        
        # Convert base64 string back to QByteArray for geometry/state data
        if key in ["window_geometry", "window_state"] and isinstance(value, str):
            try:
                from PyQt6.QtCore import QByteArray
                import base64
                return QByteArray.fromBase64(value.encode('utf-8'))
            except Exception as e:
                logger.warning(f"Failed to convert {key} from base64: {e}")
                return default
        
        return value
    
    def create_session(self, title: str = "New Chat") -> str:
        """Create a new chat session"""
        session = ChatSession(title=title)
        self.sessions[session.id] = session
        self.current_session_id = session.id
        
        if self.settings.get("auto_save", True):
            self.save_sessions()
        
        logger.info(f"Created new session: {session.id}")
        self.session_created.emit(session.id)
        return session.id
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a session by ID"""
        return self.sessions.get(session_id)
    
    def get_current_session(self) -> Optional[ChatSession]:
        """Get the current active session"""
        if self.current_session_id:
            return self.sessions.get(self.current_session_id)
        return None
    
    def set_current_session(self, session_id: str):
        """Set the current active session"""
        if session_id in self.sessions:
            self.current_session_id = session_id
            if self.settings.get("auto_save", True):
                self.save_sessions()
    
    def get_all_sessions(self) -> List[ChatSession]:
        """Get all sessions sorted by update time"""
        return sorted(
            self.sessions.values(),
            key=lambda s: s.updated_at,
            reverse=True
        )
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            
            # Clear current session if it was deleted
            if self.current_session_id == session_id:
                self.current_session_id = None
                
                # Set to most recent session if available
                sessions = self.get_all_sessions()
                if sessions:
                    self.current_session_id = sessions[0].id
            
            if self.settings.get("auto_save", True):
                self.save_sessions()
            
            logger.info(f"Deleted session: {session_id}")
            self.session_deleted.emit(session_id)
            return True
        
        return False
    
    def add_message_to_session(self, session_id: str, role: str, content: str, metadata: Dict = None) -> bool:
        """Add a message to a session"""
        session = self.sessions.get(session_id)
        if session:
            session.add_message(role, content, metadata)
            
            if self.settings.get("auto_save", True):
                self.save_sessions()
            
            self.session_updated.emit(session_id)
            return True
        
        return False
    
    def add_message_to_current_session(self, role: str, content: str, metadata: Dict = None) -> bool:
        """Add a message to the current session"""
        if not self.current_session_id:
            # Create a new session if none exists
            self.create_session()
        
        return self.add_message_to_session(self.current_session_id, role, content, metadata)
    
    def get_session_messages(self, session_id: str) -> List[Dict]:
        """Get messages from a session"""
        session = self.sessions.get(session_id)
        return session.messages if session else []
    
    def search_sessions(self, query: str) -> List[ChatSession]:
        """Search sessions by content"""
        query_lower = query.lower()
        matching_sessions = []
        
        for session in self.sessions.values():
            # Check title
            if query_lower in session.title.lower():
                matching_sessions.append(session)
                continue
            
            # Check messages
            for message in session.messages:
                if query_lower in message["content"].lower():
                    matching_sessions.append(session)
                    break
        
        return sorted(matching_sessions, key=lambda s: s.updated_at, reverse=True)
    
    def export_session(self, session_id: str, file_path: Path) -> bool:
        """Export a session to file"""
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        try:
            export_data = {
                "session": session.to_dict(),
                "exported_at": datetime.now().isoformat(),
                "app_version": "1.0.0"
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Exported session {session_id} to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export session: {e}")
            return False
    
    def import_session(self, file_path: Path) -> Optional[str]:
        """Import a session from file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            session_data = data.get("session")
            if not session_data:
                return None
            
            # Create new session with unique ID
            session = ChatSession.from_dict(session_data)
            session.id = str(uuid.uuid4())  # Ensure unique ID
            
            self.sessions[session.id] = session
            
            if self.settings.get("auto_save", True):
                self.save_sessions()
            
            logger.info(f"Imported session from {file_path}")
            self.session_created.emit(session.id)
            return session.id
            
        except Exception as e:
            logger.error(f"Failed to import session: {e}")
            return None
    
    def clear_all_sessions(self):
        """Clear all sessions"""
        self.sessions.clear()
        self.current_session_id = None
        
        if self.settings.get("auto_save", True):
            self.save_sessions()
        
        logger.info("Cleared all sessions")
        self.sessions_loaded.emit()
    
    def save_session(self):
        """Force save current session state"""
        self.save_data()
        logger.info("Session data saved")