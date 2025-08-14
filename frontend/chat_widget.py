"""
Chat Widget for RAG Desktop Application
Handles multi-session chat interface with streaming responses
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, 
    QPushButton, QListWidget, QListWidgetItem, QSplitter,
    QLabel, QScrollArea, QFrame, QMessageBox, QMenu, QTextBrowser,
    QGroupBox, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread
from PyQt6.QtGui import QFont, QTextCharFormat, QColor, QAction, QTextCursor

# Try to import markdown, use fallback if not available
try:
    import markdown
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False
    logger.warning("Markdown not available, using plain text for assistant messages")

from frontend.api_client import APIClient, StreamingQueryThread
from frontend.session_manager import SessionManager, ChatSession

logger = logging.getLogger(__name__)

class MessageWidget(QFrame):
    """Widget for displaying a single chat message"""
    
    def __init__(self, role: str, content: str, timestamp: str = None, sources: List = None):
        super().__init__()
        
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now().isoformat()
        self.sources = sources or []
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup message UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Header with role and timestamp
        header_layout = QHBoxLayout()
        
        role_label = QLabel(f"{'ðŸ§‘ You' if self.role == 'user' else 'ðŸ¤– Assistant'}")
        role_label.setStyleSheet("font-weight: bold; color: #0078d4;" if self.role == 'user' else "font-weight: bold; color: #00b7c3;")
        header_layout.addWidget(role_label)
        
        header_layout.addStretch()
        
        # Format timestamp
        try:
            dt = datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))
            time_str = dt.strftime("%H:%M")
        except:
            time_str = ""
        
        if time_str:
            time_label = QLabel(time_str)
            time_label.setStyleSheet("color: #666; font-size: 12px;")
            header_layout.addWidget(time_label)
        
        layout.addLayout(header_layout)
        
        # Message content
        content_widget = QTextBrowser()
        content_widget.setOpenExternalLinks(True)
        content_widget.setMaximumHeight(300)
        content_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        content_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Convert markdown to HTML for assistant messages
        if self.role == 'assistant':
            if HAS_MARKDOWN:
                try:
                    html_content = markdown.markdown(self.content, extensions=['codehilite', 'fenced_code'])
                    content_widget.setHtml(html_content)
                except:
                    content_widget.setPlainText(self.content)
            else:
                content_widget.setPlainText(self.content)
        else:
            content_widget.setPlainText(self.content)
        
        # Style the content widget
        if self.role == 'user':
            content_widget.setStyleSheet("""
                QTextBrowser {
                    background-color: #e3f2fd;
                    border: 1px solid #bbdefb;
                    border-radius: 8px;
                    padding: 8px;
                    color: #1565c0;
                }
            """)
        else:
            content_widget.setStyleSheet("""
                QTextBrowser {
                    background-color: #f1f8e9;
                    border: 1px solid #c8e6c9;
                    border-radius: 8px;
                    padding: 8px;
                    color: #2e7d32;
                }
            """)
        
        layout.addWidget(content_widget)
        
        # Add sources if available (only for assistant messages)
        if self.role == 'assistant' and self.sources:
            sources_widget = self.create_sources_widget()
            layout.addWidget(sources_widget)
        
        # Set frame style
        self.setFrameStyle(QFrame.Shape.Box)
        self.setStyleSheet("QFrame { border: none; margin: 2px; }")
    
    def create_sources_widget(self) -> QWidget:
        """Create sources display widget"""
        sources_frame = QFrame()
        sources_frame.setStyleSheet("""
            QFrame {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 5px;
                padding: 5px;
            }
        """)
        
        sources_layout = QVBoxLayout(sources_frame)
        sources_layout.setContentsMargins(8, 5, 8, 5)
        
        # Sources header
        header_label = QLabel("ðŸ“š Sources:")
        header_label.setStyleSheet("font-weight: bold; color: #666; font-size: 12px;")
        sources_layout.addWidget(header_label)
        
        # List sources
        for i, source in enumerate(self.sources[:3]):  # Show max 3 sources
            source_label = QLabel()
            
            if "document_id" in source:
                # Local document source
                preview = source.get("preview", "").strip()
                score = source.get("score", 0)
                source_text = f"ðŸ“„ Local Document (Match: {score:.1%})\n  \"{preview}\""
            elif "title" in source and "url" in source:
                # Web search source
                title = source.get("title", "Web Result")
                url = source.get("url", "")
                source_text = f"ðŸŒ Web Search: {title}\n  {url}"
            else:
                # Fallback
                source_text = f"ðŸ“– Source {i+1}: {str(source)[:100]}..."
            
            source_label.setText(source_text)
            source_label.setStyleSheet("color: #555; font-size: 11px; margin: 2px 0;")
            source_label.setWordWrap(True)
            sources_layout.addWidget(source_label)
        
        if len(self.sources) > 3:
            more_label = QLabel(f"... and {len(self.sources) - 3} more sources")
            more_label.setStyleSheet("color: #888; font-style: italic; font-size: 10px;")
            sources_layout.addWidget(more_label)
        
        return sources_frame

class SessionListWidget(QListWidget):
    """Custom list widget for chat sessions"""
    
    session_selected = pyqtSignal(str)  # session_id
    session_delete_requested = pyqtSignal(str)  # session_id
    
    def __init__(self):
        super().__init__()
        
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.itemClicked.connect(self.on_item_clicked)
        
        self.setMaximumHeight(200)
    
    def show_context_menu(self, position):
        """Show context menu for sessions"""
        item = self.itemAt(position)
        if not item:
            return
        
        menu = QMenu(self)
        
        delete_action = QAction("Delete Session", self)
        delete_action.triggered.connect(lambda: self.delete_session(item))
        menu.addAction(delete_action)
        
        menu.exec(self.mapToGlobal(position))
    
    def delete_session(self, item):
        """Request session deletion"""
        session_id = item.data(Qt.ItemDataRole.UserRole)
        if session_id:
            self.session_delete_requested.emit(session_id)
    
    def on_item_clicked(self, item):
        """Handle item click"""
        session_id = item.data(Qt.ItemDataRole.UserRole)
        if session_id:
            self.session_selected.emit(session_id)
    
    def add_session(self, session: ChatSession):
        """Add a session to the list"""
        item = QListWidgetItem()
        item.setText(f"{session.title} ({session.get_message_count()} messages)")
        item.setData(Qt.ItemDataRole.UserRole, session.id)
        item.setToolTip(f"Created: {session.created_at.strftime('%Y-%m-%d %H:%M')}")
        
        self.addItem(item)
    
    def update_session(self, session: ChatSession):
        """Update a session in the list"""
        for i in range(self.count()):
            item = self.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == session.id:
                item.setText(f"{session.title} ({session.get_message_count()} messages)")
                break
    
    def remove_session(self, session_id: str):
        """Remove a session from the list"""
        for i in range(self.count()):
            item = self.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == session_id:
                self.takeItem(i)
                break
    
    def select_session(self, session_id: str):
        """Select a specific session"""
        for i in range(self.count()):
            item = self.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == session_id:
                self.setCurrentItem(item)
                break

class ChatWidget(QWidget):
    """Main chat interface widget"""
    
    message_sent = pyqtSignal(str)
    
    def __init__(self, api_client: APIClient, session_manager: SessionManager):
        super().__init__()
        
        self.api_client = api_client
        self.session_manager = session_manager
        
        # State
        self.current_session_id = None
        self.is_authenticated = False
        self.is_online = True
        self.current_user = None
        self.streaming_thread = None
        
        # UI Components
        self.session_list = None
        self.chat_display = None
        self.message_input = None
        self.send_button = None
        self.status_label = None
        
        self.setup_ui()
        self.setup_signals()
        self.load_sessions()
        
        logger.info("Chat widget initialized")
    
    def setup_ui(self):
        """Setup the chat interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("ðŸ’¬ Chat Assistant")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin: 5px;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # New chat button
        new_chat_button = QPushButton("New Chat")
        new_chat_button.clicked.connect(self.create_new_chat)
        new_chat_button.setStyleSheet("padding: 5px 15px;")
        header_layout.addWidget(new_chat_button)
        
        layout.addLayout(header_layout)
        
        # Sessions group
        sessions_group = QGroupBox("Recent Sessions")
        sessions_layout = QVBoxLayout(sessions_group)
        
        self.session_list = SessionListWidget()
        sessions_layout.addWidget(self.session_list)
        
        layout.addWidget(sessions_group)
        
        # Chat display area
        chat_group = QGroupBox("Conversation")
        chat_layout = QVBoxLayout(chat_group)
        
        # Scroll area for messages
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Messages container
        self.messages_widget = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_widget)
        self.messages_layout.addStretch()  # Push messages to top
        
        scroll_area.setWidget(self.messages_widget)
        self.chat_display = scroll_area
        
        chat_layout.addWidget(self.chat_display)
        layout.addWidget(chat_group)
        
        # Input area
        input_layout = QVBoxLayout()
        
        # Status label
        self.status_label = QLabel("Ready to chat")
        self.status_label.setStyleSheet("color: #666; font-size: 12px; margin: 2px;")
        input_layout.addWidget(self.status_label)
        
        # Message input
        message_layout = QHBoxLayout()
        
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Type your message here...")
        self.message_input.returnPressed.connect(self.send_message)
        message_layout.addWidget(self.message_input)
        
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)
        self.send_button.setStyleSheet("padding: 8px 16px; font-weight: bold;")
        message_layout.addWidget(self.send_button)
        
        input_layout.addLayout(message_layout)
        layout.addLayout(input_layout)
    
    def setup_signals(self):
        """Setup signal connections"""
        # Session list signals
        self.session_list.session_selected.connect(self.switch_to_session)
        self.session_list.session_delete_requested.connect(self.delete_session)
        
        # Session manager signals
        self.session_manager.session_created.connect(self.on_session_created)
        self.session_manager.session_updated.connect(self.on_session_updated)
        self.session_manager.session_deleted.connect(self.on_session_deleted)
        self.session_manager.sessions_loaded.connect(self.load_sessions)
    
    def load_sessions(self):
        """Load all sessions into the list"""
        self.session_list.clear()
        
        sessions = self.session_manager.get_all_sessions()
        for session in sessions:
            self.session_list.add_session(session)
        
        # Select current session if exists
        current_session = self.session_manager.get_current_session()
        if current_session:
            self.current_session_id = current_session.id
            self.session_list.select_session(current_session.id)
            self.load_session_messages(current_session.id)
    
    def create_new_chat(self):
        """Create a new chat session"""
        session_id = self.session_manager.create_session()
        self.switch_to_session(session_id)
        self.message_input.setFocus()
    
    def switch_to_session(self, session_id: str):
        """Switch to a different session"""
        if session_id == self.current_session_id:
            return
        
        self.current_session_id = session_id
        self.session_manager.set_current_session(session_id)
        self.load_session_messages(session_id)
        
        # Update UI
        self.session_list.select_session(session_id)
        self.message_input.setFocus()
    
    def delete_session(self, session_id: str):
        """Delete a session"""
        session = self.session_manager.get_session(session_id)
        if not session:
            return
        
        reply = QMessageBox.question(
            self,
            "Delete Session",
            f"Are you sure you want to delete the session '{session.title}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.session_manager.delete_session(session_id)
            
            # Switch to another session if current was deleted
            if session_id == self.current_session_id:
                sessions = self.session_manager.get_all_sessions()
                if sessions:
                    self.switch_to_session(sessions[0].id)
                else:
                    self.current_session_id = None
                    self.clear_messages()
    
    def load_session_messages(self, session_id: str):
        """Load messages for a session"""
        self.clear_messages()
        
        messages = self.session_manager.get_session_messages(session_id)
        for message in messages:
            # Extract sources from metadata if available
            sources = []
            if message.get("metadata"):
                try:
                    import json
                    if isinstance(message["metadata"], str):
                        metadata = json.loads(message["metadata"])
                    else:
                        metadata = message["metadata"]
                    sources = metadata.get("sources", [])
                except:
                    sources = []
            
            self.add_message_to_display(
                message["role"],
                message["content"],
                message["timestamp"],
                sources
            )
    
    def clear_messages(self):
        """Clear all messages from display"""
        # Remove all message widgets except the stretch
        for i in reversed(range(self.messages_layout.count() - 1)):
            child = self.messages_layout.itemAt(i).widget()
            if child:
                child.deleteLater()
    
    def add_message_to_display(self, role: str, content: str, timestamp: str = None, sources: List = None):
        """Add a message to the display"""
        message_widget = MessageWidget(role, content, timestamp, sources)
        
        # Insert before the stretch item
        insert_index = self.messages_layout.count() - 1
        self.messages_layout.insertWidget(insert_index, message_widget)
        
        # Scroll to bottom
        QTimer.singleShot(100, self.scroll_to_bottom)
    
    def scroll_to_bottom(self):
        """Scroll chat display to bottom"""
        if self.chat_display:
            scrollbar = self.chat_display.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
    
    def send_message(self):
        """Send a message"""
        message_text = self.message_input.text().strip()
        if not message_text:
            return
        
        # Clear input
        self.message_input.clear()
        
        # Ensure we have a session
        if not self.current_session_id:
            self.create_new_chat()
        
        # Add user message to display and session
        self.add_message_to_display("user", message_text)
        self.session_manager.add_message_to_current_session("user", message_text)
        
        # Emit signal
        self.message_sent.emit(message_text)
        
        # Start processing
        self.start_query_processing(message_text)
    
    def start_query_processing(self, query: str):
        """Start processing a query"""
        self.set_processing_state(True)
        
        # Determine if we should use legacy endpoint
        use_legacy = not self.is_authenticated or not self.is_online
        user_id = "test_user" if use_legacy else None
        
        # Start streaming thread
        self.streaming_thread = StreamingQueryThread(
            self.api_client,
            query,
            self.current_session_id,
            use_legacy,
            user_id
        )
        
        # Connect signals
        self.streaming_thread.chunk_received.connect(self.on_response_chunk)
        self.streaming_thread.query_completed.connect(self.on_query_completed)
        self.streaming_thread.query_failed.connect(self.on_query_failed)
        
        # Start the thread
        self.streaming_thread.start()
        
        # Add placeholder for assistant response
        self.current_response = ""
        self.current_sources = []
        self.add_message_to_display("assistant", "Thinking...")
        self.assistant_message_widget = None
        
        # Get the last added widget (assistant message)
        insert_index = self.messages_layout.count() - 2  # -1 for stretch, -1 for last widget
        if insert_index >= 0:
            self.assistant_message_widget = self.messages_layout.itemAt(insert_index).widget()
    
    def on_response_chunk(self, chunk: str):
        """Handle response chunk from streaming"""
        self.current_response += chunk
        
        # Update the assistant message widget
        if self.assistant_message_widget:
            # Find the content widget and update it
            for child in self.assistant_message_widget.findChildren(QTextBrowser):
                if HAS_MARKDOWN:
                    try:
                        html_content = markdown.markdown(self.current_response, extensions=['codehilite', 'fenced_code'])
                        child.setHtml(html_content)
                    except:
                        child.setPlainText(self.current_response)
                else:
                    child.setPlainText(self.current_response)
                break
        
        # Scroll to bottom
        self.scroll_to_bottom()
    
    def on_query_completed(self, sources: List = None):
        """Handle query completion"""
        self.set_processing_state(False)
        
        # Store sources for display
        self.current_sources = sources or []
        
        # Replace the temporary message with final message including sources
        if self.assistant_message_widget:
            # Remove the temporary message
            self.assistant_message_widget.deleteLater()
        
        # Add final message with sources
        self.add_message_to_display("assistant", self.current_response, None, self.current_sources)
        
        # Save the final response to session with sources
        if self.current_response:
            # Create metadata with sources info
            metadata = {}
            if self.current_sources:
                metadata['sources'] = self.current_sources
            
            self.session_manager.add_message_to_current_session(
                "assistant", 
                self.current_response, 
                metadata
            )
        
        # Clean up
        self.current_response = ""
        self.current_sources = []
        self.assistant_message_widget = None
        self.streaming_thread = None
        
        # Update status
        self.status_label.setText("Ready to chat")
    
    def on_query_failed(self, error: str):
        """Handle query failure"""
        self.set_processing_state(False)
        
        # Update the assistant message with error
        error_message = f"Sorry, I encountered an error: {error}"
        
        if self.assistant_message_widget:
            for child in self.assistant_message_widget.findChildren(QTextBrowser):
                child.setPlainText(error_message)
                child.setStyleSheet("""
                    QTextBrowser {
                        background-color: #ffebee;
                        border: 1px solid #ffcdd2;
                        border-radius: 8px;
                        padding: 8px;
                        color: #c62828;
                    }
                """)
                break
        
        # Save error message to session
        self.session_manager.add_message_to_current_session("assistant", error_message)
        
        # Clean up
        self.current_response = ""
        self.assistant_message_widget = None
        self.streaming_thread = None
        
        # Update status
        self.status_label.setText("Error occurred - ready to try again")
    
    def set_processing_state(self, processing: bool):
        """Set processing state"""
        self.send_button.setEnabled(not processing)
        self.message_input.setEnabled(not processing)
        
        if processing:
            self.status_label.setText("ðŸ¤” Processing your request...")
            self.send_button.setText("Processing...")
        else:
            self.status_label.setText("Ready to chat")
            self.send_button.setText("Send")
    
    def clear_current_chat(self):
        """Clear the current chat session"""
        if not self.current_session_id:
            return
        
        session = self.session_manager.get_session(self.current_session_id)
        if not session:
            return
        
        reply = QMessageBox.question(
            self,
            "Clear Chat",
            f"Are you sure you want to clear all messages in '{session.title}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Clear messages from session
            session.messages.clear()
            session.updated_at = datetime.now()
            
            # Save and refresh display
            self.session_manager.save_sessions()
            self.clear_messages()
            
            # Update session list
            self.session_list.update_session(session)
    
    def update_online_status(self, is_online: bool):
        """Update online status"""
        self.is_online = is_online
        
        if is_online:
            self.status_label.setText("ðŸŸ¢ Online - Ready to chat")
        else:
            self.status_label.setText("ðŸ”´ Offline - Limited functionality")
        
        # Update input availability
        if not is_online and not self.is_authenticated:
            # In offline mode without auth, still allow chat with legacy endpoint
            pass
    
    def update_auth_state(self, is_authenticated: bool, user_info: Dict = None):
        """Update authentication state"""
        self.is_authenticated = is_authenticated
        self.current_user = user_info
        
        if is_authenticated and user_info:
            self.status_label.setText(f"ðŸ‘¤ Logged in as {user_info.get('name', 'User')} - Ready to chat")
        else:
            if self.is_online:
                self.status_label.setText("ðŸ”“ Not logged in - Using offline mode")
            else:
                self.status_label.setText("ðŸ”´ Offline mode")
    
    def refresh_sessions(self):
        """Refresh the sessions list"""
        self.load_sessions()
    
    def update_session(self, session_id: str):
        """Update a specific session in the list"""
        session = self.session_manager.get_session(session_id)
        if session:
            self.session_list.update_session(session)
    
    def on_session_created(self, session_id: str):
        """Handle session creation"""
        session = self.session_manager.get_session(session_id)
        if session:
            self.session_list.add_session(session)
    
    def on_session_updated(self, session_id: str):
        """Handle session update"""
        session = self.session_manager.get_session(session_id)
        if session:
            self.session_list.update_session(session)
    
    def on_session_deleted(self, session_id: str):
        """Handle session deletion"""
        self.session_list.remove_session(session_id)
    
    def get_current_session_info(self) -> Dict:
        """Get information about current session"""
        if not self.current_session_id:
            return {"active": False}
        
        session = self.session_manager.get_session(self.current_session_id)
        if not session:
            return {"active": False}
        
        return {
            "active": True,
            "id": session.id,
            "title": session.title,
            "message_count": session.get_message_count(),
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat()
        }
    
    def export_current_session(self, file_path: str) -> bool:
        """Export current session to file"""
        if not self.current_session_id:
            return False
        
        return self.session_manager.export_session(self.current_session_id, Path(file_path))