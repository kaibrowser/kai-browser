from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QToolButton, QMenu, QDialog, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QTextEdit,
                             QTabWidget, QWidget, QTableWidget, QTableWidgetItem,
                             QHeaderView, QFileDialog, QMessageBox)
from PyQt6.QtGui import QAction
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

class AIPerformanceMonitor:
    def __init__(self, browser):
        self.browser = browser
        self.toolbar = browser.toolbar
        
        # Setup logging directory
        self.log_dir = Path.home() / "kaibrowser" / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "ai_generation.log"
        self.stats_file = self.log_dir / "stats.json"
        
        # Initialize stats if needed
        if not self.stats_file.exists():
            self.save_stats({
                'total_requests': 0,
                'successful': 0,
                'failed': 0,
                'total_duration': 0,
                'first_use': datetime.now().isoformat()
            })
    
    def activate(self):
        button = QToolButton()
        button.setText("📊 AI Stats")
        button.clicked.connect(self.show_dashboard)
        self.toolbar.addWidget(button)
    
    def log_generation(self, request_text, success, duration_seconds, error=None, code_length=0, prompt_size=0):
        """Log an AI generation attempt - call this from your AI module"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'request_preview': request_text[:100] if request_text else "Unknown",
            'success': success,
            'duration': round(duration_seconds, 2),
            'prompt_size': prompt_size,
            'code_size': code_length,
            'error_type': type(error).__name__ if error else None,
            'error_message': str(error)[:200] if error else None
        }
        
        # Append to log file
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + '\n')
        
        # Update summary stats
        stats = self.load_stats()
        stats['total_requests'] += 1
        if success:
            stats['successful'] += 1
        else:
            stats['failed'] += 1
        stats['total_duration'] += duration_seconds
        self.save_stats(stats)
    
    def load_stats(self):
        """Load summary statistics"""
        if self.stats_file.exists():
            with open(self.stats_file, encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def save_stats(self, stats):
        """Save summary statistics"""
        with open(self.stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2)
    
    def load_logs(self, limit=None):
        """Load recent log entries"""
        if not self.log_file.exists():
            return []
        
        logs = []
        with open(self.log_file, encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        logs.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        
        # Return most recent first
        logs.reverse()
        if limit:
            return logs[:limit]
        return logs
    
    def show_dashboard(self):
        """Show the analytics dashboard"""
        dialog = QDialog()
        dialog.setWindowTitle("AI Performance Dashboard")
        dialog.setMinimumSize(800, 600)
        
        layout = QVBoxLayout()
        
        # Create tabs
        tabs = QTabWidget()
        
        # Tab 1: Overview
        overview_tab = self.create_overview_tab()
        tabs.addTab(overview_tab, "📈 Overview")
        
        # Tab 2: Recent Logs
        logs_tab = self.create_logs_tab()
        tabs.addTab(logs_tab, "📝 Recent Logs")
        
        # Tab 3: Error Analysis
        errors_tab = self.create_errors_tab()
        tabs.addTab(errors_tab, "⚠️ Errors")
        
        layout.addWidget(tabs)
        
        # Bottom buttons
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
        """Create overview statistics tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        stats = self.load_stats()
        logs = self.load_logs()
        
        # Summary stats
        total = stats.get('total_requests', 0)
        success = stats.get('successful', 0)
        failed = stats.get('failed', 0)
        total_time = stats.get('total_duration', 0)
        
        success_rate = (success / total * 100) if total > 0 else 0
        avg_time = (total_time / total) if total > 0 else 0
        
        # Display stats
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
        stats_label.setStyleSheet("font-family: monospace; padding: 10px; background-color: #f5f5f5;")
        layout.addWidget(stats_label)
        
        # Recent activity
        if logs:
            layout.addWidget(QLabel("\n📌 RECENT ACTIVITY (Last 5)"))
            layout.addWidget(QLabel("─" * 50))
            
            for log in logs[:5]:
                timestamp = datetime.fromisoformat(log['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                status = "✅" if log['success'] else "❌"
                request = log['request_preview']
                duration = log['duration']
                
                entry_text = f"{status} {timestamp} - {request} ({duration}s)"
                entry_label = QLabel(entry_text)
                entry_label.setStyleSheet("padding: 5px;")
                layout.addWidget(entry_label)
        else:
            layout.addWidget(QLabel("\n📭 No AI generations logged yet."))
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_logs_tab(self):
        """Create detailed logs tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Recent AI Generation Logs (Latest 50)"))
        
        # Create table
        table = QTableWidget()
        logs = self.load_logs(limit=50)
        
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(['Time', 'Status', 'Request', 'Duration', 'Code Size', 'Error'])
        table.setRowCount(len(logs))
        
        for i, log in enumerate(logs):
            timestamp = datetime.fromisoformat(log['timestamp']).strftime('%H:%M:%S')
            table.setItem(i, 0, QTableWidgetItem(timestamp))
            
            status = "✅ Success" if log['success'] else "❌ Failed"
            table.setItem(i, 1, QTableWidgetItem(status))
            
            table.setItem(i, 2, QTableWidgetItem(log['request_preview']))
            table.setItem(i, 3, QTableWidgetItem(f"{log['duration']}s"))
            table.setItem(i, 4, QTableWidgetItem(str(log.get('code_size', 0))))
            
            error = log.get('error_type', '') or ''
            table.setItem(i, 5, QTableWidgetItem(error))
        
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        
        layout.addWidget(table)
        widget.setLayout(layout)
        return widget
    
    def create_errors_tab(self):
        """Create error analysis tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Error Analysis"))
        layout.addWidget(QLabel("─" * 50))
        
        logs = self.load_logs()
        failed_logs = [log for log in logs if not log['success']]
        
        if not failed_logs:
            layout.addWidget(QLabel("🎉 No errors recorded!"))
            layout.addStretch()
            widget.setLayout(layout)
            return widget
        
        # Count error types
        error_counts = defaultdict(int)
        error_examples = {}
        
        for log in failed_logs:
            error_type = log.get('error_type') or 'Unknown'
            error_counts[error_type] += 1
            if error_type not in error_examples:
                error_examples[error_type] = log.get('error_message', 'No details')
        
        # Display error summary
        summary_text = f"Total Errors: {len(failed_logs)}\n\n"
        for error_type, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True):
            summary_text += f"• {error_type}: {count} occurrences\n"
        
        summary_label = QLabel(summary_text)
        summary_label.setStyleSheet("font-family: monospace; padding: 10px; background-color: #fff3cd;")
        layout.addWidget(summary_label)
        
        # Show example errors
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
        """Export logs to a file"""
        file_path, _ = QFileDialog.getSaveFileName(
            None,
            "Export Logs",
            str(Path.home() / "ai_generation_logs.json"),
            "JSON Files (*.json)"
        )
        
        if file_path:
            logs = self.load_logs()
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'stats': self.load_stats(),
                    'logs': logs
                }, f, indent=2)
            
            QMessageBox.information(None, "Exported", f"Logs exported to:\n{file_path}")
    
    def clear_logs(self, dialog):
        """Clear all logs after confirmation"""
        reply = QMessageBox.question(
            None,
            "Clear Logs",
            "Are you sure you want to clear all logs and statistics?\n\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Clear log file
            if self.log_file.exists():
                self.log_file.unlink()
            
            # Reset stats
            self.save_stats({
                'total_requests': 0,
                'successful': 0,
                'failed': 0,
                'total_duration': 0,
                'first_use': datetime.now().isoformat()
            })
            
            QMessageBox.information(None, "Cleared", "All logs and statistics have been cleared.")
            
            # Refresh dashboard
            dialog.close()
            self.show_dashboard()