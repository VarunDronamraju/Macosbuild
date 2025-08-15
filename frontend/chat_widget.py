"""
Chat Widget for RAG Desktop Application
Handles multi-session chat interface with streaming responses - Dream UI Style
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, 
    QPushButton, QListWidget, QListWidgetItem, QSplitter,
    QLabel, QScrollArea, QFrame, QMessageBox, QMenu, QTextBrowser,
    QGroupBox, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, QPropertyAnimation, QRect, QEasingCurve
from PyQt6.QtGui import QFont, QTextCharFormat, QColor, QAction, QTextCursor, QPainter, QBrush, QLinearGradient, QRadialGradient

# Try to import markdown, use fallback if not available
try:
    import markdown
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False
    logger = logging.getLogger(__name__)
    logger.warning("Markdown not available, using plain text for assistant messages")

from frontend.api_client import APIClient, StreamingQueryThread
from frontend.session_manager import SessionManager, ChatSession

logger = logging.getLogger(__name__)

class GradientWidget(QWidget):
    """Widget with dream UI gradient background"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Main gradient background
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, QColor(248, 255, 254))  # #f8fffe
        gradient.setColorAt(1, QColor(240, 249, 247))  # #f0f9f7
        painter.fillRect(self.rect(), QBrush(gradient))
        
        # Radial gradient patterns
        radial1 = QRadialGradient(self.width() * 0.2, self.height() * 0.8, self.width() * 0.5)
        radial1.setColorAt(0, QColor(120, 220, 180, 25))
        radial1.setColorAt(1, QColor(120, 220, 180, 0))
        painter.fillRect(self.rect(), QBrush(radial1))
        
        radial2 = QRadialGradient(self.width() * 0.8, self.height() * 0.2, self.width() * 0.5)
        radial2.setColorAt(0, QColor(120, 220, 180, 20))
        radial2.setColorAt(1, QColor(120, 220, 180, 0))
        painter.fillRect(self.rect(), QBrush(radial2))

class MessageWidget(QFrame):
    """Widget for displaying a single chat message - Dream UI style"""
    
    def __init__(self, role: str, content: str, timestamp: str = None, sources: List = None):
        super().__init__()
        
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now().isoformat()
        self.sources = sources or []
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup message UI in dream style"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 16)
        
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
        
        # Style the content widget - Dream UI style
        if self.role == 'user':
            content_widget.setStyleSheet("""
                QTextBrowser {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                              stop:0 #78dcb4, stop:1 #68d391);
                    border: none;
                    border-radius: 20px;
                    padding: 18px 24px;
                    color: white;
                    font-size: 14px;
                    font-weight: 500;
                    margin: 8px 0px;
                    line-height: 1.5;
                }
            """)
        else:
            content_widget.setStyleSheet("""
                QTextBrowser {
                    background: white;
                    border: 1px solid rgba(0, 0, 0, 0.1);
                    border-radius: 20px;
                    padding: 18px 24px;
                    color: #2d3748;
                    font-size: 14px;
                    margin: 8px 0px;
                    line-height: 1.5;
                }
            """)
        
        layout.addWidget(content_widget)
        
        # Add sources if available (only for assistant messages)
        if self.role == 'assistant' and self.sources:
            sources_widget = self.create_sources_widget()
            layout.addWidget(sources_widget)
        
        # Set frame style
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setStyleSheet("QFrame { border: none; }")
    
    def create_sources_widget(self) -> QWidget:
        """Create sources display widget"""
        sources_frame = QFrame()
        sources_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.6);
                border: 1px solid rgba(0, 0, 0, 0.05);
                border-radius: 8px;
                margin-top: 8px;
                padding: 8px;
            }
        """)
        
        sources_layout = QVBoxLayout(sources_frame)
        sources_layout.setContentsMargins(8, 5, 8, 5)
        
        # Sources header
        header_label = QLabel("📚 Sources:")
        header_label.setStyleSheet("font-weight: 600; color: #4a5568; font-size: 11px;")
        sources_layout.addWidget(header_label)
        
        # List sources
        for i, source in enumerate(self.sources[:3]):  # Show max 3 sources
            source_label = QLabel()
            
            if "document_id" in source:
                # Local document source
                preview = source.get("preview", "").strip()
                score = source.get("score", 0)
                source_text = f"[DOC] Local Document (Match: {score:.1%})\n  \"{preview}\""
            elif "title" in source and "url" in source:
                # Web search source
                title = source.get("title", "Web Result")
                url = source.get("url", "")
                source_text = f"[GLOBE] Web Search: {title}\n  {url}"
            else:
                # Fallback
                source_text = f"[CLIPBOARD] Source {i+1}: {str(source)[:100]}..."
            
            source_label.setText(source_text)
            source_label.setStyleSheet("color: #555; font-size: 10px; margin: 2px 0;")
            source_label.setWordWrap(True)
            sources_layout.addWidget(source_label)
        
        if len(self.sources) > 3:
            more_label = QLabel(f"... and {len(self.sources) - 3} more sources")
            more_label.setStyleSheet("color: #888; font-style: italic; font-size: 9px;")
            sources_layout.addWidget(more_label)
        
        return sources_frame

class SessionListWidget(QListWidget):
    """Custom list widget for chat sessions - Dream UI style"""
    
    session_selected = pyqtSignal(str)  # session_id
    session_delete_requested = pyqtSignal(str)  # session_id
    
    def __init__(self):
        super().__init__()
        
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.itemClicked.connect(self.on_item_clicked)
        
        self.setMaximumHeight(200)
        
        # Dream UI styling
        self.setStyleSheet("""
            QListWidget {
                background: rgba(255, 255, 255, 0.6);
                border: 1px solid rgba(0, 0, 0, 0.05);
                border-radius: 8px;
                padding: 4px;
            }
            QListWidget::item {
                background: rgba(255, 255, 255, 0.5);
                border: 1px solid rgba(0, 0, 0, 0.05);
                border-radius: 8px;
                margin: 2px;
                padding: 8px 12px;
                font-size: 11px;
                color: #2d3748;
            }
            QListWidget::item:hover {
                background: rgba(120, 220, 180, 0.1);
                border: 1px solid rgba(120, 220, 180, 0.2);
            }
            QListWidget::item:selected {
                background: rgba(120, 220, 180, 0.15);
                border: 1px solid rgba(120, 220, 180, 0.3);
                color: #2d3748;
            }
        """)
    
    def show_context_menu(self, position):
        """Show context menu for sessions"""
        item = self.itemAt(position)
        if not item:
            return
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: white;
                border: 1px solid rgba(0, 0, 0, 0.05);
                border-radius: 8px;
                padding: 4px 0;
            }
            QMenu::item {
                padding: 8px 16px;
            }
            QMenu::item:selected {
                background: rgba(120, 220, 180, 0.1);
            }
        """)
        
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
    """Main chat interface widget - Dream UI style"""
    
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
        
        # Add initial message after a short delay
        QTimer.singleShot(500, self.add_initial_message)
        
        logger.info("Chat widget initialized")
    
    def setup_ui(self):
        """Setup the chat interface in dream UI style"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Messages area with gradient background
        self.messages_scroll = QScrollArea()
        self.messages_scroll.setWidgetResizable(True)
        self.messages_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.messages_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.messages_scroll.setStyleSheet("""
            QScrollArea { 
                border: none; 
                background: transparent;
                padding: 10px;
            }
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 0.5);
                width: 10px;
                border-radius: 5px;
                margin: 2px;
            }
            QScrollBar::handle:vertical {
                background: rgba(120, 220, 180, 0.6);
                border-radius: 5px;
                min-height: 30px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(120, 220, 180, 0.8);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        # Messages widget with gradient background
        self.messages_widget = GradientWidget()
        self.messages_layout = QVBoxLayout(self.messages_widget)
        self.messages_layout.setContentsMargins(20, 20, 20, 20)
        self.messages_layout.setSpacing(0)
        
        # Welcome message
        self.welcome_widget = QWidget()
        welcome_layout = QVBoxLayout()
        welcome_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        welcome_title = QLabel("Welcome to CompanionAI")
        welcome_title.setFont(QFont("Arial", 20, QFont.Weight.DemiBold))
        welcome_title.setStyleSheet("color: #2d3748; margin-bottom: 10px;")
        welcome_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        welcome_subtitle = QLabel("Your intelligent workplace companion. How can I assist you today?")
        welcome_subtitle.setFont(QFont("Arial", 12))
        welcome_subtitle.setStyleSheet("color: #4a5568; opacity: 0.7;")
        welcome_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        welcome_layout.addWidget(welcome_title)
        welcome_layout.addWidget(welcome_subtitle)
        self.welcome_widget.setLayout(welcome_layout)
        
        self.messages_layout.addStretch()
        self.messages_layout.addWidget(self.welcome_widget)
        self.messages_layout.addStretch()
        
        self.messages_scroll.setWidget(self.messages_widget)
        
        # Input area
        input_area = self.create_input_area()
        
        layout.addWidget(self.messages_scroll)
        layout.addWidget(input_area)
        
        # For compatibility
        self.chat_display = self.messages_scroll
    
    def create_input_area(self):
        """Create the input area with user avatar and message input"""
        input_area = QFrame()
        input_area.setFixedHeight(120)  # Increased height
        input_area.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.9);
                border-top: 1px solid rgba(0, 0, 0, 0.1);
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 18, 24, 18)  # Increased margins
        
        input_wrapper = QFrame()
        input_wrapper.setStyleSheet("""
            QFrame {
                background: white;
                border: 2px solid rgba(120, 220, 180, 0.3);
                border-radius: 20px;
            }
            QFrame:hover {
                border: 2px solid rgba(120, 220, 180, 0.5);
            }
        """)
        
        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(20, 16, 20, 16)  # Increased padding
        input_layout.setSpacing(16)  # Increased spacing
        
        # Document button
        doc_btn = QPushButton("📄")
        doc_btn.setFixedSize(44, 44)  # Slightly larger
        doc_btn.setStyleSheet("""
            QPushButton {
                background: rgba(120, 220, 180, 0.15);
                border: 1px solid rgba(120, 220, 180, 0.4);
                border-radius: 12px;
                font-size: 20px;
                color: #68d391;
            }
            QPushButton:hover {
                background: rgba(120, 220, 180, 0.25);
                border: 1px solid rgba(120, 220, 180, 0.6);
                color: #48bb78;
            }
            QPushButton:pressed {
                background: rgba(120, 220, 180, 0.35);
            }
        """)
        doc_btn.clicked.connect(self.add_document)
        
        # Input field
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Type your message here...")
        self.message_input.setStyleSheet("""
            QLineEdit {
                border: none;
                font-size: 15px;
                background: transparent;
                color: #2d3748;
                padding: 10px 0px;
            }
            QLineEdit::placeholder {
                color: #a0aec0;
                font-style: italic;
            }
            QLineEdit:focus {
                outline: none;
            }
        """)
        self.message_input.returnPressed.connect(self.send_message)
        
        # Send button
        self.send_button = QPushButton("➤")
        self.send_button.setFixedSize(44, 44)  # Slightly larger
        self.send_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                          stop:0 #78dcb4, stop:1 #68d391);
                border: none;
                border-radius: 12px;
                font-size: 20px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                          stop:0 #68d391, stop:1 #48bb78);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                          stop:0 #48bb78, stop:1 #38a169);
            }
        """)
        self.send_button.clicked.connect(self.send_message)
        
        input_layout.addWidget(doc_btn)
        input_layout.addWidget(self.message_input)
        input_layout.addWidget(self.send_button)
        
        input_wrapper.setLayout(input_layout)
        layout.addWidget(input_wrapper)
        input_area.setLayout(layout)
        
        # Status label (hidden initially)
        self.status_label = QLabel("Ready to chat")
        self.status_label.setStyleSheet("color: #666; font-size: 11px; margin: 2px; background: transparent;")
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)
        
        return input_area
    
    def add_document(self):
        """Handle document upload"""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        
        # Check authentication status from main window if available
        has_auth_token = False
        if hasattr(self, 'main_window') and self.main_window:
            has_auth_token = self.main_window.is_authenticated
        else:
            has_auth_token = bool(self.api_client.access_token)
        
        if not has_auth_token:
            reply = QMessageBox.question(
                self,
                "Authentication Required - CompanionAI",
                "Document upload requires authentication. Would you like to log in now, or continue with legacy upload?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Cancel:
                return
            elif reply == QMessageBox.StandardButton.Yes:
                # Try to trigger login from main window
                if hasattr(self, 'main_window') and self.main_window:
                    self.main_window.show_login_dialog()
                else:
                    QMessageBox.information(
                        self,
                        "Login Required",
                        "Please use the Account menu to log in before uploading documents."
                    )
                return
        
        # Open file dialog for document selection
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle("Select Documents to Upload")
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_dialog.setNameFilter(
            "Documents (*.txt *.pdf *.doc *.docx *.md);;"
            "Text Files (*.txt *.md);;"
            "PDF Files (*.pdf);;"
            "Word Documents (*.doc *.docx);;"
            "All Files (*.*)"
        )
        
        if file_dialog.exec() == QFileDialog.DialogCode.Accepted:
            file_paths = file_dialog.selectedFiles()
            if file_paths:
                self.upload_documents(file_paths)
    
    def upload_documents(self, file_paths: List[str]):
        """Upload multiple documents"""
        from PyQt6.QtWidgets import QMessageBox
        
        # Check if we have authentication token in API client
        has_auth_token = bool(self.api_client.access_token)
        
        if not has_auth_token and not self.is_online:
            QMessageBox.warning(
                self,
                "Upload Not Available",
                "Document upload requires authentication or online mode."
            )
            return
        
        success_count = 0
        failed_count = 0
        
        # Process each file silently
        for file_path in file_paths:
            try:
                # Upload using API client - prefer authenticated endpoint if token available
                if has_auth_token:
                    logger.info(f"[DOC] Using authenticated upload for: {Path(file_path).name}")
                    result = self.api_client.upload_document(file_path)
                else:
                    logger.info(f"[DOC] Using legacy upload for: {Path(file_path).name}")
                    result = self.api_client.upload_document_legacy(file_path)
                
                if result["success"]:
                    logger.info(f"[SUCCESS] Document uploaded: {Path(file_path).name}")
                    success_count += 1
                else:
                    logger.error(f"[FAIL] Upload failed: {result['error']}")
                    failed_count += 1
                    
            except Exception as e:
                logger.error(f"[ERROR] Upload error: {e}")
                failed_count += 1
        
        # Show only completion message
        if failed_count == 0:
            QMessageBox.information(
                self,
                "Upload Complete - CompanionAI",
                f"Successfully uploaded {success_count} document(s) to your knowledge base."
            )
        elif success_count == 0:
            QMessageBox.critical(
                self,
                "Upload Failed",
                f"Failed to upload {failed_count} document(s).\n\n"
                f"Please check your authentication status and try again."
            )
        else:
            QMessageBox.warning(
                self,
                "Upload Partially Complete",
                f"Uploaded {success_count} document(s) successfully.\n"
                f"Failed to upload {failed_count} document(s).\n\n"
                f"Please check the logs for more details."
            )
    
    def add_initial_message(self):
        """Add initial welcome message"""
        self.add_message_to_display("assistant", "Hello! Welcome to CompanionAI.")
    
    def setup_signals(self):
        """Setup signal connections"""
        # Session manager signals
        self.session_manager.session_created.connect(self.on_session_created)
        self.session_manager.session_updated.connect(self.on_session_updated)
        self.session_manager.session_deleted.connect(self.on_session_deleted)
        self.session_manager.sessions_loaded.connect(self.load_sessions)
    
    def load_sessions(self):
        """Load all sessions into the list"""
        # Note: Session list is now handled by sidebar in main window
        # This method kept for compatibility
        pass
    
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
        for i in reversed(range(self.messages_layout.count())):
            item = self.messages_layout.itemAt(i)
            if item and item.widget() and item.widget() != self.welcome_widget:
                item.widget().deleteLater()
        
        # Recreate layout with welcome message
        self.messages_layout.addStretch()
        if hasattr(self, 'welcome_widget') and self.welcome_widget:
            self.welcome_widget.setVisible(True)
            self.messages_layout.addWidget(self.welcome_widget)
        self.messages_layout.addStretch()
    
    def add_message_to_display(self, role: str, content: str, timestamp: str = None, sources: List = None):
        """Add a message to the display - Dream UI style"""
        # Remove welcome message if present
        if hasattr(self, 'welcome_widget') and self.welcome_widget and self.welcome_widget.isVisible():
            self.welcome_widget.setVisible(False)
        
        message_widget = MessageWidget(role, content, timestamp, sources)
        
        # Create wrapper for proper alignment
        wrapper = QWidget()
        wrapper.setStyleSheet("background: transparent; margin: 6px 0px;")  # Increased margin
        wrapper_layout = QHBoxLayout()
        wrapper_layout.setContentsMargins(24, 10, 24, 10)  # Increased margins
        wrapper_layout.setSpacing(16)  # Increased spacing
        
        if role == 'user':
            wrapper_layout.addStretch()
            wrapper_layout.addWidget(message_widget)
            message_widget.setMaximumWidth(int(self.width() * 0.7))  # Slightly smaller for better balance
        else:
            wrapper_layout.addWidget(message_widget)
            wrapper_layout.addStretch()
            message_widget.setMaximumWidth(int(self.width() * 0.8))  # Assistant messages can be wider
        
        wrapper.setLayout(wrapper_layout)
        
        # Insert before the last stretch item
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, wrapper)
        
        # Scroll to bottom
        QTimer.singleShot(100, self.scroll_to_bottom)
    
    def scroll_to_bottom(self):
        """Scroll chat display to bottom"""
        if self.messages_scroll:
            scrollbar = self.messages_scroll.verticalScrollBar()
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
        last_widget_item = self.messages_layout.itemAt(self.messages_layout.count() - 2)
        if last_widget_item:
            self.assistant_message_widget = last_widget_item.widget()
    
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
                        background-color: #fed7d7;
                        border: 1px solid #feb2b2;
                        border-radius: 16px;
                        padding: 12px 16px;
                        color: #e53e3e;
                    }
                """)
                break
        
        # Save error message to session
        self.session_manager.add_message_to_current_session("assistant", error_message)
        
        # Clean up
        self.current_response = ""
        self.assistant_message_widget = None
        self.streaming_thread = None
    
    def set_processing_state(self, processing: bool):
        """Set processing state"""
        self.send_button.setEnabled(not processing)
        self.message_input.setEnabled(not processing)
        
        if processing:
            self.send_button.setText("⏳")
            self.send_button.setStyleSheet("""
                QPushButton {
                    background: rgba(120, 220, 180, 0.3);
                    border: none;
                    border-radius: 10px;
                    font-size: 18px;
                    color: #68d391;
                }
            """)
        else:
            self.send_button.setText("➤")
            self.send_button.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                              stop:0 #78dcb4, stop:1 #68d391);
                    border: none;
                    border-radius: 10px;
                    font-size: 18px;
                    color: white;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                              stop:0 #68d391, stop:1 #48bb78);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                              stop:0 #48bb78, stop:1 #38a169);
                }
            """)
    
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
    
    def update_online_status(self, is_online: bool):
        """Update online status"""
        self.is_online = is_online
    
    def update_auth_state(self, is_authenticated: bool, user_info: Dict = None):
        """Update authentication state"""
        self.is_authenticated = is_authenticated
        self.current_user = user_info
        
        # Log the authentication state change
        if is_authenticated:
            user_name = user_info.get('name', 'Unknown') if user_info else 'Unknown'
            logger.info(f"[AUTH] Chat widget authenticated as: {user_name}")
        else:
            logger.info("[AUTH] Chat widget authentication cleared")
    
    def refresh_sessions(self):
        """Refresh the sessions list"""
        self.load_sessions()
    
    def update_session(self, session_id: str):
        """Update a specific session in the list"""
        pass  # Handled by main window sidebar
    
    def on_session_created(self, session_id: str):
        """Handle session creation"""
        pass  # Handled by main window sidebar
    
    def on_session_updated(self, session_id: str):
        """Handle session update"""
        pass  # Handled by main window sidebar
    
    def on_session_deleted(self, session_id: str):
        """Handle session deletion"""
        pass  # Handled by main window sidebar
    
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
        
        from pathlib import Path
        return self.session_manager.export_session(self.current_session_id, Path(file_path))