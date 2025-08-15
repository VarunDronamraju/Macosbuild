"""
Main Window for RAG Desktop Application
Contains the primary user interface with document management and chat - Dream UI Style
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
    QGroupBox, QComboBox, QCheckBox, QSpinBox, QSlider, QDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, QMimeData, QPropertyAnimation, QRect, QEasingCurve
from PyQt6.QtGui import (
    QAction, QFont, QPixmap, QIcon, QDragEnterEvent, QDropEvent,
    QKeySequence, QPalette, QColor, QPainter, QBrush, QLinearGradient, QRadialGradient
)

from frontend.api_client import APIClient, StreamingQueryThread
from frontend.session_manager import SessionManager, ChatSession
from frontend.auth_dialog import create_auth_dialog
from frontend.chat_widget import ChatWidget
from frontend.document_panel import DocumentPanel

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

class PulsingDot(QWidget):
    """Animated pulsing dot for connection status"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(8, 8)
        self.opacity = 1.0
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.updateOpacity)
        self.timer.start(50)  # Update every 50ms for smooth animation
        
        self.direction = -1  # -1 for decreasing, 1 for increasing
        
    def updateOpacity(self):
        self.opacity += self.direction * 0.05
        if self.opacity <= 0.5:
            self.direction = 1
        elif self.opacity >= 1.0:
            self.direction = -1
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setOpacity(self.opacity)
        painter.setBrush(QBrush(QColor(72, 187, 120)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, 8, 8)

class ChatItem(QFrame):
    """Individual chat history item"""
    clicked = pyqtSignal()
    
    def __init__(self, title, preview, is_active=False):
        super().__init__()
        self.title = title
        self.preview = preview
        self.is_active = is_active
        self.setFixedHeight(40)  # Even more compact
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QHBoxLayout()  # Changed to horizontal for cleaner look
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(0)
        
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 13, QFont.Weight.Medium))
        title_label.setStyleSheet("color: #2d3748; font-weight: 500;")
        
        layout.addWidget(title_label)
        layout.addStretch()
        self.setLayout(layout)
        
        self.updateStyle()
        
    def updateStyle(self):
        if self.is_active:
            self.setStyleSheet("""
                QFrame {
                    background: rgba(120, 220, 180, 0.15);
                    border: none;
                    border-radius: 8px;
                    margin-bottom: 8px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background: transparent;
                    border: none;
                    border-radius: 8px;
                    margin-bottom: 8px;
                }
                QFrame:hover {
                    background: rgba(120, 220, 180, 0.1);
                }
            """)
    
    def mousePressEvent(self, event):
        self.clicked.emit()

class ToggleSwitch(QWidget):
    """Custom toggle switch widget"""
    toggled = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.is_active = False
        
    def mousePressEvent(self, event):
        self.is_active = not self.is_active
        self.toggled.emit(self.is_active)
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background
        if self.is_active:
            painter.setBrush(QBrush(QColor(120, 220, 180)))
        else:
            painter.setBrush(QBrush(QColor(226, 232, 240)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, 40, 20, 10, 10)
        
        # Circle
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        if self.is_active:
            painter.drawEllipse(22, 2, 16, 16)
        else:
            painter.drawEllipse(2, 2, 16, 16)

class UserMenuDialog(QDialog):
    """Dream UI styled user menu dialog"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("User Menu")
        self.setFixedSize(400, 500)
        self.setModal(True)
        
        # Remove window frame for custom styling
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("User Menu")
        title.setFont(QFont("Arial", 16, QFont.Weight.DemiBold))
        title.setStyleSheet("color: #2d3748;")
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet("""
            QPushButton {
                background: none;
                border: none;
                font-size: 20px;
                color: #a0aec0;
            }
            QPushButton:hover {
                color: #78dcb4;
            }
        """)
        close_btn.clicked.connect(self.close)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)
        
        layout.addLayout(header_layout)
        layout.addSpacing(20)
        
        # Menu items
        menu_items = [
            ("[CLIPBOARD]", "Prompt History", self.showPromptHistory),
            ("📁", "Data Controls", self.showDataControls),
            ("👤", "Personal Details", self.showPersonalDetails),
            ("☀", "Theme", self.changeTheme),
            ("❓", "Help & Support", self.showHelp),
            ("☁", "Cloud Documents", self.showCloudDocuments),
            ("🚪", "Logout", self.logout)
        ]
        
        for icon, text, callback in menu_items:
            item_layout = QHBoxLayout()
            
            icon_label = QLabel(icon)
            icon_label.setFixedSize(16, 16)
            
            text_label = QLabel(text)
            text_label.setFont(QFont("Arial", 11))
            
            item_widget = QWidget()
            item_widget.setLayout(item_layout)
            item_widget.setFixedHeight(40)
            item_widget.setCursor(Qt.CursorShape.PointingHandCursor)
            
            if text == "Data Controls":
                toggle = ToggleSwitch()
                item_layout.addWidget(icon_label)
                item_layout.addWidget(text_label)
                item_layout.addStretch()
                item_layout.addWidget(toggle)
            else:
                item_layout.addWidget(icon_label)
                item_layout.addWidget(text_label)
                item_layout.addStretch()
            
            item_widget.mousePressEvent = lambda e, cb=callback: cb()
            
            item_widget.setStyleSheet("""
                QWidget:hover {
                    background: rgba(120, 220, 180, 0.05);
                    border-radius: 4px;
                }
            """)
            
            layout.addWidget(item_widget)
            
            # Add separator
            if text != "Logout":
                separator = QFrame()
                separator.setFrameShape(QFrame.Shape.HLine)
                separator.setStyleSheet("background: rgba(0, 0, 0, 0.05); margin: 4px 0;")
                layout.addWidget(separator)
        
        self.setLayout(layout)
        
        # Styling
        self.setStyleSheet("""
            QDialog {
                background: white;
                border-radius: 16px;
                border: 1px solid rgba(0, 0, 0, 0.05);
            }
        """)
        
    def showPromptHistory(self):
        QMessageBox.information(self, "Prompt History", 
                               "Total queries: 4\n\nRecent prompts:\n• Getting started with CompanionAI\n• Document analysis request\n• Wellness strategies discussion")
        self.close()
        
    def showDataControls(self):
        QMessageBox.information(self, "Data Controls", 
                               "Ingested Documents:\n• Project_Report_Q4.pdf\n• Wellness_Guidelines.docx\n• Team_Analytics.xlsx\n\nCloud storage: Disabled")
        self.close()
        
    def showPersonalDetails(self):
        QMessageBox.information(self, "Personal Details", 
                               "Name: User\nEmail: user@company.com\nRole: Team Member\nSubscription: Pro")
        self.close()
        
    def changeTheme(self):
        QMessageBox.information(self, "Theme Options", 
                               "• Light Theme (Current)\n• Dark Theme\n• Auto (System)\n• High Contrast")
        self.close()
        
    def showHelp(self):
        QMessageBox.information(self, "Help & Support", 
                               "• Report Bug\n• Send Feedback\n• Documentation\n• Contact Support\n• Feature Requests")
        self.close()
        
    def showCloudDocuments(self):
        QMessageBox.information(self, "Cloud Documents", 
                               "Stored Documents:\n• Analysis_Report.pdf (2.1 MB)\n• Meeting_Notes.docx (856 KB)\n• Data_Export.csv (1.3 MB)\n\nTotal: 4.3 MB / 50 MB used")
        self.close()
        
    def logout(self):
        reply = QMessageBox.question(self, "Logout", "Are you sure you want to logout?", 
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.parent().logout()
        self.close()

class MainWindow(QMainWindow):
    """Main application window with Dream UI styling"""
    
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
        self.chat_items = []
        
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
        """Setup the main user interface in Dream UI style"""
        self.setWindowTitle("CompanionAI")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        
        # Central widget with gradient background
        central_widget = GradientWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout - vertical structure like dream UI
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header
        header = self.create_header()
        main_layout.addWidget(header)
        
        # Content area with horizontal splitter
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        content_splitter.setStyleSheet("""
            QSplitter::handle {
                background: rgba(0, 0, 0, 0.05);
                width: 3px;
            }
            QSplitter::handle:hover {
                background: rgba(120, 220, 180, 0.3);
            }
        """)
        
        # Left sidebar - Chat history (280px like dream UI)
        self.sidebar = self.create_sidebar()
        self.sidebar.setFixedWidth(280)
        content_splitter.addWidget(self.sidebar)
        
        # Right panel - Chat interface
        self.chat_widget = ChatWidget(self.api_client, self.session_manager)
        self.chat_widget.main_window = self  # Pass reference to main window
        self.chat_widget.setMinimumWidth(400)
        content_splitter.addWidget(self.chat_widget)
        
        # Set splitter proportions
        content_splitter.setSizes([280, 920])
        content_splitter.setChildrenCollapsible(False)
        
        main_layout.addWidget(content_splitter)
    
    def create_header(self):
        """Create the header with title and connection status"""
        header = QFrame()
        header.setFixedHeight(60)
        header.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.95);
                border-bottom: 1px solid rgba(0, 0, 0, 0.05);
            }
        """)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(20, 0, 20, 0)
        
        # Title
        title = QLabel("CompanionAI")
        title.setFont(QFont("Arial", 16, QFont.Weight.DemiBold))
        title.setStyleSheet("color: #2d3748; letter-spacing: -0.5px;")
        
        # Connection status
        status_widget = QWidget()
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(8)
        
        # Pulsing dot for connection status
        self.connection_dot = PulsingDot()
        
        self.connection_status_label = QLabel("Connected")
        self.connection_status_label.setFont(QFont("Arial", 11))
        self.connection_status_label.setStyleSheet("color: #48bb78;")
        
        status_layout.addWidget(self.connection_dot)
        status_layout.addWidget(self.connection_status_label)
        status_widget.setLayout(status_layout)
        
        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(status_widget)
        
        header.setLayout(layout)
        return header
    
    def create_sidebar(self):
        """Create the sidebar with chat history"""
        sidebar = QFrame()
        sidebar.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.95);
                border-right: 1px solid rgba(120, 220, 180, 0.15);
                border-radius: 0px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Sidebar header
        sidebar_header = QFrame()
        sidebar_header.setFixedHeight(50)  # Reduced height
        sidebar_header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 rgba(255, 255, 255, 0.98),
                                          stop:1 rgba(248, 255, 254, 0.95));
                border-bottom: 1px solid rgba(120, 220, 180, 0.15);
                border-radius: 0px;
            }
        """)
        
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(20, 8, 20, 8)  # Reduced margins
        
        # Add New Chat button
        new_chat_btn = QPushButton("✨ New Chat")
        new_chat_btn.setFixedHeight(30)  # Slightly smaller
        new_chat_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                          stop:0 #78dcb4, stop:1 #68d391);
                border: none;
                border-radius: 15px;
                color: white;
                font-size: 11px;
                font-weight: bold;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                          stop:0 #68d391, stop:1 #48bb78);
            }
        """)
        new_chat_btn.clicked.connect(self.create_new_chat)
        header_layout.addWidget(new_chat_btn)
        
        sidebar_header.setLayout(header_layout)
        
        # Chat history scroll area
        history_scroll = QScrollArea()
        history_scroll.setWidgetResizable(True)
        history_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        history_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        history_scroll.setStyleSheet("""
            QScrollArea { 
                border: none; 
                background: transparent;
            }
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 0.3);
                width: 8px;
                border-radius: 4px;
                margin: 1px;
            }
            QScrollBar::handle:vertical {
                background: rgba(120, 220, 180, 0.7);
                border-radius: 4px;
                min-height: 20px;
                margin: 1px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(120, 220, 180, 0.9);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        history_widget = QWidget()
        self.history_layout = QVBoxLayout()
        self.history_layout.setContentsMargins(20, 15, 20, 15)  # Reduced margins
        self.history_layout.setSpacing(4)  # Reduced spacing between items
        
        # Load existing chat sessions
        self.load_chat_history()
        
        self.history_layout.addStretch()
        history_widget.setLayout(self.history_layout)
        history_scroll.setWidget(history_widget)
        
        # Profile section at bottom
        profile_section = QFrame()
        profile_section.setFixedHeight(110)  # Increased height
        profile_section.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 rgba(248, 255, 254, 0.95),
                                          stop:1 rgba(255, 255, 255, 0.98));
                border-top: 1px solid rgba(120, 220, 180, 0.2);
                border-radius: 0px;
            }
        """)
        
        profile_layout = QHBoxLayout()  # Changed to horizontal layout
        profile_layout.setContentsMargins(20, 15, 20, 15)
        profile_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        profile_btn = QPushButton("👤")
        profile_btn.setFixedSize(55, 55)
        profile_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                          stop:0 #78dcb4, stop:1 #68d391);
                border: 2px solid rgba(120, 220, 180, 0.3);
                border-radius: 28px;
                color: white;
                font-size: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                          stop:0 #68d391, stop:1 #48bb78);
                border: 2px solid rgba(120, 220, 180, 0.5);
            }
        """)
        profile_btn.clicked.connect(self.show_user_menu)
        
        # User info
        user_info_layout = QVBoxLayout()
        user_info_layout.setContentsMargins(0, 0, 0, 0)
        user_info_layout.setSpacing(2)
        
        user_name_label = QLabel("Varun Dronamraju")
        user_name_label.setFont(QFont("Arial", 13, QFont.Weight.DemiBold))
        user_name_label.setStyleSheet("color: #2d3748; margin-bottom: 2px;")
        
        user_email_label = QLabel("varun.18903@gmail.com")
        user_email_label.setFont(QFont("Arial", 11))
        user_email_label.setStyleSheet("color: #718096; font-weight: 500;")
        
        user_info_layout.addWidget(user_name_label)
        user_info_layout.addWidget(user_email_label)
        
        profile_layout.addWidget(profile_btn)
        profile_layout.addSpacing(12)
        profile_layout.addLayout(user_info_layout)
        profile_layout.addStretch()
        
        profile_section.setLayout(profile_layout)
        
        layout.addWidget(sidebar_header)  # Add the header
        layout.addWidget(history_scroll)
        layout.addWidget(profile_section)
        sidebar.setLayout(layout)
        
        return sidebar
    
    def load_chat_history(self):
        """Load chat history items from session manager"""
        # Clear existing items
        for item in self.chat_items:
            item.deleteLater()
        self.chat_items.clear()
        
        # Load sessions from session manager
        sessions = self.session_manager.get_all_sessions()
        current_session = self.session_manager.get_current_session()
        
        # If no sessions, add default items
        if not sessions:
            chat_items_data = [
                ("Chat 1", "", True),
                ("Chat 2", "", False),
                ("Chat 3", "", False),
                ("Chat 4", "", False)
            ]
            
            for title, preview, is_active in chat_items_data:
                item = self.create_chat_item(title, preview, is_active)
                self.history_layout.insertWidget(self.history_layout.count() - 1, item)
                self.chat_items.append(item)
        else:
            # Load actual sessions with simple numbering
            for i, session in enumerate(sessions[:10], 1):  # Show only last 10 sessions
                title = f"Chat {i}"
                is_active = current_session and session.id == current_session.id
                
                item = self.create_chat_item(title, "", is_active, session.id)
                self.history_layout.insertWidget(self.history_layout.count() - 1, item)
                self.chat_items.append(item)
    
    def create_chat_item(self, title, preview, is_active=False, session_id=None):
        """Create a chat history item"""
        item = ChatItem(title, preview, is_active)
        item.session_id = session_id  # Store session ID
        item.clicked.connect(lambda: self.select_chat_item(item))
        return item
    
    def select_chat_item(self, selected_item):
        """Handle chat item selection"""
        # Update visual state
        for item in self.chat_items:
            item.is_active = (item == selected_item)
            item.updateStyle()
        
        # Switch to session if it exists
        if hasattr(selected_item, 'session_id') and selected_item.session_id:
            self.chat_widget.switch_to_session(selected_item.session_id)
        else:
            # Create new session for demo items
            session_id = self.session_manager.create_session(selected_item.title)
            self.chat_widget.switch_to_session(session_id)
            self.load_chat_history()  # Refresh to show new session
    
    def show_user_menu(self):
        """Show user menu dialog"""
        dialog = UserMenuDialog(self)
        dialog.exec()
    
    def setup_menu_bar(self):
        """Setup the menu bar"""
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background: rgba(255, 255, 255, 0.95);
                color: #2d3748;
                border-bottom: 1px solid rgba(0, 0, 0, 0.05);
                padding: 4px;
            }
            QMenuBar::item {
                background: transparent;
                padding: 8px 12px;
                border-radius: 4px;
            }
            QMenuBar::item:selected {
                background: rgba(120, 220, 180, 0.1);
            }
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
        
        # New chat
        new_chat_action = QAction("&New Chat", self)
        new_chat_action.setShortcut(QKeySequence("Ctrl+N"))
        new_chat_action.triggered.connect(self.create_new_chat)
        edit_menu.addAction(new_chat_action)
        
        # Clear chat
        clear_action = QAction("&Clear Current Chat", self)
        clear_action.setShortcut(QKeySequence("Ctrl+L"))
        clear_action.triggered.connect(self.clear_current_chat)
        edit_menu.addAction(clear_action)
        
        edit_menu.addSeparator()
        
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
        
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background: rgba(255, 255, 255, 0.95);
                color: #2d3748;
                border: none;
                padding: 4px;
            }
            QStatusBar::item {
                border: none;
            }
            QStatusBar QLabel {
                color: #2d3748;
                padding: 2px 8px;
            }
        """)
        
        # Connection status
        self.connection_label = QLabel("Checking connection...")
        self.status_bar.addPermanentWidget(self.connection_label)
        
        # User info
        self.user_label = QLabel("Not logged in")
        self.status_bar.addPermanentWidget(self.user_label)
        
        # Progress bar for operations
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background: rgba(255, 255, 255, 0.6);
                border: 1px solid rgba(0, 0, 0, 0.05);
                border-radius: 8px;
                text-align: center;
                color: #2d3748;
                height: 16px;
            }
            QProgressBar::chunk {
                background: #78dcb4;
                border-radius: 6px;
                margin: 1px;
            }
        """)
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
        # Dream UI styles are applied via setStyleSheet in each component
        pass
    
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
            
            # Also set the token in API client if we have one
            token = self.session_manager.get_setting("auth_token")
            if token:
                self.api_client.set_auth_token(token, user_info)
    
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
                QMessageBox.information(self, "Document Upload", 
                                       f"Found {len(valid_files)} documents. Document panel integration coming soon!")
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
            self.connection_label.setText("[GREEN] Online")
            self.connection_status_label.setText("Connected")
            self.connection_status_label.setStyleSheet("color: #48bb78;")
            self.status_bar.showMessage("Connected to backend", 3000)
        else:
            self.connection_label.setText("[RED] Offline")
            self.connection_status_label.setText("Disconnected")
            self.connection_status_label.setStyleSheet("color: #e53e3e;")
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
            self.user_label.setText(f"👤 {user_info.get('name', user_info.get('email', 'User'))}")
            self.session_manager.set_user_info(user_info)
            
            # Store auth token if we have one
            if hasattr(self.api_client, 'access_token') and self.api_client.access_token:
                self.session_manager.set_setting("auth_token", self.api_client.access_token)
        else:
            self.user_label.setText("👤 Not logged in")
            self.current_user = None
            # Clear stored token
            self.session_manager.set_setting("auth_token", None)
        
        self.update_auth_menu()
        
        # Update widgets
        if self.document_panel:
            self.document_panel.update_auth_state(is_authenticated, user_info)
        if self.chat_widget:
            self.chat_widget.update_auth_state(is_authenticated, user_info)
        
        # Refresh chat history when auth state changes
        self.load_chat_history()
    
    def update_auth_menu(self):
        """Update authentication menu items"""
        self.login_action.setVisible(not self.is_authenticated)
        self.logout_action.setVisible(self.is_authenticated)
    
    def create_new_chat(self):
        """Create a new chat session"""
        session_id = self.session_manager.create_session()
        self.chat_widget.switch_to_session(session_id)
        self.load_chat_history()  # Refresh sidebar
        self.chat_widget.message_input.setFocus()
    
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
                    
                    # Store the access token
                    access_token = result.get("data", {}).get("access_token")
                    if access_token:
                        self.api_client.set_auth_token(access_token, self.current_user)
                        self.session_manager.set_setting("auth_token", access_token)
                    
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
            
            # Clear session manager user info (this will also clear sessions)
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
        elif file_path:
            QMessageBox.information(self, "Document Import", 
                                   f"Document panel not available. File selected: {Path(file_path).name}")
    
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
                self.load_chat_history()  # Refresh sidebar
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
        else:
            QMessageBox.information(self, "Document Panel", "Document panel not available in this view")
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About CompanionAI",
            """
            <h3>CompanionAI v1.0.0</h3>
            <p>A privacy-first document intelligence assistant with Dream UI</p>
            <p>Features:</p>
            <ul>
            <li>Beautiful modern interface</li>
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
        self.load_chat_history()  # Refresh sidebar
    
    def on_session_updated(self, session_id: str):
        """Handle session update"""
        self.load_chat_history()  # Refresh sidebar
    
    def on_session_deleted(self, session_id: str):
        """Handle session deletion"""
        self.load_chat_history()  # Refresh sidebar
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Clean up offline data before closing
        if self.session_manager:
            self.session_manager.cleanup_offline_data()
        
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
                "CompanionAI",
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