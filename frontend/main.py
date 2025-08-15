#!/usr/bin/env python3
"""
RAG Desktop Application - Main Entry Point
PyQt6-based desktop interface for the RAG system with Dream UI styling
"""

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox
from PyQt6.QtCore import QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QIcon, QAction, QPalette, QColor
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from frontend.main_window import MainWindow
from frontend.session_manager import SessionManager
from frontend.api_client import APIClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/frontend.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class RAGApplication(QApplication):
    """Main application class with system tray support and Dream UI styling"""
    
    def __init__(self, argv):
        super().__init__(argv)
        
        # Set application properties
        self.setApplicationName("CompanionAI")
        self.setApplicationDisplayName("CompanionAI")
        self.setApplicationVersion("1.0.0")
        self.setOrganizationName("RAG AI")
        self.setOrganizationDomain("companionai.app")
        
        # Apply Dream UI theme
        self.apply_dream_ui_theme()
        
        # Initialize components
        self.session_manager = SessionManager()
        self.api_client = APIClient()
        self.main_window = None
        self.tray_icon = None
        
        # Connection status
        self.online_mode = True
        
        # Setup application
        self.setup_tray_icon()
        self.setup_main_window()
        self.setup_connection_monitor()
        
        logger.info("CompanionAI application initialized with Dream UI")
    
    def apply_dream_ui_theme(self):
        """Apply Dream UI color scheme and styling"""
        # Set application style
        dream_style = """
        QApplication {
            font-family: "Segoe UI", "Arial", sans-serif;
            font-size: 13px;
        }
        
        QMainWindow {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                      stop:0 #f8fffe, stop:1 #f0f9f7);
            color: #2d3748;
        }
        
        QWidget {
            background: transparent;
            color: #2d3748;
        }
        
        QMessageBox {
            background: white;
            border-radius: 12px;
        }
        
        QMessageBox QLabel {
            color: #2d3748;
            font-size: 13px;
        }
        
        QMessageBox QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                      stop:0 #78dcb4, stop:1 #68d391);
            border: none;
            border-radius: 6px;
            color: white;
            padding: 8px 16px;
            font-weight: 500;
            min-width: 80px;
        }
        
        QMessageBox QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                      stop:0 #68d391, stop:1 #48bb78);
        }
        
        QFileDialog {
            background: white;
            color: #2d3748;
        }
        
        QFileDialog QListView {
            background: rgba(255, 255, 255, 0.8);
            border: 1px solid rgba(0, 0, 0, 0.05);
            border-radius: 8px;
        }
        
        QFileDialog QTreeView {
            background: rgba(255, 255, 255, 0.8);
            border: 1px solid rgba(0, 0, 0, 0.05);
            border-radius: 8px;
        }
        
        QFileDialog QPushButton {
            background: #78dcb4;
            border: 1px solid #68d391;
            color: white;
            padding: 6px 12px;
            border-radius: 6px;
            font-weight: 500;
        }
        
        QFileDialog QPushButton:hover {
            background: #68d391;
        }
        """
        
        self.setStyleSheet(dream_style)
    
    def setup_tray_icon(self):
        """Setup system tray icon and menu"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.warning("System tray not available")
            return
        
        # Create tray icon
        self.tray_icon = QSystemTrayIcon(self)
        
        # Set icon (you can replace with actual icon file)
        try:
            icon_path = Path("frontend/resources/app_icon.png")
            if icon_path.exists():
                self.tray_icon.setIcon(QIcon(str(icon_path)))
            else:
                # Use default icon
                self.tray_icon.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))
        except:
            self.tray_icon.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))
        
        # Create tray menu with Dream UI styling
        tray_menu = QMenu()
        tray_menu.setStyleSheet("""
            QMenu {
                background: white;
                border: 1px solid rgba(0, 0, 0, 0.05);
                border-radius: 8px;
                padding: 4px 0;
            }
            QMenu::item {
                padding: 8px 16px;
                color: #2d3748;
            }
            QMenu::item:selected {
                background: rgba(120, 220, 180, 0.1);
            }
        """)
        
        # Show action
        show_action = QAction("Show CompanionAI", self)
        show_action.triggered.connect(self.show_main_window)
        tray_menu.addAction(show_action)
        
        # Separator
        tray_menu.addSeparator()
        
        # Status action
        self.status_action = QAction("Status: Checking...", self)
        self.status_action.setEnabled(False)
        tray_menu.addAction(self.status_action)
        
        # Separator
        tray_menu.addSeparator()
        
        # New chat action
        new_chat_action = QAction("New Chat", self)
        new_chat_action.triggered.connect(self.create_new_chat)
        tray_menu.addAction(new_chat_action)
        
        # Separator
        tray_menu.addSeparator()
        
        # Quit action
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        
        # Show tray icon
        self.tray_icon.show()
        self.tray_icon.showMessage(
            "CompanionAI",
            "Application started with beautiful Dream UI design",
            QSystemTrayIcon.MessageIcon.Information,
            3000
        )
    
    def setup_main_window(self):
        """Initialize main window"""
        self.main_window = MainWindow(
            api_client=self.api_client,
            session_manager=self.session_manager,
            app=self
        )
        
        # Connect window signals
        self.main_window.window_closed.connect(self.on_window_closed)
        
        # Show window initially
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()
    
    def setup_connection_monitor(self):
        """Setup connection monitoring timer"""
        self.connection_timer = QTimer()
        self.connection_timer.timeout.connect(self.check_connection_status)
        self.connection_timer.start(60000)  # Check every 60 seconds for presentation
        
        # Initial check
        QTimer.singleShot(5000, self.check_connection_status)  # Delayed initial check
    
    def check_connection_status(self):
        """Check API connection status"""
        try:
            # Check if backend is available
            is_online = self.api_client.check_health()
            
            if is_online != self.online_mode:
                self.online_mode = is_online
                self.update_connection_status()
                
                # Notify main window
                if self.main_window:
                    self.main_window.update_online_status(is_online)
        except Exception as e:
            # Silent error handling for presentation
            if self.online_mode:
                self.online_mode = False
                self.update_connection_status()
                if self.main_window:
                    self.main_window.update_online_status(False)
    
    def update_connection_status(self):
        """Update tray icon tooltip and status"""
        if self.tray_icon:
            if self.online_mode:
                self.tray_icon.setToolTip("CompanionAI - Online")
                if hasattr(self, 'status_action'):
                    self.status_action.setText("Status: Online")
            else:
                self.tray_icon.setToolTip("CompanionAI - Offline")
                if hasattr(self, 'status_action'):
                    self.status_action.setText("Status: Offline")
    
    def on_tray_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_main_window()
    
    def show_main_window(self):
        """Show and raise main window"""
        if self.main_window:
            if not self.main_window.isVisible():
                self.main_window.show()
            self.main_window.raise_()
            self.main_window.activateWindow()
    
    def create_new_chat(self):
        """Create new chat from tray menu"""
        if self.main_window:
            self.show_main_window()
            self.main_window.create_new_chat()
    
    def on_window_closed(self):
        """Handle main window close event"""
        # Don't quit, window is now hidden to tray
        if self.tray_icon and self.tray_icon.isVisible():
            logger.info("Main window hidden to system tray")
            self.tray_icon.showMessage(
                "CompanionAI",
                "Application is still running in the background",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
        else:
            # No system tray, actually quit
            self.quit_application()
    
    def quit_application(self):
        """Properly quit the application"""
        logger.info("Shutting down CompanionAI")
        
        # Save session data
        if self.session_manager:
            self.session_manager.save_session()
        
        # Show goodbye message
        if self.tray_icon:
            self.tray_icon.showMessage(
                "CompanionAI",
                "Thank you for using CompanionAI. Goodbye! 👋",
                QSystemTrayIcon.MessageIcon.Information,
                1000
            )
        
        # Hide tray icon
        if self.tray_icon:
            self.tray_icon.hide()
        
        # Close main window
        if self.main_window:
            self.main_window.close()
        
        # Quit application
        QTimer.singleShot(1000, self.quit)

def show_startup_splash():
    """Show a startup message"""
    logger.info("Starting CompanionAI with Dream UI...")
    print("CompanionAI - Beautiful AI Assistant")
    print("Loading Dream UI components...")

def main():
    """Main entry point"""
    # Show startup message
    show_startup_splash()
    
    # Ensure required directories exist
    Path("logs").mkdir(exist_ok=True)
    Path("frontend/resources").mkdir(exist_ok=True)
    
    # Create application
    app = RAGApplication(sys.argv)
    
    # Handle system signals gracefully
    import signal
    signal.signal(signal.SIGINT, lambda sig, frame: app.quit_application())
    signal.signal(signal.SIGTERM, lambda sig, frame: app.quit_application())
    
    # Show ready message
    logger.info("[SUCCESS] CompanionAI ready with Dream UI styling")
    
    # Start application
    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        app.quit_application()
    except Exception as e:
        logger.error(f"Application error: {e}")
        # Show error dialog
        try:
            from PyQt6.QtWidgets import QMessageBox
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setWindowTitle("CompanionAI Error")
            msg.setText("An unexpected error occurred:")
            msg.setDetailedText(str(e))
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.exec()
        except:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()