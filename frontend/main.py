#!/usr/bin/env python3
"""
RAG Desktop Application - Main Entry Point
PyQt6-based desktop interface for the RAG system
"""

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtCore import QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QIcon, QAction
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
        logging.FileHandler('logs/frontend.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class RAGApplication(QApplication):
    """Main application class with system tray support"""
    
    def __init__(self, argv):
        super().__init__(argv)
        
        # Set application properties
        self.setApplicationName("RAG Companion AI")
        self.setApplicationDisplayName("RAG Companion AI")
        self.setApplicationVersion("1.0.0")
        self.setOrganizationName("RAG AI")
        self.setOrganizationDomain("ragcompanion.ai")
        
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
        
        logger.info("RAG Companion AI application initialized")
    
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
        
        # Create tray menu
        tray_menu = QMenu()
        
        # Show action
        show_action = QAction("Show RAG Companion", self)
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
        
        # Quit action
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        
        # Show tray icon
        self.tray_icon.show()
        self.tray_icon.showMessage(
            "RAG Companion AI",
            "Application started and running in system tray",
            QSystemTrayIcon.MessageIcon.Information,
            2000
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
        self.connection_timer.start(30000)  # Check every 30 seconds
        
        # Initial check
        QTimer.singleShot(1000, self.check_connection_status)
    
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
            logger.error(f"Connection check failed: {e}")
            if self.online_mode:
                self.online_mode = False
                self.update_connection_status()
                if self.main_window:
                    self.main_window.update_online_status(False)
    
    def update_connection_status(self):
        """Update tray icon tooltip and status"""
        if self.tray_icon:
            if self.online_mode:
                self.tray_icon.setToolTip("RAG Companion AI - Online")
                if hasattr(self, 'status_action'):
                    self.status_action.setText("Status: Online")
            else:
                self.tray_icon.setToolTip("RAG Companion AI - Offline")
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
    
    def on_window_closed(self):
        """Handle main window close event"""
        # Don't quit, window is now hidden to tray
        if self.tray_icon and self.tray_icon.isVisible():
            logger.info("Main window hidden to system tray")
        else:
            # No system tray, actually quit
            self.quit_application()
    
    def quit_application(self):
        """Properly quit the application"""
        logger.info("Shutting down RAG Companion AI")
        
        # Save session data
        if self.session_manager:
            self.session_manager.save_session()
        
        # Hide tray icon
        if self.tray_icon:
            self.tray_icon.hide()
        
        # Close main window
        if self.main_window:
            self.main_window.close()
        
        # Quit application
        self.quit()

def main():
    """Main entry point"""
    # Ensure required directories exist
    Path("logs").mkdir(exist_ok=True)
    Path("frontend/resources").mkdir(exist_ok=True)
    
    # Create application
    app = RAGApplication(sys.argv)
    
    # Handle system signals gracefully
    import signal
    signal.signal(signal.SIGINT, lambda sig, frame: app.quit_application())
    signal.signal(signal.SIGTERM, lambda sig, frame: app.quit_application())
    
    # Start application
    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        app.quit_application()
    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()