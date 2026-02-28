"""
Token Usage Display Widget
Shows real-time token statistics during AI generation
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QFont


class TokenStatsWidget(QWidget):
    """
    Compact token statistics display widget
    Shows: Total tokens | Tokens/sec | Time elapsed | Input/Output split
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.reset()

    def _setup_ui(self):
        """Setup the widget UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(12)

        # Icon
        self.icon_label = QLabel("⚡")
        self.icon_label.setStyleSheet("font-size: 14px;")
        layout.addWidget(self.icon_label)

        # Total tokens
        self.total_label = QLabel("0 tokens")
        self.total_label.setStyleSheet("color: #a78bfa; font-weight: bold;")
        layout.addWidget(self.total_label)

        # Separator
        sep1 = QLabel("|")
        sep1.setStyleSheet("color: #555;")
        layout.addWidget(sep1)

        # Tokens per second
        self.rate_label = QLabel("0 tok/s")
        self.rate_label.setStyleSheet("color: #34d399;")
        layout.addWidget(self.rate_label)

        # Separator
        sep2 = QLabel("|")
        sep2.setStyleSheet("color: #555;")
        layout.addWidget(sep2)

        # Time elapsed
        self.time_label = QLabel("0s")
        self.time_label.setStyleSheet("color: #60a5fa;")
        layout.addWidget(self.time_label)

        # Separator
        sep3 = QLabel("|")
        sep3.setStyleSheet("color: #555;")
        layout.addWidget(sep3)

        # Input/Output split
        self.split_label = QLabel("In: 0 / Out: 0")
        self.split_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.split_label)

        layout.addStretch()

        # Set font
        font = QFont("Consolas", 11)
        for widget in [
            self.total_label,
            self.rate_label,
            self.time_label,
            self.split_label,
        ]:
            widget.setFont(font)

        # Overall styling
        self.setStyleSheet(
            """
            QWidget {
                background: #1a1a2e;
                border: 1px solid #334155;
                border-radius: 6px;
            }
        """
        )

    @pyqtSlot(dict)
    def update_stats(self, stats):
        """
        Update token statistics display

        Args:
            stats: dict with keys:
                - total_tokens: int
                - input_tokens: int (optional)
                - output_tokens: int (optional)
                - tokens_per_sec: float
                - elapsed_time: float
                - is_streaming: bool
        """
        total = stats.get("total_tokens", 0)
        input_tok = stats.get("input_tokens", 0)
        output_tok = stats.get("output_tokens", 0)
        rate = stats.get("tokens_per_sec", 0)
        elapsed = stats.get("elapsed_time", 0)
        is_streaming = stats.get("is_streaming", False)

        # Update total tokens
        self.total_label.setText(f"{total:,} tokens")

        # Update rate with color coding
        if is_streaming:
            if rate > 50:
                color = "#34d399"  # Green - fast
            elif rate > 20:
                color = "#fbbf24"  # Yellow - medium
            else:
                color = "#f87171"  # Red - slow
            self.rate_label.setStyleSheet(f"color: {color}; font-weight: bold;")
            self.rate_label.setText(f"{rate:.0f} tok/s")
        else:
            self.rate_label.setStyleSheet("color: #888;")
            self.rate_label.setText("—")

        # Update time
        if elapsed < 60:
            time_str = f"{elapsed:.0f}s"
        else:
            mins = int(elapsed / 60)
            secs = int(elapsed % 60)
            time_str = f"{mins}m {secs}s"
        self.time_label.setText(time_str)

        # Update input/output split
        if input_tok > 0 or output_tok > 0:
            self.split_label.setText(f"In: {input_tok:,} / Out: {output_tok:,}")
        else:
            self.split_label.setText("—")

        # Update icon based on state
        if is_streaming:
            self.icon_label.setText("⚡")
        else:
            self.icon_label.setText("✓")

    def reset(self):
        """Reset the display to initial state"""
        self.total_label.setText("0 tokens")
        self.rate_label.setText("0 tok/s")
        self.rate_label.setStyleSheet("color: #888;")
        self.time_label.setText("0s")
        self.split_label.setText("—")
        self.icon_label.setText("⚡")

    def set_error_state(self):
        """Show error state"""
        self.icon_label.setText("⚠️")
        self.rate_label.setText("Error")
        self.rate_label.setStyleSheet("color: #f87171;")


# Example usage in your AI builder UI:
"""
# In your main window/dialog:

def __init__(self):
    # ... other init code ...
    
    # Add token stats widget
    self.token_widget = TokenStatsWidget()
    layout.addWidget(self.token_widget)
    
    # Connect to streaming thread
    self.streaming_thread.token_stats.connect(self.token_widget.update_stats)
    
def start_generation(self):
    # Reset display before starting
    self.token_widget.reset()
    
    # Start streaming...
    self.streaming_thread.start()

def on_error(self):
    self.token_widget.set_error_state()
"""


class CompactTokenStats(QWidget):
    """
    Ultra-compact version - single line
    Shows: ⚡ 2,847 tokens @ 142 tok/s (20s)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)

        self.label = QLabel("⚡ 0 tokens")
        self.label.setFont(QFont("Consolas", 10))
        self.label.setStyleSheet("color: #a78bfa;")
        layout.addWidget(self.label)

        self.setStyleSheet(
            """
            QWidget {
                background: #16213e;
                border-radius: 4px;
            }
        """
        )

    @pyqtSlot(dict)
    def update_stats(self, stats):
        total = stats.get("total_tokens", 0)
        rate = stats.get("tokens_per_sec", 0)
        elapsed = stats.get("elapsed_time", 0)
        is_streaming = stats.get("is_streaming", False)

        if is_streaming and rate > 0:
            text = f"⚡ {total:,} tokens @ {rate:.0f} tok/s ({elapsed:.0f}s)"
        else:
            text = f"✓ {total:,} tokens ({elapsed:.0f}s)"

        self.label.setText(text)

    def reset(self):
        self.label.setText("⚡ 0 tokens")
