"""
Downloads Manager - Chrome-style downloads with progress, history, and controls
"""

import os
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QScrollArea,
    QProgressBar,
    QFileDialog,
    QMenu,
)
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QStandardPaths
from PyQt6.QtWebEngineCore import QWebEngineDownloadRequest


class DownloadItem(QFrame):
    """Single download item with progress and controls"""

    removed = pyqtSignal(object)

    def __init__(self, download, manager):
        super().__init__()
        self.download = download
        self.manager = manager
        self.file_path = ""
        self.is_complete = False
        self.is_cancelled = False

        self.setStyleSheet(
            """
            QFrame {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                margin: 4px 0;
            }
            QToolTip {
                background-color: #1f2937;
                color: white;
                border: none;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
            }
        """
        )
        self.setMinimumHeight(80)
        self.setup_ui()
        self.connect_download()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # File icon
        icon = QLabel("📄")
        icon.setStyleSheet("font-size: 24px; border: none;")
        icon.setFixedWidth(32)
        layout.addWidget(icon)

        # Info section
        info = QWidget()
        info.setStyleSheet("border: none;")
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(4)

        # Filename
        self.filename_label = QLabel("Downloading...")
        self.filename_label.setStyleSheet(
            "font-weight: 500; font-size: 13px; color: #1f2937; border: none;"
        )
        self.filename_label.setMinimumHeight(20)
        self.filename_label.setMaximumWidth(180)
        from PyQt6.QtWidgets import QSizePolicy

        self.filename_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        info_layout.addWidget(self.filename_label)

        # Status/progress
        self.status_label = QLabel("Starting...")
        self.status_label.setStyleSheet(
            "font-size: 12px; color: #6b7280; border: none;"
        )
        self.status_label.setMinimumHeight(18)
        self.status_label.setMaximumWidth(180)
        info_layout.addWidget(self.status_label)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setFixedHeight(6)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(
            """
            QProgressBar {
                background-color: #e5e7eb;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #7c3aed;
                border-radius: 3px;
            }
        """
        )
        info_layout.addWidget(self.progress)

        layout.addWidget(info, 1)

        # Action buttons
        btn_container = QWidget()
        btn_container.setStyleSheet("border: none;")
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(4)

        # Cancel/Remove button
        self.cancel_btn = QPushButton("✕")
        self.cancel_btn.setFixedSize(28, 28)
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setToolTip("Cancel")
        self.cancel_btn.setStyleSheet(
            """
            QPushButton {
                background: #fee2e2;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                color: #dc2626;
            }
            QPushButton:hover { background: #fecaca; }
        """
        )
        self.cancel_btn.clicked.connect(self.cancel_download)
        btn_layout.addWidget(self.cancel_btn)

        # Open button (hidden until complete)
        self.open_btn = QPushButton("📂")
        self.open_btn.setFixedSize(28, 28)
        self.open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_btn.setToolTip("Show in folder")
        self.open_btn.setStyleSheet(
            """
            QPushButton {
                background: #dbeafe;
                border: none;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover { background: #bfdbfe; }
        """
        )
        self.open_btn.clicked.connect(self.show_in_folder)
        self.open_btn.hide()
        btn_layout.addWidget(self.open_btn)

        layout.addWidget(btn_container)

    def connect_download(self):
        """Connect download signals"""
        self.download.receivedBytesChanged.connect(self.update_progress)
        self.download.stateChanged.connect(self.on_state_changed)

        # Get filename
        suggested = self.download.downloadFileName()
        self.filename_label.setText(
            suggested[:40] + "..." if len(suggested) > 40 else suggested
        )

        # Set download path
        downloads_dir = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DownloadLocation
        )
        self.file_path = os.path.join(downloads_dir, suggested)
        self.download.setDownloadDirectory(downloads_dir)
        self.download.setDownloadFileName(suggested)

        # Accept the download
        self.download.accept()

    def update_progress(self):
        """Update progress bar and status"""
        received = self.download.receivedBytes()
        total = self.download.totalBytes()

        if total > 0:
            percent = int((received / total) * 100)
            self.progress.setValue(percent)
            self.status_label.setText(
                f"{self.format_size(received)} / {self.format_size(total)}"
            )
        else:
            self.progress.setMaximum(0)
            self.status_label.setText(f"{self.format_size(received)}")

    def on_state_changed(self, state):
        """Handle download state changes"""
        if state == QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
            self.is_complete = True
            self.progress.setValue(100)
            self.progress.setMaximum(100)  # Set back to normal range
            self.progress.setStyleSheet(
                """
                QProgressBar { background-color: #d1fae5; border: none; border-radius: 3px; }
                QProgressBar::chunk { background-color: #10b981; border-radius: 3px; }
            """
            )
            self.status_label.setText(
                f"Complete • {self.format_size(self.download.receivedBytes())}"
            )
            self.cancel_btn.setText("🗑")
            self.cancel_btn.setToolTip("Remove from list")
            self.cancel_btn.setStyleSheet(
                """
                QPushButton { background: #f3f4f6; border: none; border-radius: 4px; font-size: 12px; color: #6b7280; }
                QPushButton:hover { background: #e5e7eb; }
            """
            )
            self.open_btn.show()
            self.manager.save_history(
                self.file_path,
                self.download.downloadFileName(),
                self.download.receivedBytes(),
            )

        elif state == QWebEngineDownloadRequest.DownloadState.DownloadCancelled:
            self.is_cancelled = True
            self.progress.setMaximum(100)  # Set back to normal range
            self.progress.setStyleSheet(
                """
                QProgressBar { background-color: #fee2e2; border: none; border-radius: 3px; }
                QProgressBar::chunk { background-color: #ef4444; border-radius: 3px; }
            """
            )
            self.status_label.setText("Cancelled")
            self.cancel_btn.setText("🗑")
            self.cancel_btn.setToolTip("Remove from list")

        elif state == QWebEngineDownloadRequest.DownloadState.DownloadInterrupted:
            self.progress.setMaximum(100)  # Set back to normal range
            self.status_label.setText(
                "Failed - " + self.download.interruptReasonString()
            )
            self.progress.setStyleSheet(
                """
                QProgressBar { background-color: #fee2e2; border: none; border-radius: 3px; }
                QProgressBar::chunk { background-color: #ef4444; border-radius: 3px; }
            """
            )

    def cancel_download(self):
        """Cancel or remove download"""
        if self.is_complete or self.is_cancelled:
            self.removed.emit(self)
        else:
            self.download.cancel()

    def show_in_folder(self):
        """Open file location in system file manager"""
        if not os.path.exists(self.file_path):
            self.status_label.setText("File not found")
            return

        if sys.platform == "darwin":
            subprocess.run(["open", "-R", self.file_path])
        elif sys.platform == "win32":
            subprocess.run(["explorer", "/select,", self.file_path])
        else:
            subprocess.run(["xdg-open", os.path.dirname(self.file_path)])

    def format_size(self, bytes):
        """Format bytes to human readable"""
        for unit in ["B", "KB", "MB", "GB"]:
            if bytes < 1024:
                return f"{bytes:.1f} {unit}"
            bytes /= 1024
        return f"{bytes:.1f} TB"


class DownloadsSidebar(QFrame):
    """Sidebar showing all downloads"""

    def __init__(self, browser, manager):
        super().__init__()
        self.browser = browser
        self.manager = manager
        self.download_items = []

        self.setFixedWidth(320)
        self.setStyleSheet(
            """
            QFrame {
                background-color: #fafafa;
                border-left: 1px solid #e5e7eb;
            }
        """
        )
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setStyleSheet(
            """
            QFrame { background-color: #f3f4f6; border-bottom: 1px solid #e5e7eb; }
        """
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 10, 12, 10)

        title = QLabel("Downloads")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        # Open downloads folder
        folder_btn = QPushButton("📁")
        folder_btn.setFixedSize(28, 28)
        folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        folder_btn.setToolTip("Open downloads folder")
        folder_btn.setStyleSheet(
            """
            QPushButton { background: transparent; border: none; font-size: 14px; }
            QPushButton:hover { background: #e5e7eb; border-radius: 4px; }
        """
        )
        folder_btn.clicked.connect(self.open_downloads_folder)
        header_layout.addWidget(folder_btn)

        # Clear all
        clear_btn = QPushButton("🗑")
        clear_btn.setFixedSize(28, 28)
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setToolTip("Clear completed")
        clear_btn.setStyleSheet(
            """
            QPushButton { background: transparent; border: none; font-size: 14px; }
            QPushButton:hover { background: #e5e7eb; border-radius: 4px; }
        """
        )
        clear_btn.clicked.connect(self.clear_completed)
        header_layout.addWidget(clear_btn)

        # Close button
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(
            """
            QPushButton { background: transparent; border: none; font-size: 14px; color: #6b7280; }
            QPushButton:hover { color: #1f2937; }
        """
        )
        close_btn.clicked.connect(self.hide)
        header_layout.addWidget(close_btn)

        layout.addWidget(header)

        # Scroll area for downloads
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")

        self.list_container = QWidget()
        self.list_container.setStyleSheet("background: transparent;")
        self.list_container.setMaximumWidth(304)
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(8, 8, 8, 8)
        self.list_layout.setSpacing(4)
        self.list_layout.addStretch()

        scroll.setWidget(self.list_container)
        layout.addWidget(scroll)

        # Empty state
        self.empty_label = QLabel("No downloads yet")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet(
            "color: #9ca3af; padding: 40px; font-size: 13px;"
        )
        self.list_layout.insertWidget(0, self.empty_label)

    def add_download(self, download):
        """Add a new download to the list"""
        self.empty_label.hide()

        item = DownloadItem(download, self.manager)
        item.removed.connect(self.remove_item)
        self.download_items.append(item)
        self.list_layout.insertWidget(0, item)

    def remove_item(self, item):
        """Remove a download item from list"""
        if item in self.download_items:
            self.download_items.remove(item)
            self.list_layout.removeWidget(item)
            item.deleteLater()

        if not self.download_items:
            self.empty_label.show()

    def clear_completed(self):
        """Remove all completed downloads from list"""
        for item in self.download_items[:]:
            if item.is_complete or item.is_cancelled:
                self.remove_item(item)

    def open_downloads_folder(self):
        """Open system downloads folder"""
        downloads_dir = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DownloadLocation
        )
        if sys.platform == "darwin":
            subprocess.run(["open", downloads_dir])
        elif sys.platform == "win32":
            subprocess.run(["explorer", downloads_dir])
        else:
            subprocess.run(["xdg-open", downloads_dir])


class DownloadsManager:
    """Manages downloads and history"""

    def __init__(self, browser):
        self.browser = browser
        self.preferences = browser.preferences
        self.sidebar = DownloadsSidebar(browser, self)
        self.sidebar.hide()

        # Connect to profile's download handler
        browser.profile.downloadRequested.connect(self.on_download_requested)

    def on_download_requested(self, download):
        """Handle new download request"""
        self.sidebar.add_download(download)
        self.button.start_tracking(download)
        self.browser.show_status(f"⬇️ Downloading: {download.downloadFileName()}", 3000)

    def save_history(self, path, filename, size):
        """Save download to history"""
        history = self.get_history()
        history.append(
            {
                "path": path,
                "filename": filename,
                "size": size,
                "timestamp": datetime.now().isoformat(),
            }
        )
        # Keep last 100 downloads
        history = history[-100:]
        self.preferences.set_module_setting("Downloads", "history", json.dumps(history))

    def get_history(self):
        """Get download history"""
        data = self.preferences.get_module_setting("Downloads", "history", "[]")
        try:
            return json.loads(data)
        except:
            return []

    def toggle_sidebar(self):
        """Toggle downloads sidebar visibility"""
        if self.sidebar.isVisible():
            self.sidebar.hide()
        else:
            self.sidebar.show()


class DownloadButton(QPushButton):
    """Toolbar button with circular progress indicator"""

    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.progress = 0
        self.state = "idle"  # idle, downloading, complete
        self.active_downloads = 0
        self.total_bytes = 0
        self.received_bytes = 0
        self._downloads_tracking = {}

        self.setFixedSize(32, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Downloads")
        self.clicked.connect(manager.toggle_sidebar)

        # Timer for resetting to idle after complete
        self._reset_timer = None

    def start_tracking(self, download):
        """Start tracking a download's progress"""
        download_id = id(download)
        self._downloads_tracking[download_id] = {"received": 0, "total": 0}
        self.active_downloads += 1
        self.state = "downloading"

        download.receivedBytesChanged.connect(lambda: self._on_progress(download))
        download.stateChanged.connect(lambda state: self._on_state(state, download))
        self.update()

    def _on_progress(self, download):
        """Update progress from a download"""
        download_id = id(download)
        if download_id in self._downloads_tracking:
            self._downloads_tracking[download_id]["received"] = download.receivedBytes()
            self._downloads_tracking[download_id]["total"] = download.totalBytes()

        # Calculate total progress across all downloads
        total_received = sum(d["received"] for d in self._downloads_tracking.values())
        total_size = sum(d["total"] for d in self._downloads_tracking.values())

        if total_size > 0:
            self.progress = total_received / total_size
        else:
            self.progress = 0
        self.update()

    def _on_state(self, state, download):
        """Handle download state change"""
        download_id = id(download)

        if state in (
            QWebEngineDownloadRequest.DownloadState.DownloadCompleted,
            QWebEngineDownloadRequest.DownloadState.DownloadCancelled,
            QWebEngineDownloadRequest.DownloadState.DownloadInterrupted,
        ):

            if download_id in self._downloads_tracking:
                del self._downloads_tracking[download_id]
            self.active_downloads = max(0, self.active_downloads - 1)

            if self.active_downloads == 0:
                if state == QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
                    self.state = "complete"
                    self.progress = 1.0
                    # Reset to idle after 3 seconds
                    from PyQt6.QtCore import QTimer

                    if self._reset_timer:
                        self._reset_timer.stop()
                    self._reset_timer = QTimer()
                    self._reset_timer.setSingleShot(True)
                    self._reset_timer.timeout.connect(self._reset_to_idle)
                    self._reset_timer.start(3000)
                else:
                    self._reset_to_idle()
        self.update()

    def _reset_to_idle(self):
        """Reset button to idle state"""
        self.state = "idle"
        self.progress = 0
        self.update()

    def paintEvent(self, event):
        """Custom paint for circular progress"""
        from PyQt6.QtGui import QPainter, QPen, QColor, QFont
        from PyQt6.QtCore import QRectF

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        size = min(self.width(), self.height())
        margin = 3
        rect = QRectF(margin, margin, size - 2 * margin, size - 2 * margin)

        # Background circle (only when downloading or complete)
        if self.state in ("downloading", "complete"):
            bg_pen = QPen(QColor("#e5e7eb"), 2.5)
            painter.setPen(bg_pen)
            painter.drawEllipse(rect)

        # Progress arc
        if self.state == "downloading" and self.progress > 0:
            progress_pen = QPen(QColor("#7c3aed"), 2.5)
            painter.setPen(progress_pen)
            start_angle = 90 * 16  # Start from top
            span_angle = -int(self.progress * 360 * 16)  # Clockwise
            painter.drawArc(rect, start_angle, span_angle)

        # Complete circle
        elif self.state == "complete":
            complete_pen = QPen(QColor("#10b981"), 2.5)
            painter.setPen(complete_pen)
            painter.drawEllipse(rect)

        # Icon
        painter.setPen(QColor("#6b7280") if self.state == "idle" else QColor("#1f2937"))
        font = QFont()
        font.setPixelSize(14)
        painter.setFont(font)

        if self.state == "complete":
            icon = "✓"
            painter.setPen(QColor("#10b981"))
        else:
            icon = "⬇"

        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, icon)

        # Hover effect
        if self.underMouse() and self.state == "idle":
            painter.setBrush(QColor(0, 0, 0, 20))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(self.rect(), 4, 4)


def setup_downloads(browser):
    """Set up downloads manager for the browser"""
    manager = DownloadsManager(browser)
    button = DownloadButton(manager)
    manager.button = button  # Reference for progress tracking
    return button, manager.sidebar
