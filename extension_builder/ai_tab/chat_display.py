"""
Chat Display Manager
Handles conversation history rendering and message bubbles
"""

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt


class ChatDisplayManager:
    """Manages chat message display and conversation history"""

    def __init__(self, chat_container):
        """
        Args:
            chat_container: QVBoxLayout where messages are added
        """
        self.chat_container = chat_container

    def add_user_message(self, text):
        """Add user message bubble"""
        msg_frame = QFrame()
        msg_frame.setStyleSheet(
            """
            QFrame {
                background-color: #e7e5e4;
                border-radius: 12px;
                padding: 12px 16px;
                margin-left: 40px;
            }
        """
        )
        msg_layout = QVBoxLayout(msg_frame)
        msg_layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        label.setStyleSheet("color: #111827; font-size: 13px;")
        msg_layout.addWidget(label)

        self.chat_container.addWidget(msg_frame)

    def add_assistant_message(self, text):
        """Add assistant message bubble with gradient background"""
        msg_frame = QFrame()
        msg_frame.setStyleSheet(
            """
            QFrame {
                border-radius: 12px;
                padding: 12px 16px;
                margin-right: 40px;

                background: qlineargradient(
                    x1:0, y1:0,
                    x2:1, y2:1,
                    stop:0 #e0f2fe,
                    stop:1 #ede9fe
                );
            }
        """
        )
        msg_layout = QVBoxLayout(msg_frame)
        msg_layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        label.setStyleSheet("color: #333; font-size: 13px;")
        msg_layout.addWidget(label)

        self.chat_container.addWidget(msg_frame)

    def rebuild_display(self, conversation_history):
        """Rebuild entire chat display from history"""
        # Clear existing messages
        self.clear_display()

        # Rebuild from history (last 10 messages)
        for msg in conversation_history[-10:]:
            if msg["role"] == "user":
                self.add_user_message(msg["message"])
            elif msg["role"] == "assistant":
                self.add_assistant_message(msg.get("status", ""))

    def clear_display(self):
        """Clear all messages from display"""
        while self.chat_container.count():
            item = self.chat_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def get_message_count(self):
        """Get current number of displayed messages"""
        return self.chat_container.count()
