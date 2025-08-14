"""
Main Window for RAG Desktop Application
Contains the primary user interface with document management and chat
"""

import os
from pathlib import Path
from typing import Dict, List, Optional
import logging
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QPushButton, QTextEdit, QLineEdit, QListWidget, QListWidgetItem,
    QMenuBar, QMenu, QStatusBar, QProgressBar, QFrame, QScrollArea,
    QMessageBox, QFileDialog, QTabWidget, QTreeWidget, QTreeWidgetItem,
    QGroupBox, QComboBox, QCheckBox, QSpinBox, QSlider
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, QMimeData
from PyQt6.QtGui import (
    QAction, QFont, QPixmap, QIcon, QDragEnterEvent, QDropEvent,
    QKeySequence, QPalette, QColor
)

from frontend.api_client import APIClient, StreamingQueryThread
from frontend.session_manager import SessionManager, ChatSession
from frontend.auth_dialog import create_auth_dialog
from frontend.chat_widget import ChatWidget
from frontend.document_panel import DocumentPanel

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    """Main application window"""
    
    window_closed = pyqtSignal()
    
    def __init__(self, api_client: APIClient, session_manager: SessionManager, app=None):
        super().__init__()
        
        self.api_client = api_client
        self.session_manager = session_manager
        self.app = app
        
        # State
        self.is_authenticated = False
        self.is_online = True
        self.current_user = None
        
        # UI Components
        self.chat_widget = None
        self.document_panel = None
        self.status_bar = None
        
        # Setup UI
        self.setup_ui()
        self.setup_menu_bar()
        self.setup_status_bar()
        self.setup_signals()
        self.setup_drag_drop()
        
        # Load styles
        self.load_styles()
        
        # Restore window state
        self.restore_window_state()
        
        # Initialize authentication check
        QTimer.singleShot(1000, self.check_initial_auth)
        
        logger.info("Main window initialized")
    
    def setup_ui(self):
        """Setup the main user interface"""
        self.setWindowTitle("RAG Companion AI")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel - Document management
        self.document_panel = DocumentPanel(self.api_client, self.session_manager)
        self.document_panel.setMinimumWidth(300)
        self.document_panel.setMaximumWidth(500)
        splitter.addWidget(self.document_panel)
        
        # Right panel - Chat interface
        self.chat_widget = ChatWidget(self.api_client, self.session_manager)
        self.chat_widget.setMinimumWidth(400)
        splitter.addWidget(self.chat_widget)
        
        # Set splitter proportions
        splitter.setSizes([350, 800])
        splitter.setStretchFactor(0, 0)  # Document panel fixed size
        splitter.setStretchFactor(1, 1)  # Chat widget grows
    
    def setup_menu_bar(self):
        """Setup the menu bar"""
        menubar = self.menuBar()
        
        # File Menu
        file_menu = menubar.addMenu("&File")
        
        # Import document
        import_action = QAction("&Import Document...", self)
        import_action.setShortcut(QKeySequence("Ctrl+O"))
        import_action.triggered.connect(self.import_document)
        file_menu.addAction(import_action)
        
        file_menu.addSeparator()
        
        # Export chat
        export_action = QAction("&Export Chat...", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.triggered.connect(self.export_current_chat)
        file_menu.addAction(export_action)
        
        # Import chat
        import_chat_action = QAction("&Import Chat...", self)
        import_chat_action.triggered.connect(self.import_chat)
        file_menu.addAction(import_chat_action)
        
        file_menu.addSeparator()
        
        # Exit
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit Menu
        edit_menu = menubar.addMenu("&Edit")
        
        # Clear chat
        clear_action = QAction("&Clear Current Chat", self)
        clear_action.setShortcut(QKeySequence("Ctrl+L"))
        clear_action.triggered.connect(self.clear_current_chat)
        edit_menu.addAction(clear_action)
        
        # Settings
        settings_action = QAction("&Settings...", self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.triggered.connect(self.show_settings)
        edit_menu.addAction(settings_action)
        
        # View Menu
        view_menu = menubar.addMenu("&View")
        
        # Toggle panels
        toggle_docs_action = QAction("Toggle &Document Panel", self)
        toggle_docs_action.setShortcut(QKeySequence("Ctrl+1"))
        toggle_docs_action.triggered.connect(self.toggle_document_panel)
        view_menu.addAction(toggle_docs_action)
        
        # Account Menu
        account_menu = menubar.addMenu("&Account")
        
        # Login/Logout
        self.login_action = QAction("&Login with Google", self)
        self.login_action.triggered.connect(self.show_login_dialog)
        account_menu.addAction(self.login_action)
        
        self.logout_action = QAction("&Logout", self)
        self.logout_action.triggered.connect(self.logout)
        account_menu.addAction(self.logout_action)
        
        # Help Menu
        help_menu = menubar.addMenu("&Help")
        
        # About
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        # Update menu based on auth state
        self.update_auth_menu()
    
    def setup_status_bar(self):
        """Setup the status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Connection status
        self.connection_label = QLabel("Checking connection...")
        self.status_bar.addPermanentWidget(self.connection_label)
        
        # User info
        self.user_label = QLabel("Not logged in")
        self.status_bar.addPermanentWidget(self.user_label)
        
        # Progress bar for operations
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addWidget(self.progress_bar)
    
    def setup_signals(self):
        """Setup signal connections"""
        # API client signals
        self.api_client.connection_status_changed.connect(self.update_online_status)
        self.api_client.authentication_changed.connect(self.on_authentication_changed)
        self.api_client.upload_progress.connect(self.update_upload_progress)
        self.api_client.upload_completed.connect(self.on_upload_completed)
        self.api_client.upload_failed.connect(self.on_upload_failed)
        
        # Session manager signals
        self.session_manager.session_created.connect(self.on_session_created)
        self.session_manager.session_updated.connect(self.on_session_updated)
        self.session_manager.session_deleted.connect(self.on_session_deleted)
        
        # Widget signals
        if self.document_panel:
            self.document_panel.document_uploaded.connect(self.on_document_uploaded)
            self.document_panel.document_deleted.connect(self.on_document_deleted)
        
        if self.chat_widget:
            self.chat_widget.message_sent.connect(self.on_message_sent)
    
    def setup_drag_drop(self):
        """Setup drag and drop functionality"""
        self.setAcceptDrops(True)
    
    def load_styles(self):
        """Load application styles"""
        try:
            # Try to load custom stylesheet
            style_path = Path("frontend/styles.qss")
            if style_path.exists():
                with open(style_path, 'r') as f:
                    self.setStyleSheet(f.read())
            else:
                # Use built-in dark theme
                self.apply_dark_theme()
        except Exception as e:
            logger.warning(f"Failed to load styles: {e}")
            self.apply_dark_theme()
    
    def apply_dark_theme(self):
        """Apply built-in dark theme"""
        dark_stylesheet = """
        QMainWindow {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        
        QWidget {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        
        QTextEdit, QLineEdit, QListWidget, QTreeWidget {
            background-color: #3c3c3c;
            border: 1px solid #555555;
            color: #ffffff;
            selection-background-color: #0078d4;
        }
        
        QPushButton {
            background-color: #404040;
            border: 1px solid #555555;
            color: #ffffff;
            padding: 8px 16px;
            border-radius: 4px;
        }
        
        QPushButton:hover {
            background-color: #4a4a4a;
        }
        
        QPushButton:pressed {
            background-color: #0078d4;
        }
        
        QMenuBar {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        
        QMenuBar::item:selected {
            background-color: #404040;
        }
        
        QMenu {
            background-color: #3c3c3c;
            color: #ffffff;
            border: 1px solid #555555;
        }
        
        QMenu::item:selected {
            background-color: #0078d4;
        }
        
        QStatusBar {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        
        QSplitter::handle {
            background-color: #555555;
        }
        
        QGroupBox {
            font-weight: bold;
            border: 2px solid #555555;
            border-radius: 4px;
            margin-top: 1ex;
            padding-top: 10px;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        """
        self.setStyleSheet(dark_stylesheet)
    
    def restore_window_state(self):
        """Restore window geometry and state"""
        geometry = self.session_manager.get_setting("window_geometry")
        state = self.session_manager.get_setting("window_state")
        
        if geometry:
            self.restoreGeometry(geometry)
        
        if state:
            self.restoreState(state)
    
    def save_window_state(self):
        """Save window geometry and state"""
        self.session_manager.set_setting("window_geometry", self.saveGeometry())
        self.session_manager.set_setting("window_state", self.saveState())
    
    def check_initial_auth(self):
        """Check if user is already authenticated"""
        user_info = self.session_manager.get_user_info()
        if user_info and self.session_manager.get_setting("remember_login", True):
            # Try to validate existing session
            logger.info("Found existing user info, checking authentication...")
            self.current_user = user_info
            self.update_auth_state(True, user_info)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter event"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        """Handle drop event"""
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        valid_files = []
        
        for file_path in files:
            if Path(file_path).suffix.lower() in ['.pdf', '.docx', '.txt', '.md']:
                valid_files.append(file_path)
        
        if valid_files:
            if self.document_panel:
                self.document_panel.upload_files(valid_files)
        else:
            QMessageBox.warning(
                self, 
                "Invalid Files", 
                "Please drop supported document files (PDF, DOCX, TXT, MD)"
            )
    
    def update_online_status(self, is_online: bool):
        """Update online/offline status"""
        self.is_online = is_online
        
        if is_online:
            self.connection_label.setText("ðŸŸ¢ Online")
            self.status_bar.showMessage("Connected to backend", 3000)
        else:
            self.connection_label.setText("ðŸ”´ Offline")
            self.status_bar.showMessage("Offline mode - limited functionality", 5000)
        
        # Update widgets
        if self.document_panel:
            self.document_panel.update_online_status(is_online)
        if self.chat_widget:
            self.chat_widget.update_online_status(is_online)
    
    def on_authentication_changed(self, is_authenticated: bool, user_info: Dict):
        """Handle authentication status change"""
        self.update_auth_state(is_authenticated, user_info)
    
    def update_auth_state(self, is_authenticated: bool, user_info: Dict = None):
        """Update authentication state"""
        self.is_authenticated = is_authenticated
        self.current_user = user_info
        
        if is_authenticated and user_info:
            self.user_label.setText(f"ðŸ‘¤ {user_info.get('name', user_info.get('email', 'User'))}")
            self.session_manager.set_user_info(user_info)
        else:
            self.user_label.setText("ðŸ‘¤ Not logged in")
            self.current_user = None
        
        self.update_auth_menu()
        
        # Update widgets
        if self.document_panel:
            self.document_panel.update_auth_state(is_authenticated, user_info)
        if self.chat_widget:
            self.chat_widget.update_auth_state(is_authenticated, user_info)
    
    def update_auth_menu(self):
        """Update authentication menu items"""
        self.login_action.setVisible(not self.is_authenticated)
        self.logout_action.setVisible(self.is_authenticated)
    
    def show_login_dialog(self):
        """Show login dialog"""
        dialog = create_auth_dialog(self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            token = getattr(dialog, 'get_google_token', lambda: None)()
            if token:
                # Validate the JWT token from OAuth callback
                result = self.api_client.validate_jwt_token(token)
                if result["success"]:
                    # Update authentication state
                    self.is_authenticated = True
                    self.current_user = result.get("data", {}).get("user", {})
                    
                    # Update session manager with user info
                    if self.current_user:
                        self.session_manager.set_user_info(self.current_user)
                    
                    # Update UI components
                    self.update_auth_state(True, self.current_user)
                    
                    # Update menu bar
                    self.update_auth_menu()
                    
                    # Get user name safely
                    user_name = self.current_user.get('name', 'User') if self.current_user else 'User'
                    user_email = self.current_user.get('email', '') if self.current_user else ''
                    
                    self.status_bar.showMessage(f"Login successful! Welcome, {user_name}", 5000)
                    
                    # Show success message
                    QMessageBox.information(
                        self,
                        "Login Successful",
                        f"Welcome to RAG Companion AI!\n\n"
                        f"You are now logged in as: {user_name}\n"
                        f"Email: {user_email}\n\n"
                        f"You now have access to:\n"
                        f"• Personal document storage\n"
                        f"• Cloud synchronization\n"
                        f"• Enhanced web search\n"
                        f"• Session backup"
                    )
                else:
                    QMessageBox.critical(
                        self, 
                        "Login Failed", 
                        f"Failed to authenticate: {result.get('error', 'Unknown error')}\n\n"
                        f"Please check your token and try again."
                    )
            else:
                # User chose to continue offline
                self.status_bar.showMessage("Continuing in offline mode", 3000)
    
    def logout(self):
        """Logout current user"""
        reply = QMessageBox.question(
            self,
            "Logout",
            "Are you sure you want to logout?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Clear authentication state
            self.is_authenticated = False
            self.current_user = None
            
            # Clear API client token
            self.api_client.set_auth_token(None)
            
            # Clear session manager user info
            self.session_manager.set_user_info({})
            
            # Update UI components
            self.update_auth_state(False, None)
            
            # Update menu bar
            self.update_auth_menu()
            
            self.status_bar.showMessage("Logged out successfully", 3000)
    
    def import_document(self):
        """Import document dialog"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Document",
            "",
            "Documents (*.pdf *.docx *.txt *.md);;All Files (*)"
        )
        
        if file_path and self.document_panel:
            self.document_panel.upload_files([file_path])
    
    def export_current_chat(self):
        """Export current chat session"""
        current_session = self.session_manager.get_current_session()
        if not current_session:
            QMessageBox.information(self, "Export Chat", "No active chat session to export")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Chat",
            f"{current_session.title}.json",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            if self.session_manager.export_session(current_session.id, Path(file_path)):
                QMessageBox.information(self, "Export Successful", f"Chat exported to {file_path}")
            else:
                QMessageBox.critical(self, "Export Failed", "Failed to export chat session")
    
    def import_chat(self):
        """Import chat session"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Chat",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            session_id = self.session_manager.import_session(Path(file_path))
            if session_id:
                QMessageBox.information(self, "Import Successful", "Chat session imported successfully")
                if self.chat_widget:
                    self.chat_widget.refresh_sessions()
            else:
                QMessageBox.critical(self, "Import Failed", "Failed to import chat session")
    
    def clear_current_chat(self):
        """Clear current chat session"""
        reply = QMessageBox.question(
            self,
            "Clear Chat",
            "Are you sure you want to clear the current chat?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes and self.chat_widget:
            self.chat_widget.clear_current_chat()
    
    def show_settings(self):
        """Show settings dialog"""
        # TODO: Implement settings dialog
        QMessageBox.information(self, "Settings", "Settings dialog coming soon!")
    
    def toggle_document_panel(self):
        """Toggle document panel visibility"""
        if self.document_panel:
            self.document_panel.setVisible(not self.document_panel.isVisible())
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About RAG Companion AI",
            """
            <h3>RAG Companion AI v1.0.0</h3>
            <p>A privacy-first document intelligence assistant</p>
            <p>Features:</p>
            <ul>
            <li>Local document processing</li>
            <li>Semantic search and RAG</li>
            <li>Multi-session chat</li>
            <li>Online/offline operation</li>
            </ul>
            <p><b>Developed with PyQt6 and FastAPI</b></p>
            """
        )
    
    def update_upload_progress(self, filename: str, percentage: int):
        """Update upload progress"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(percentage)
        self.status_bar.showMessage(f"Uploading {filename}... {percentage}%")
    
    def on_upload_completed(self, filename: str, result: Dict):
        """Handle upload completion"""
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage(f"Upload completed: {filename}", 3000)
        
        if self.document_panel:
            self.document_panel.refresh_documents()
    
    def on_upload_failed(self, filename: str, error: str):
        """Handle upload failure"""
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage(f"Upload failed: {filename}", 5000)
        
        QMessageBox.critical(
            self,
            "Upload Failed",
            f"Failed to upload {filename}:\n{error}"
        )
    
    def on_document_uploaded(self, filename: str):
        """Handle document upload notification"""
        self.status_bar.showMessage(f"Document processed: {filename}", 3000)
    
    def on_document_deleted(self, filename: str):
        """Handle document deletion notification"""
        self.status_bar.showMessage(f"Document deleted: {filename}", 3000)
    
    def on_message_sent(self, message: str):
        """Handle message sent notification"""
        self.status_bar.showMessage("Processing query...", 2000)
    
    def on_session_created(self, session_id: str):
        """Handle session creation"""
        if self.chat_widget:
            self.chat_widget.refresh_sessions()
    
    def on_session_updated(self, session_id: str):
        """Handle session update"""
        if self.chat_widget:
            self.chat_widget.update_session(session_id)
    
    def on_session_deleted(self, session_id: str):
        """Handle session deletion"""
        if self.chat_widget:
            self.chat_widget.refresh_sessions()
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Check if system tray is available
        if self.app and hasattr(self.app, 'tray_icon') and self.app.tray_icon and self.app.tray_icon.isVisible():
            # Hide to system tray instead of closing
            event.ignore()
            self.hide()
            
            # Save window state
            self.save_window_state()
            
            # Emit signal for app handling
            self.window_closed.emit()
            
            # Show tray message
            self.app.tray_icon.showMessage(
                "RAG Companion AI",
                "Application was minimized to system tray",
                self.app.tray_icon.MessageIcon.Information,
                2000
            )
        else:
            # No system tray available, actually close the application
            # Save window state
            self.save_window_state()
            
            # Emit signal for app handling
            self.window_closed.emit()
            
            # Accept the close event
            event.accept()
            
            # Quit the application
            if self.app:
                self.app.quit_application()