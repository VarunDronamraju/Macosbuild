"""
Document Panel for RAG Desktop Application
Handles document upload, management, and display - Dream UI Style
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, 
    QListWidgetItem, QLabel, QProgressBar, QGroupBox, QFileDialog,
    QMessageBox, QMenu, QFrame, QTextEdit, QSplitter, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, QMimeData
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QAction, QFont, QPainter, QBrush, QLinearGradient, QRadialGradient, QColor

from frontend.api_client import APIClient
from frontend.session_manager import SessionManager

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

class DocumentItem(QListWidgetItem):
    """Custom list item for documents with Dream UI styling"""
    
    def __init__(self, document_data: Dict):
        super().__init__()
        
        self.document_data = document_data
        self.update_display()
    
    def update_display(self):
        """Update the display text"""
        filename = self.document_data.get("filename", "Unknown")
        file_type = self.document_data.get("file_type", "").upper()
        status = self.document_data.get("processing_status", "unknown")
        
        # Status emoji with better styling
        status_emoji = {
            "completed": "[SUCCESS]",
            "processing": "⏳",
            "pending": "⏸️",
            "failed": "[FAIL]"
        }.get(status, "❓")
        
        self.setText(f"{status_emoji} {filename}")
        
        # Tooltip with details
        file_size = self.document_data.get("file_size", 0)
        chunk_count = self.document_data.get("chunk_count", 0)
        upload_date = self.document_data.get("upload_date", "")
        
        size_str = self.format_file_size(file_size)
        
        tooltip = f"""
        [DOC] {filename}
        📂 Type: {file_type}
        📊 Size: {size_str}
        ⚡ Status: {status.title()}
        🧩 Chunks: {chunk_count}
        📅 Uploaded: {upload_date.split('T')[0] if upload_date else 'Unknown'}
        """
        self.setToolTip(tooltip.strip())
        
        # Store document ID
        self.setData(Qt.ItemDataRole.UserRole, self.document_data.get("id"))
    
    def format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"

class UploadThread(QThread):
    """Thread for uploading documents"""
    
    upload_progress = pyqtSignal(str, int)  # filename, percentage
    upload_completed = pyqtSignal(str, dict)  # filename, result
    upload_failed = pyqtSignal(str, str)  # filename, error
    
    def __init__(self, api_client: APIClient, file_paths: List[str], use_legacy: bool = False):
        super().__init__()
        self.api_client = api_client
        self.file_paths = file_paths
        self.use_legacy = use_legacy
    
    def run(self):
        """Run upload process"""
        for file_path in self.file_paths:
            filename = Path(file_path).name
            
            try:
                # Emit initial progress
                self.upload_progress.emit(filename, 0)
                
                # Upload file
                if self.use_legacy:
                    result = self.api_client.upload_document_legacy(file_path, filename)
                else:
                    result = self.api_client.upload_document(file_path, filename)
                
                # Simulate progress (since we don't have real progress from API)
                for i in range(10, 101, 10):
                    self.upload_progress.emit(filename, i)
                    self.msleep(100)
                
                if result["success"]:
                    self.upload_completed.emit(filename, result)
                else:
                    # Ensure error is a string
                    error_msg = result.get("error", "Unknown error")
                    if isinstance(error_msg, list):
                        error_msg = "; ".join(error_msg)
                    elif not isinstance(error_msg, str):
                        error_msg = str(error_msg)
                    self.upload_failed.emit(filename, error_msg)
                    
            except Exception as e:
                self.upload_failed.emit(filename, str(e))

class DocumentPanel(QWidget):
    """Document management panel with Dream UI styling"""
    
    document_uploaded = pyqtSignal(str)  # filename
    document_deleted = pyqtSignal(str)   # filename
    
    def __init__(self, api_client: APIClient, session_manager: SessionManager):
        super().__init__()
        
        self.api_client = api_client
        self.session_manager = session_manager
        
        # State
        self.is_authenticated = False
        self.is_online = True
        self.current_user = None
        self.documents = []
        self.upload_thread = None
        
        # UI Components
        self.document_list = None
        self.upload_button = None
        self.refresh_button = None
        self.delete_button = None
        self.status_label = None
        self.progress_bar = None
        
        self.setup_ui()
        self.setup_signals()
        self.setup_drag_drop()
        
        # Initial load
        QTimer.singleShot(1000, self.refresh_documents)
        
        logger.info("Document panel initialized")
    
    def setup_ui(self):
        """Setup the user interface in Dream UI style"""
        # Create main widget with gradient background
        main_widget = GradientWidget()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(main_widget)
        
        # Content layout
        content_layout = QVBoxLayout(main_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("[DOC] Documents")
        title_label.setFont(QFont("Arial", 18, QFont.Weight.DemiBold))
        title_label.setStyleSheet("color: #2d3748; margin-bottom: 10px;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Refresh button
        self.refresh_button = QPushButton("🔄")
        self.refresh_button.setToolTip("Refresh document list")
        self.refresh_button.clicked.connect(self.refresh_documents)
        self.refresh_button.setFixedSize(36, 36)
        self.refresh_button.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.8);
                border: 1px solid rgba(0, 0, 0, 0.05);
                border-radius: 18px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: rgba(120, 220, 180, 0.1);
                border: 1px solid rgba(120, 220, 180, 0.2);
            }
        """)
        header_layout.addWidget(self.refresh_button)
        
        content_layout.addLayout(header_layout)
        
        # Upload area
        upload_area = self.create_upload_area()
        content_layout.addWidget(upload_area)
        
        # Document list
        list_area = self.create_document_list()
        content_layout.addWidget(list_area)
        
        content_layout.addStretch()
    
    def create_upload_area(self):
        """Create the upload area with Dream UI styling"""
        upload_frame = QFrame()
        upload_frame.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.7);
                border: 1px solid rgba(0, 0, 0, 0.05);
                border-radius: 16px;
                padding: 20px;
            }
        """)
        
        layout = QVBoxLayout(upload_frame)
        layout.setSpacing(16)
        
        # Upload title
        upload_title = QLabel("Upload Documents")
        upload_title.setFont(QFont("Arial", 14, QFont.Weight.Medium))
        upload_title.setStyleSheet("color: #2d3748; margin-bottom: 8px;")
        layout.addWidget(upload_title)
        
        # Drop zone
        self.drop_zone = QFrame()
        self.drop_zone.setFrameStyle(QFrame.Shape.NoFrame)
        self.drop_zone.setStyleSheet("""
            QFrame {
                border: 2px dashed rgba(120, 220, 180, 0.5);
                border-radius: 12px;
                background: rgba(248, 255, 254, 0.8);
                min-height: 100px;
                padding: 20px;
            }
            QFrame:hover {
                border-color: #78dcb4;
                background: rgba(120, 220, 180, 0.05);
            }
        """)
        
        drop_layout = QVBoxLayout(self.drop_zone)
        drop_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Drop zone icon and text
        drop_icon = QLabel("📁")
        drop_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_icon.setStyleSheet("font-size: 32px; margin-bottom: 8px;")
        drop_layout.addWidget(drop_icon)
        
        drop_label = QLabel("Drag & Drop Documents Here\nor click Upload to browse")
        drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_label.setStyleSheet("color: #4a5568; font-size: 12px; line-height: 1.4;")
        drop_layout.addWidget(drop_label)
        
        layout.addWidget(self.drop_zone)
        
        # Upload buttons
        button_layout = QHBoxLayout()
        
        self.upload_button = QPushButton("📤 Upload Files...")
        self.upload_button.clicked.connect(self.select_and_upload_files)
        self.upload_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                          stop:0 #78dcb4, stop:1 #68d391);
                border: none;
                border-radius: 8px;
                color: white;
                padding: 10px 20px;
                font-weight: 500;
                font-size: 12px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                          stop:0 #68d391, stop:1 #48bb78);
            }
            QPushButton:disabled {
                background: #e2e8f0;
                color: #a0aec0;
            }
        """)
        button_layout.addWidget(self.upload_button)
        
        button_layout.addStretch()
        
        # Supported formats info
        formats_label = QLabel("Supported: PDF, DOCX, TXT, MD")
        formats_label.setStyleSheet("color: #718096; font-size: 10px;")
        button_layout.addWidget(formats_label)
        
        layout.addLayout(button_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background: rgba(255, 255, 255, 0.8);
                border: 1px solid rgba(0, 0, 0, 0.05);
                border-radius: 8px;
                text-align: center;
                color: #2d3748;
                height: 20px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                                          stop:0 #78dcb4, stop:1 #68d391);
                border-radius: 6px;
                margin: 1px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        return upload_frame
    
    def create_document_list(self):
        """Create the document list area"""
        list_frame = QFrame()
        list_frame.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.7);
                border: 1px solid rgba(0, 0, 0, 0.05);
                border-radius: 16px;
                padding: 20px;
            }
        """)
        
        layout = QVBoxLayout(list_frame)
        layout.setSpacing(16)
        
        # List title and actions
        header_layout = QHBoxLayout()
        
        list_title = QLabel("Your Documents")
        list_title.setFont(QFont("Arial", 14, QFont.Weight.Medium))
        list_title.setStyleSheet("color: #2d3748;")
        header_layout.addWidget(list_title)
        
        header_layout.addStretch()
        
        # Delete button
        self.delete_button = QPushButton("[DELETE] Delete")
        self.delete_button.clicked.connect(self.delete_selected_document)
        self.delete_button.setEnabled(False)
        self.delete_button.setStyleSheet("""
            QPushButton {
                background: rgba(239, 68, 68, 0.1);
                border: 1px solid rgba(239, 68, 68, 0.2);
                border-radius: 8px;
                color: #ef4444;
                padding: 6px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.2);
                border: 1px solid rgba(239, 68, 68, 0.3);
            }
            QPushButton:disabled {
                background: rgba(0, 0, 0, 0.05);
                border: 1px solid rgba(0, 0, 0, 0.05);
                color: #a0aec0;
            }
        """)
        header_layout.addWidget(self.delete_button)
        
        layout.addLayout(header_layout)
        
        # Document list widget
        self.document_list = QListWidget()
        self.document_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.document_list.customContextMenuRequested.connect(self.show_context_menu)
        self.document_list.itemSelectionChanged.connect(self.on_selection_changed)
        self.document_list.setStyleSheet("""
            QListWidget {
                background: rgba(255, 255, 255, 0.5);
                border: 1px solid rgba(0, 0, 0, 0.05);
                border-radius: 8px;
                padding: 8px;
            }
            QListWidget::item {
                background: rgba(255, 255, 255, 0.8);
                border: 1px solid rgba(0, 0, 0, 0.05);
                border-radius: 8px;
                margin: 2px;
                padding: 12px 16px;
                font-size: 12px;
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
        layout.addWidget(self.document_list)
        
        # Status
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #718096; font-size: 11px; margin-top: 8px;")
        layout.addWidget(self.status_label)
        
        return list_frame
    
    def setup_signals(self):
        """Setup signal connections"""
        pass
    
    def setup_drag_drop(self):
        """Setup drag and drop functionality"""
        self.setAcceptDrops(True)
        self.drop_zone.setAcceptDrops(True)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter event"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            # Visual feedback
            self.drop_zone.setStyleSheet("""
                QFrame {
                    border: 2px dashed #78dcb4;
                    border-radius: 12px;
                    background: rgba(120, 220, 180, 0.1);
                    min-height: 100px;
                    padding: 20px;
                }
            """)
    
    def dragLeaveEvent(self, event):
        """Handle drag leave event"""
        # Reset drop zone style
        self.drop_zone.setStyleSheet("""
            QFrame {
                border: 2px dashed rgba(120, 220, 180, 0.5);
                border-radius: 12px;
                background: rgba(248, 255, 254, 0.8);
                min-height: 100px;
                padding: 20px;
            }
            QFrame:hover {
                border-color: #78dcb4;
                background: rgba(120, 220, 180, 0.05);
            }
        """)
    
    def dropEvent(self, event: QDropEvent):
        """Handle drop event"""
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        self.upload_files(files)
        
        # Reset drop zone style
        self.dragLeaveEvent(None)
    
    def select_and_upload_files(self):
        """Open file dialog and upload selected files"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Documents to Upload",
            "",
            "Documents (*.pdf *.docx *.txt *.md);;PDF Files (*.pdf);;Word Documents (*.docx);;Text Files (*.txt);;Markdown (*.md);;All Files (*)"
        )
        
        if file_paths:
            self.upload_files(file_paths)
    
    def upload_files(self, file_paths: List[str]):
        """Upload multiple files"""
        if not file_paths:
            return
        
        # Filter valid files
        valid_files = []
        invalid_files = []
        
        for file_path in file_paths:
            if Path(file_path).suffix.lower() in ['.pdf', '.docx', '.txt', '.md']:
                if Path(file_path).exists():
                    valid_files.append(file_path)
                else:
                    invalid_files.append(file_path)
            else:
                invalid_files.append(file_path)
        
        if invalid_files:
            QMessageBox.warning(
                self,
                "Invalid Files",
                f"The following files are not supported or don't exist:\n" +
                "\n".join([Path(f).name for f in invalid_files[:5]]) +
                (f"\n... and {len(invalid_files) - 5} more" if len(invalid_files) > 5 else "")
            )
        
        if not valid_files:
            return
        
        # Start upload
        self.start_upload(valid_files)
    
    def start_upload(self, file_paths: List[str]):
        """Start the upload process"""
        if self.upload_thread and self.upload_thread.isRunning():
            QMessageBox.information(self, "Upload in Progress", "Please wait for the current upload to complete.")
            return
        
        # Determine if we should use legacy endpoint
        use_legacy = not self.is_authenticated or not self.is_online
        
        # Create and start upload thread
        self.upload_thread = UploadThread(self.api_client, file_paths, use_legacy)
        self.upload_thread.upload_progress.connect(self.on_upload_progress)
        self.upload_thread.upload_completed.connect(self.on_upload_completed)
        self.upload_thread.upload_failed.connect(self.on_upload_failed)
        self.upload_thread.finished.connect(self.on_upload_finished)
        
        self.upload_thread.start()
        
        # Update UI
        self.set_upload_state(True)
        self.status_label.setText(f"Uploading {len(file_paths)} file(s)...")
    
    def on_upload_progress(self, filename: str, percentage: int):
        """Handle upload progress"""
        self.progress_bar.setValue(percentage)
        self.status_label.setText(f"📤 Uploading {filename}... {percentage}%")
    
    def on_upload_completed(self, filename: str, result: Dict):
        """Handle upload completion"""
        logger.info(f"Upload completed: {filename}")
        self.document_uploaded.emit(filename)
    
    def on_upload_failed(self, filename: str, error: str):
        """Handle upload failure"""
        logger.error(f"Upload failed: {filename} - {error}")
        QMessageBox.critical(
            self,
            "Upload Failed",
            f"Failed to upload {filename}:\n{error}"
        )
    
    def on_upload_finished(self):
        """Handle upload process completion"""
        self.set_upload_state(False)
        self.status_label.setText("[SUCCESS] Upload completed")
        
        # Refresh document list
        QTimer.singleShot(1000, self.refresh_documents)
    
    def set_upload_state(self, uploading: bool):
        """Set upload state"""
        self.upload_button.setEnabled(not uploading)
        self.progress_bar.setVisible(uploading)
        
        if uploading:
            self.progress_bar.setRange(0, 100)
        else:
            self.progress_bar.setValue(0)
    
    def refresh_documents(self):
        """Refresh the document list"""
        self.status_label.setText("[CLIPBOARD] Loading documents...")
        
        # Determine which endpoint to use
        if self.is_authenticated and self.is_online:
            result = self.api_client.get_documents()
        else:
            result = self.api_client.get_documents_legacy("test_user")
        
        if result["success"]:
            self.documents = result["documents"]
            self.update_document_list()
            self.status_label.setText(f"📊 Loaded {len(self.documents)} document(s)")
        else:
            self.status_label.setText(f"[FAIL] Failed to load documents: {result['error']}")
            logger.error(f"Failed to refresh documents: {result['error']}")
    
    def update_document_list(self):
        """Update the document list widget"""
        self.document_list.clear()
        
        for doc_data in self.documents:
            item = DocumentItem(doc_data)
            self.document_list.addItem(item)
        
        # Update delete button state
        self.on_selection_changed()
    
    def show_context_menu(self, position):
        """Show context menu for document list"""
        item = self.document_list.itemAt(position)
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
                font-size: 12px;
            }
            QMenu::item:selected {
                background: rgba(120, 220, 180, 0.1);
            }
        """)
        
        # Delete action
        delete_action = QAction("[DELETE] Delete Document", self)
        delete_action.triggered.connect(lambda: self.delete_document(item))
        menu.addAction(delete_action)
        
        # View details action
        details_action = QAction("ℹ️ View Details", self)
        details_action.triggered.connect(lambda: self.show_document_details(item))
        menu.addAction(details_action)
        
        menu.exec(self.document_list.mapToGlobal(position))
    
    def on_selection_changed(self):
        """Handle selection change"""
        has_selection = len(self.document_list.selectedItems()) > 0
        self.delete_button.setEnabled(has_selection)
    
    def delete_selected_document(self):
        """Delete the selected document"""
        selected_items = self.document_list.selectedItems()
        if not selected_items:
            return
        
        self.delete_document(selected_items[0])
    
    def delete_document(self, item: DocumentItem):
        """Delete a specific document"""
        document_id = item.data(Qt.ItemDataRole.UserRole)
        filename = item.document_data.get("filename", "Unknown")
        
        if not document_id:
            return
        
        reply = QMessageBox.question(
            self,
            "Delete Document",
            f"Are you sure you want to delete '{filename}'?\n\n"
            "This will remove the document and all its processed chunks from the system.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            result = self.api_client.delete_document(document_id)
            
            if result["success"]:
                self.status_label.setText(f"[DELETE] Deleted {filename}")
                self.document_deleted.emit(filename)
                self.refresh_documents()
            else:
                QMessageBox.critical(
                    self,
                    "Delete Failed",
                    f"Failed to delete {filename}:\n{result['error']}"
                )
    
    def show_document_details(self, item: DocumentItem):
        """Show detailed information about a document"""
        doc_data = item.document_data
        
        details = f"""
        <div style="font-family: Arial; font-size: 12px;">
        <h3 style="color: #2d3748; margin-bottom: 16px;">[DOC] {doc_data.get('filename', 'Unknown')}</h3>
        <table style="width: 100%; border-collapse: collapse;">
        <tr><td style="padding: 4px 8px; font-weight: bold; color: #4a5568;">Type:</td><td style="padding: 4px 8px;">{doc_data.get('file_type', 'Unknown').upper()}</td></tr>
        <tr><td style="padding: 4px 8px; font-weight: bold; color: #4a5568;">Size:</td><td style="padding: 4px 8px;">{item.format_file_size(doc_data.get('file_size', 0))}</td></tr>
        <tr><td style="padding: 4px 8px; font-weight: bold; color: #4a5568;">Status:</td><td style="padding: 4px 8px;">{doc_data.get('processing_status', 'Unknown').title()}</td></tr>
        <tr><td style="padding: 4px 8px; font-weight: bold; color: #4a5568;">Chunks:</td><td style="padding: 4px 8px;">{doc_data.get('chunk_count', 0)}</td></tr>
        <tr><td style="padding: 4px 8px; font-weight: bold; color: #4a5568;">Uploaded:</td><td style="padding: 4px 8px;">{doc_data.get('upload_date', 'Unknown').split('T')[0]}</td></tr>
        <tr><td style="padding: 4px 8px; font-weight: bold; color: #4a5568;">ID:</td><td style="padding: 4px 8px; font-family: monospace; font-size: 10px;">{doc_data.get('id', 'Unknown')}</td></tr>
        </table>
        </div>
        """
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Document Details")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(details)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()
    
    def update_online_status(self, is_online: bool):
        """Update online status"""
        self.is_online = is_online
        
        if is_online:
            self.status_label.setText("[GREEN] Online - Full functionality available")
        else:
            self.status_label.setText("[RED] Offline - Using local storage")
        
        # Refresh documents with appropriate endpoint
        QTimer.singleShot(500, self.refresh_documents)
    
    def update_auth_state(self, is_authenticated: bool, user_info: Dict = None):
        """Update authentication state"""
        self.is_authenticated = is_authenticated
        self.current_user = user_info
        
        if is_authenticated and user_info:
            self.status_label.setText(f"👤 {user_info.get('name', 'User')}'s documents")
        else:
            self.status_label.setText("📂 Local documents")
        
        # Refresh documents with appropriate endpoint
        QTimer.singleShot(500, self.refresh_documents)
    
    def get_document_count(self) -> int:
        """Get total document count"""
        return len(self.documents)
    
    def get_processed_document_count(self) -> int:
        """Get count of successfully processed documents"""
        return len([doc for doc in self.documents if doc.get("processing_status") == "completed"])