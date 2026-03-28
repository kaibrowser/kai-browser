from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QToolButton,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QTabWidget,
    QWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFileDialog,
    QMessageBox,
    QSplitter,
)
from PyQt6.QtGui import QFont
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict


class AIPerformanceMonitor:
    def __init__(self, browser):
        self.browser = browser
        self.toolbar = browser.toolbar

        self.log_dir = Path.home() / "kaibrowser" / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "ai_generation.log"
        self.stats_file = self.log_dir / "stats.json"

        if not self.stats_file.exists():
            self.save_stats(
                {
                    "total_requests": 0,
                    "successful": 0,
                    "failed": 0,
                    "total_duration": 0,
                    "first_use": datetime.now().isoformat(),
                }
            )

    def activate(self):
        button = QToolButton()
        button.setText("📊 AI Stats")
        button.clicked.connect(self.show_dashboard)
        self.toolbar.addWidget(button)

    def log_generation(
        self,
        request_text,
        success,
        duration_seconds,
        error=None,
        code_length=0,
        prompt_size=0,
        chat_response=None,
        generated_code=None,
        load_error=None,
    ):
        """Log an AI generation attempt including full chat, code, and load errors"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "request_preview": request_text[:100] if request_text else "Unknown",
            "request_full": request_text or "Unknown",
            "success": success,
            "duration": round(duration_seconds, 2),
            "prompt_size": prompt_size,
            "code_size": code_length,
            "error_type": type(error).__name__ if error else None,
            "error_message": str(error)[:200] if error else None,
            "chat_response": chat_response or None,
            "generated_code": generated_code or None,
            "load_error": load_error or None,
        }

        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        stats = self.load_stats()
        stats["total_requests"] += 1
        if success:
            stats["successful"] += 1
        else:
            stats["failed"] += 1
        stats["total_duration"] += duration_seconds
        self.save_stats(stats)

    def log_load_error(self, module_name, error_type, error_message, traceback_text):
        """Log a load time error from the code editor or AI tab"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "request_preview": f"[LOAD ERROR] {module_name}",
            "request_full": f"Load error in {module_name}",
            "success": False,
            "duration": 0,
            "prompt_size": 0,
            "code_size": 0,
            "error_type": error_type,
            "error_message": error_message[:200] if error_message else None,
            "chat_response": None,
            "generated_code": None,
            "load_error": f"{error_type}: {error_message}\n\n{traceback_text}",
        }

        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        stats = self.load_stats()
        stats["total_requests"] += 1
        stats["failed"] += 1
        stats["total_duration"] += 0
        self.save_stats(stats)

    def log_load_error(self, module_name, error_type, error_message, traceback_text):
        """Log a load time error from the code editor or AI tab"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "request_preview": f"[LOAD ERROR] {module_name}",
            "request_full": f"Load error in {module_name}",
            "success": False,
            "duration": 0,
            "prompt_size": 0,
            "code_size": 0,
            "error_type": error_type,
            "error_message": error_message[:200] if error_message else None,
            "chat_response": None,
            "generated_code": None,
            "load_error": f"{error_type}: {error_message}\n\n{traceback_text}",
        }
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        stats = self.load_stats()
        stats["total_requests"] += 1
        stats["failed"] += 1
        stats["total_duration"] += 0
        self.save_stats(stats)

    def load_stats(self):
        if self.stats_file.exists():
            with open(self.stats_file, encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_stats(self, stats):
        with open(self.stats_file, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)

    def load_logs(self, limit=None):
        if not self.log_file.exists():
            return []
        logs = []
        with open(self.log_file, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        logs.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        logs.reverse()
        if limit:
            return logs[:limit]
        return logs

    def show_dashboard(self):
        dialog = QDialog()
        dialog.setWindowTitle("AI Performance Dashboard")
        dialog.setMinimumSize(900, 650)

        layout = QVBoxLayout()
        tabs = QTabWidget()

        tabs.addTab(self.create_overview_tab(), "📈 Overview")
        tabs.addTab(self.create_logs_tab(), "📝 Recent Logs")
        tabs.addTab(self.create_errors_tab(), "⚠️ Errors")

        layout.addWidget(tabs)

        btn_layout = QHBoxLayout()

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(lambda: (dialog.close(), self.show_dashboard()))
        btn_layout.addWidget(refresh_btn)

        export_btn = QPushButton("💾 Export Logs")
        export_btn.clicked.connect(self.export_logs)
        btn_layout.addWidget(export_btn)

        clear_btn = QPushButton("🗑️ Clear Logs")
        clear_btn.clicked.connect(lambda: self.clear_logs(dialog))
        btn_layout.addWidget(clear_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)
        dialog.setLayout(layout)
        dialog.exec()

    def create_overview_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        stats = self.load_stats()
        logs = self.load_logs()

        total = stats.get("total_requests", 0)
        success = stats.get("successful", 0)
        failed = stats.get("failed", 0)
        total_time = stats.get("total_duration", 0)
        success_rate = (success / total * 100) if total > 0 else 0
        avg_time = (total_time / total) if total > 0 else 0

        stats_text = f"""
📊 OVERALL STATISTICS
{'─' * 50}

Total Requests: {total}
✅ Successful: {success} ({success_rate:.1f}%)
❌ Failed: {failed} ({100 - success_rate:.1f}%)

⏱️ Average Generation Time: {avg_time:.2f}s
⏱️ Total Time Spent: {total_time:.1f}s

📅 First Use: {stats.get('first_use', 'Unknown')}
"""
        stats_label = QLabel(stats_text)
        stats_label.setStyleSheet(
            "font-family: monospace; padding: 10px; background-color: #f5f5f5;"
        )
        layout.addWidget(stats_label)

        if logs:
            layout.addWidget(QLabel("\n📌 RECENT ACTIVITY (Last 5)"))
            layout.addWidget(QLabel("─" * 50))
            for log in logs[:5]:
                ts = datetime.fromisoformat(log["timestamp"]).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                status = "✅" if log["success"] else "❌"
                load_err = " ⚠️ load error" if log.get("load_error") else ""
                entry_label = QLabel(
                    f"{status} {ts} - {log['request_preview']} ({log['duration']}s){load_err}"
                )
                entry_label.setStyleSheet("padding: 5px;")
                layout.addWidget(entry_label)
        else:
            layout.addWidget(QLabel("\n📭 No AI generations logged yet."))

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def create_logs_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        hint = QLabel(
            "Recent AI Generation Logs (Latest 50) — click a row to view full detail"
        )
        hint.setStyleSheet("font-size: 11px; color: #666; padding-bottom: 4px;")
        layout.addWidget(hint)

        logs = self.load_logs(limit=50)

        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(
            ["Time", "Status", "Request", "Duration", "Code Size", "Load Error"]
        )
        table.setRowCount(len(logs))
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        for i, log in enumerate(logs):
            ts = datetime.fromisoformat(log["timestamp"]).strftime("%H:%M:%S")
            table.setItem(i, 0, QTableWidgetItem(ts))

            status = "✅ Success" if log["success"] else "❌ Failed"
            table.setItem(i, 1, QTableWidgetItem(status))
            table.setItem(i, 2, QTableWidgetItem(log["request_preview"]))
            table.setItem(i, 3, QTableWidgetItem(f"{log['duration']}s"))
            table.setItem(i, 4, QTableWidgetItem(str(log.get("code_size", 0))))

            load_err = "⚠️ Yes" if log.get("load_error") else ""
            table.setItem(i, 5, QTableWidgetItem(load_err))

        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        table.cellDoubleClicked.connect(lambda row, _: self.show_log_detail(logs[row]))

        layout.addWidget(table)
        widget.setLayout(layout)
        return widget

    def show_log_detail(self, log):
        """Show full detail dialog for a log entry"""
        dialog = QDialog()
        dialog.setWindowTitle(f"Log Detail — {log['request_preview'][:60]}")
        dialog.setMinimumSize(750, 600)

        layout = QVBoxLayout()

        # Header info
        ts = datetime.fromisoformat(log["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
        status = "✅ Success" if log["success"] else "❌ Failed"
        load_err_flag = "  ⚠️ Load error recorded" if log.get("load_error") else ""
        header = QLabel(f"{status}  |  {ts}  |  {log['duration']}s{load_err_flag}")
        header.setStyleSheet("font-size: 12px; font-weight: bold; padding: 6px;")
        layout.addWidget(header)

        tabs = QTabWidget()

        # Request tab
        req_widget = QWidget()
        req_layout = QVBoxLayout(req_widget)
        req_text = QTextEdit()
        req_text.setReadOnly(True)
        req_text.setPlainText(log.get("request_full") or log.get("request_preview", ""))
        req_layout.addWidget(req_text)
        tabs.addTab(req_widget, "📝 Request")

        # Chat response tab
        chat_widget = QWidget()
        chat_layout = QVBoxLayout(chat_widget)
        chat_text = QTextEdit()
        chat_text.setReadOnly(True)
        chat_text.setPlainText(log.get("chat_response") or "No chat response recorded")
        chat_layout.addWidget(chat_text)
        tabs.addTab(chat_widget, "💬 Chat Response")

        # Generated code tab
        code_widget = QWidget()
        code_layout = QVBoxLayout(code_widget)
        code_text = QTextEdit()
        code_text.setReadOnly(True)
        code_text.setFont(QFont("Monospace", 10))
        code_text.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;")
        code_text.setPlainText(log.get("generated_code") or "No code recorded")
        code_layout.addWidget(code_text)
        tabs.addTab(code_widget, "🧩 Generated Code")

        # Errors tab
        err_widget = QWidget()
        err_layout = QVBoxLayout(err_widget)
        err_text = QTextEdit()
        err_text.setReadOnly(True)
        parts = []
        if log.get("error_type"):
            parts.append(
                f"AI Error:\n{log['error_type']}: {log.get('error_message','')}"
            )
        if log.get("load_error"):
            parts.append(f"Load Error:\n{log['load_error']}")
        err_text.setPlainText("\n\n".join(parts) if parts else "No errors recorded")
        err_layout.addWidget(err_text)
        tabs.addTab(err_widget, "⚠️ Errors")

        layout.addWidget(tabs)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)

        dialog.setLayout(layout)
        dialog.exec()

    def create_errors_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Error Analysis"))
        layout.addWidget(QLabel("─" * 50))

        logs = self.load_logs()
        failed_logs = [
            log for log in logs if not log["success"] or log.get("load_error")
        ]

        if not failed_logs:
            layout.addWidget(QLabel("🎉 No errors recorded!"))
            layout.addStretch()
            widget.setLayout(layout)
            return widget

        error_counts = defaultdict(int)
        error_examples = {}
        load_error_count = 0

        for log in failed_logs:
            if log.get("load_error"):
                load_error_count += 1
            error_type = log.get("error_type") or "Unknown"
            error_counts[error_type] += 1
            if error_type not in error_examples:
                error_examples[error_type] = log.get("error_message", "No details")

        summary_text = f"Total Failed: {len(failed_logs)}\n"
        if load_error_count:
            summary_text += f"Load Errors: {load_error_count}\n"
        summary_text += "\n"
        for error_type, count in sorted(
            error_counts.items(), key=lambda x: x[1], reverse=True
        ):
            summary_text += f"• {error_type}: {count} occurrences\n"

        summary_label = QLabel(summary_text)
        summary_label.setStyleSheet(
            "font-family: monospace; padding: 10px; background-color: #fff3cd;"
        )
        layout.addWidget(summary_label)

        layout.addWidget(QLabel("\n📋 Example Error Messages:"))
        error_text = QTextEdit()
        error_text.setReadOnly(True)
        examples = ""
        for error_type, message in error_examples.items():
            examples += f"\n{'═' * 60}\n{error_type}\n{'─' * 60}\n{message}\n"
        error_text.setPlainText(examples)
        layout.addWidget(error_text)

        widget.setLayout(layout)
        return widget

    def export_logs(self):
        file_path, _ = QFileDialog.getSaveFileName(
            None,
            "Export Logs",
            str(Path.home() / "ai_generation_logs.json"),
            "JSON Files (*.json)",
        )
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(
                    {"stats": self.load_stats(), "logs": self.load_logs()}, f, indent=2
                )
            QMessageBox.information(None, "Exported", f"Logs exported to:\n{file_path}")

    def clear_logs(self, dialog):
        reply = QMessageBox.question(
            None,
            "Clear Logs",
            "Are you sure you want to clear all logs and statistics?\n\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self.log_file.exists():
                self.log_file.unlink()
            self.save_stats(
                {
                    "total_requests": 0,
                    "successful": 0,
                    "failed": 0,
                    "total_duration": 0,
                    "first_use": datetime.now().isoformat(),
                }
            )
            QMessageBox.information(
                None, "Cleared", "All logs and statistics have been cleared."
            )
            dialog.close()
            self.show_dashboard()
