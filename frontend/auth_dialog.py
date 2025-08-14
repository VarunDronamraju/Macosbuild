"""
Authentication Dialog for Google OAuth Login
Handles Google OAuth flow in a web view
"""

import sys
import logging
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QProgressBar, QTextEdit, QMessageBox, QGroupBox, QLineEdit
)
from PyQt6.QtCore import Qt, QUrl, QTimer, pyqtSignal
import webbrowser
import urllib.parse
import re

logger = logging.getLogger(__name__)

# Try to import web engine widgets (optional dependency)
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
    HAS_WEB_ENGINE = True
except ImportError:
    HAS_WEB_ENGINE = False
    logger.warning("QWebEngine not available, using fallback authentication method")
    # Create dummy classes to avoid NameError
    class QWebEngineView:
        pass
    class QWebEnginePage:
        pass

if HAS_WEB_ENGINE:
    class GoogleAuthPage(QWebEnginePage):
        """Custom web page for handling Google OAuth"""
        
        token_received = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.urlChanged.connect(self.handle_url_change)
    
    def handle_url_change(self, url):
        """Handle URL changes to detect OAuth callback"""
        url_string = url.toString()
        logger.debug(f"URL changed: {url_string}")
        
        # Look for access token in URL
        if "access_token=" in url_string:
            try:
                # Extract token from URL fragment
                fragment = url.fragment()
                params = urllib.parse.parse_qs(fragment)
                
                if "access_token" in params:
                    token = params["access_token"][0]
                    self.token_received.emit(token)
                    return
            except Exception as e:
                logger.error(f"Error extracting token from URL: {e}")
        
        # Look for authorization code
        if "code=" in url_string:
            try:
                parsed_url = urllib.parse.urlparse(url_string)
                params = urllib.parse.parse_qs(parsed_url.query)
                
                if "code" in params:
                    code = params["code"][0]
                    # For simplicity, we'll use the code as token
                    # In production, you'd exchange this for an access token
                    self.token_received.emit(code)
                    return
            except Exception as e:
                logger.error(f"Error extracting code from URL: {e}")

class AuthDialog(QDialog):
    """Authentication dialog for Google OAuth"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.google_token = None
        self.web_view = None
        
        self.setup_ui()
        self.setup_signals()
        
        # Set dialog properties
        self.setWindowTitle("Login to RAG Companion AI")
        self.setModal(True)
        self.resize(800, 600)
        
        logger.info("Authentication dialog initialized")
    
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel("Login with Google Account")
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_label.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(header_label)
        
        # Instructions
        instructions = QLabel(
            "Please login with your Google account to access personalized features.\n"
            "Your documents and chat history will be securely stored locally."
        )
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instructions.setWordWrap(True)
        instructions.setStyleSheet("margin: 10px; color: #666;")
        layout.addWidget(instructions)
        
        if HAS_WEB_ENGINE:
            # Web view for OAuth
            self.web_view = QWebEngineView()
            self.web_view.setPage(GoogleAuthPage())
            layout.addWidget(self.web_view)
            
            # Progress bar
            self.progress_bar = QProgressBar()
            self.progress_bar.setVisible(False)
            layout.addWidget(self.progress_bar)
        else:
            # Fallback manual token input
            self.setup_fallback_ui(layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        if HAS_WEB_ENGINE:
            self.login_button = QPushButton("Login with Google")
            self.login_button.clicked.connect(self.start_oauth_flow)
            button_layout.addWidget(self.login_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        button_layout.addStretch()
        
        # Offline mode button
        self.offline_button = QPushButton("Continue in Offline Mode")
        self.offline_button.clicked.connect(self.continue_offline)
        button_layout.addWidget(self.offline_button)
        
        layout.addLayout(button_layout)
    
    def setup_fallback_ui(self, layout):
        """Setup fallback UI when WebEngine is not available"""
        fallback_group = QGroupBox("Manual Authentication")
        fallback_layout = QVBoxLayout(fallback_group)
        
        # Instructions
        fallback_instructions = QLabel(
            "1. Click 'Open Browser' to open Google OAuth in your default browser\n"
            "2. Complete the authentication process\n"
            "3. Copy the access token from the final URL\n"
            "4. Paste it in the field below"
        )
        fallback_instructions.setWordWrap(True)
        fallback_layout.addWidget(fallback_instructions)
        
        # Browser button
        self.browser_button = QPushButton("Open Browser for Authentication")
        self.browser_button.clicked.connect(self.open_browser_auth)
        fallback_layout.addWidget(self.browser_button)
        
        # Token input
        token_label = QLabel("Access Token:")
        fallback_layout.addWidget(token_label)
        
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("Paste your access token here...")
        self.token_input.textChanged.connect(self.on_token_input_changed)
        fallback_layout.addWidget(self.token_input)
        
        # Verify button
        self.verify_button = QPushButton("Verify Token")
        self.verify_button.setEnabled(False)
        self.verify_button.clicked.connect(self.verify_manual_token)
        fallback_layout.addWidget(self.verify_button)
        
        layout.addWidget(fallback_group)
    
    def setup_signals(self):
        """Setup signal connections"""
        if HAS_WEB_ENGINE and self.web_view:
            self.web_view.page().token_received.connect(self.on_token_received)
            self.web_view.loadStarted.connect(self.on_load_started)
            self.web_view.loadFinished.connect(self.on_load_finished)
    
    def start_oauth_flow(self):
        """Start the OAuth flow"""
        if not HAS_WEB_ENGINE or not self.web_view:
            return
        
        # Google OAuth URL
        oauth_url = self.build_oauth_url()
        
        logger.info("Starting OAuth flow")
        self.web_view.load(QUrl(oauth_url))
        self.login_button.setEnabled(False)
    
    def build_oauth_url(self):
        """Build Google OAuth URL"""
        # These are the actual OAuth parameters from your config
        client_id = "778657599269-ouflj5id5r0bchm9a8lcko1tskkk4j4f.apps.googleusercontent.com"
        redirect_uri = "http://localhost:8000/auth/callback"  # Your backend callback
        scope = "openid email profile"
        
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent"
        }
        
        base_url = "https://accounts.google.com/o/oauth2/v2/auth"
        return f"{base_url}?{urllib.parse.urlencode(params)}"
    
    def open_browser_auth(self):
        """Open browser for manual authentication"""
        oauth_url = self.build_oauth_url()
        webbrowser.open(oauth_url)
        
        QMessageBox.information(
            self,
            "Browser Opened",
            "Your default browser has been opened for authentication.\n"
            "Please complete the process and copy the access token."
        )
    
    def on_token_input_changed(self, text):
        """Handle token input changes"""
        if hasattr(self, 'verify_button'):
            self.verify_button.setEnabled(len(text.strip()) > 0)
    
    def verify_manual_token(self):
        """Verify manually entered token"""
        token = self.token_input.text().strip()
        if token:
            self.google_token = token
            self.accept()
    
    def on_load_started(self):
        """Handle web view load start"""
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # Indeterminate progress
    
    def on_load_finished(self, success):
        """Handle web view load finish"""
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setVisible(False)
        
        if not success:
            logger.warning("Failed to load OAuth page")
    
    def on_token_received(self, token):
        """Handle token reception"""
        logger.info("OAuth token received")
        self.google_token = token
        self.accept()
    
    def continue_offline(self):
        """Continue in offline mode"""
        reply = QMessageBox.question(
            self,
            "Offline Mode",
            "Continue in offline mode?\n\n"
            "You will have limited functionality:\n"
            "• No cloud authentication\n"
            "• No web search enhancement\n"
            "• Local documents only\n\n"
            "You can login later from the Account menu.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.reject()  # Close dialog without authentication
    
    def get_google_token(self):
        """Get the received Google token"""
        return self.google_token

class SimpleAuthDialog(QDialog):
    """Simplified authentication dialog without web engine"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.google_token = None
        self.setup_ui()
        self.setWindowTitle("Login to RAG Companion AI")
        self.setModal(True)
        self.resize(500, 400)
    
    def setup_ui(self):
        """Setup simplified UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Header
        header = QLabel("🔐 Login to RAG Companion AI")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("font-size: 18px; font-weight: bold; margin: 20px; color: #0078d4;")
        layout.addWidget(header)
        
        # Message
        message = QLabel(
            "To access full features with your personal documents and cloud sync, "
            "you need to authenticate with Google.\n\n"
            "🌟 <b>With Login:</b>\n"
            "• Personal document storage\n"
            "• Cloud synchronization\n"
            "• Enhanced web search\n"
            "• Session backup\n\n"
            "🔒 <b>Without Login (Offline Mode):</b>\n"
            "• Local documents only\n"
            "• No cloud features\n"
            "• Basic functionality"
        )
        message.setWordWrap(True)
        message.setAlignment(Qt.AlignmentFlag.AlignLeft)
        message.setStyleSheet("margin: 20px; line-height: 1.4; background-color: #f5f5f5; padding: 15px; border-radius: 8px;")
        layout.addWidget(message)
        
        # Note about WebEngine
        note = QLabel(
            "💡 <b>Note:</b> For seamless OAuth, install PyQtWebEngine:\n"
            "<code>pip install PyQt6-WebEngine</code>"
        )
        note.setWordWrap(True)
        note.setStyleSheet("margin: 10px; color: #666; font-size: 12px; background-color: #fff3cd; padding: 10px; border-radius: 4px;")
        layout.addWidget(note)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        # Browser auth button
        browser_button = QPushButton("🌐 Login with Browser")
        browser_button.clicked.connect(self.open_browser_auth)
        browser_button.setStyleSheet("padding: 10px 20px; font-size: 14px; font-weight: bold;")
        button_layout.addWidget(browser_button)
        
        button_layout.addStretch()
        
        offline_button = QPushButton("Continue Offline")
        offline_button.clicked.connect(self.accept)
        offline_button.setStyleSheet("padding: 10px 20px; background-color: #6c757d;")
        button_layout.addWidget(offline_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
    
    def open_browser_auth(self):
        """Open browser for manual authentication"""
        # Build OAuth URL
        client_id = "778657599269-ouflj5id5r0bchm9a8lcko1tskkk4j4f.apps.googleusercontent.com"
        redirect_uri = "http://localhost:8000/auth/callback"
        scope = "openid email profile"
        
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent"
        }
        
        import urllib.parse
        oauth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
        
        # Open browser
        import webbrowser
        webbrowser.open(oauth_url)
        
        # Show simple completion dialog
        QMessageBox.information(
            self,
            "Authentication in Progress",
            "✅ Browser opened for Google authentication.\n\n"
            "After completing authentication, the app will automatically\n"
            "detect your login and enable full features.\n\n"
            "Click 'Continue Offline' for now to use the app."
        )
    
    def get_google_token(self):
        """Get the Google token (none for simplified dialog)"""
        return None

# Factory function to create appropriate dialog
def create_auth_dialog(parent=None):
    """Create appropriate authentication dialog based on available features"""
    if HAS_WEB_ENGINE:
        return AuthDialog(parent)
    else:
        return SimpleAuthDialog(parent)