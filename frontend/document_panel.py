"""
Document Panel for RAG Desktop Application
Handles document upload, management, and display
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
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QAction, QFont

from frontend.api_client import APIClient
from frontend.session_manager import SessionManager

logger = logging.getLogger(__name__)

class DocumentItem(QListWidgetItem):
    """Custom list item for documents"""
    
    def __init__(self, document_data: Dict):
        super().__init__()
        
        self.document_data = document_data
        self.update_display()
    
    def update_display(self):
        """Update the display text"""
        filename = self.document_data.get("filename", "Unknown")
        file_type = self.document_data.get("file_type", "").upper()
        status = self.document_data.get("processing_status", "unknown")
        
        # Status emoji
        status_emoji = {
            "completed": "âœ…",
            "processing": "â³",
            "pending": "â¸ï¸",
            "failed": "âŒ"
        }.get(status, "â“")
        
        self.setText(f"{status_emoji} {filename} ({file_type})")
        
        # Tooltip with details
        file_size = self.document_data.get("file_size", 0)
        chunk_count = self.document_data.get("chunk_count", 0)
        upload_date = self.document_data.get("upload_date", "")
        
        size_str = self.format_file_size(file_size)
        
        tooltip = f"""
        File: {filename}
        Type: {file_type}
        Size: {size_str}
        Status: {status.title()}
        Chunks: {chunk_count}
        Uploaded: {upload_date.split('T')[0] if upload_date else 'Unknown'}
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
                    self.upload_failed.emit(filename, result["error"])
                    
            except Exception as e:
                self.upload_failed.emit(filename, str(e))

class DocumentPanel(QWidget):
    """Document management panel"""
    
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
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("ðŸ“„ Documents")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin: 5px;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Refresh button
        self.refresh_button = QPushButton("ðŸ”„")
        self.refresh_button.setToolTip("Refresh document list")
        self.refresh_button.clicked.connect(self.refresh_documents)
        self.refresh_button.setMaximumWidth(30)
        header_layout.addWidget(self.refresh_button)
        
        layout.addLayout(header_layout)
        
        # Upload area
        upload_group = QGroupBox("Upload Documents")
        upload_layout = QVBoxLayout(upload_group)
        
        # Drop zone
        self.drop_zone = QFrame()
        self.drop_zone.setFrameStyle(QFrame.Shape.StyledPanel)
        self.drop_zone.setStyleSheet("""
            QFrame {
                border: 2px dashed #aaa;
                border-radius: 8px;
                background-color: #f9f9f9;
                min-height: 80px;
            }
        """)
        
        drop_layout = QVBoxLayout(self.drop_zone)
        drop_label = QLabel("ðŸ“ Drag & Drop Documents Here\nor click Upload to browse")
        drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_label.setStyleSheet("color: #666; font-size: 14px;")
        drop_layout.addWidget(drop_label)
        
        upload_layout.addWidget(self.drop_zone)
        
        # Upload buttons
        button_layout = QHBoxLayout()
        
        self.upload_button = QPushButton("ðŸ“¤ Upload Files...")
        self.upload_button.clicked.connect(self.select_and_upload_files)
        button_layout.addWidget(self.upload_button)
        
        button_layout.addStretch()
        
        upload_layout.addLayout(button_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        upload_layout.addWidget(self.progress_bar)
        
        layout.addWidget(upload_group)
        
        # Document list
        list_group = QGroupBox("Your Documents")
        list_layout = QVBoxLayout(list_group)
        
        self.document_list = QListWidget()
        self.document_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.document_list.customContextMenuRequested.connect(self.show_context_menu)
        self.document_list.itemSelectionChanged.connect(self.on_selection_changed)
        list_layout.addWidget(self.document_list)
        
        # Document actions
        actions_layout = QHBoxLayout()
        
        self.delete_button = QPushButton("ðŸ—‘ï¸ Delete")
        self.delete_button.clicked.connect(self.delete_selected_document)
        self.delete_button.setEnabled(False)
        actions_layout.addWidget(self.delete_button)
        
        actions_layout.addStretch()
        
        list_layout.addLayout(actions_layout)
        
        layout.addWidget(list_group)
        
        # Status
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #666; font-size: 12px; margin: 5px;")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
    
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
    
    def dropEvent(self, event: QDropEvent):
        """Handle drop event"""
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        self.upload_files(files)
    
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
        self.status_label.setText(f"Uploading {filename}... {percentage}%")
    
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
        self.status_label.setText("Upload completed")
        
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
        self.status_label.setText("Loading documents...")
        
        # Determine which endpoint to use
        if self.is_authenticated and self.is_online:
            result = self.api_client.get_documents()
        else:
            result = self.api_client.get_documents_legacy("test_user")
        
        if result["success"]:
            self.documents = result["documents"]
            self.update_document_list()
            self.status_label.setText(f"Loaded {len(self.documents)} document(s)")
        else:
            self.status_label.setText(f"Failed to load documents: {result['error']}")
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
        
        # Delete action
        delete_action = QAction("Delete Document", self)
        delete_action.triggered.connect(lambda: self.delete_document(item))
        menu.addAction(delete_action)
        
        # View details action
        details_action = QAction("View Details", self)
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
                self.status_label.setText(f"Deleted {filename}")
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
        <h3>{doc_data.get('filename', 'Unknown')}</h3>
        <table>
        <tr><td><b>Type:</b></td><td>{doc_data.get('file_type', 'Unknown').upper()}</td></tr>
        <tr><td><b>Size:</b></td><td>{item.format_file_size(doc_data.get('file_size', 0))}</td></tr>
        <tr><td><b>Status:</b></td><td>{doc_data.get('processing_status', 'Unknown').title()}</td></tr>
        <tr><td><b>Chunks:</b></td><td>{doc_data.get('chunk_count', 0)}</td></tr>
        <tr><td><b>Uploaded:</b></td><td>{doc_data.get('upload_date', 'Unknown').split('T')[0]}</td></tr>
        <tr><td><b>ID:</b></td><td>{doc_data.get('id', 'Unknown')}</td></tr>
        </table>
        """
        
        QMessageBox.information(self, "Document Details", details)
    
    def update_online_status(self, is_online: bool):
        """Update online status"""
        self.is_online = is_online
        
        if is_online:
            self.status_label.setText("ðŸŸ¢ Online - Full functionality available")
        else:
            self.status_label.setText("ðŸ”´ Offline - Using local storage")
        
        # Refresh documents with appropriate endpoint
        QTimer.singleShot(500, self.refresh_documents)
    
    def update_auth_state(self, is_authenticated: bool, user_info: Dict = None):
        """Update authentication state"""
        self.is_authenticated = is_authenticated
        self.current_user = user_info
        
        if is_authenticated and user_info:
            self.status_label.setText(f"ðŸ‘¤ {user_info.get('name', 'User')}'s documents")
        else:
            self.status_label.setText("ðŸ”“ Local documents (not authenticated)")
        
        # Refresh documents with appropriate endpoint
        QTimer.singleShot(500, self.refresh_documents)
    
    def get_document_count(self) -> int:
        """Get total document count"""
        return len(self.documents)
    
    def get_processed_document_count(self) -> int:
        """Get count of successfully processed documents"""
        return len([doc for doc in self.documents if doc.get("processing_status") == "completed"])