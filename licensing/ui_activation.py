import os
import sqlite3
import hashlib
from datetime import datetime

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QMessageBox, QWidget, QTableWidget, QTableWidgetItem, QHeaderView, 
    QApplication, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QClipboard

from licensing import manager
from licensing import crypto_utils

# Sha256 hashes of vendor credentials:
# Username: vendor
# Password: admin@mobileshop2026
VENDOR_USER_HASH = "630ba09448af522154f38ef7685ef1f44b0f3e9430f80829a03ce24f400f3754"
VENDOR_PASS_HASH = "eb81458ed6233107869846cba983748999d33ed7bbaa275d376dd1e87a485d66"

def init_history_db():
    db_path = os.path.join(manager.get_storage_dir(), "vendor_history.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            machine_id TEXT NOT NULL,
            activation_key TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def add_history_entry(machine_id: str, activation_key: str):
    init_history_db()
    db_path = os.path.join(manager.get_storage_dir(), "vendor_history.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO history (machine_id, activation_key) VALUES (?, ?)", (machine_id, activation_key))
    conn.commit()
    conn.close()

def get_history_entries() -> list[tuple[str, str, str]]:
    init_history_db()
    db_path = os.path.join(manager.get_storage_dir(), "vendor_history.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, machine_id, activation_key FROM history ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows


class BaseLicensedDialog(QDialog):
    """Base dialog implementing hidden vendor access via Ctrl+Shift+V or double click."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

    def keyPressEvent(self, event):
        # Trigger vendor login on Ctrl+Shift+V
        if (event.modifiers() & Qt.ControlModifier) and (event.modifiers() & Qt.ShiftModifier) and event.key() == Qt.Key_V:
            self.open_vendor_login()
            event.accept()
        else:
            super().keyPressEvent(event)

    def mouseDoubleClickEvent(self, event):
        # Trigger vendor login on double clicking any empty space on dialog
        self.open_vendor_login()
        event.accept()

    def open_vendor_login(self):
        login_dlg = VendorLoginDialog(self)
        if login_dlg.exec() == QDialog.Accepted:
            gen_dlg = VendorGeneratorDialog(self)
            gen_dlg.exec()
            # If the user successfully activated while inside vendor portal, close this dialog as well
            status = manager.check_license_status()
            if status["status"] == "active":
                self.accept()


class TrialStatusDialog(BaseLicensedDialog):
    """Dialog displayed during active 30 days trial period on app startup."""
    def __init__(self, days_remaining: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mobile Shop Management - Free Trial")
        self.setFixedSize(450, 320)
        self.days_remaining = days_remaining
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        title = QLabel("FREE TRIAL ACTIVE")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #6366f1; letter-spacing: 1px;")
        layout.addWidget(title)

        # Radial / Display box for remaining days
        days_box = QFrame()
        days_box.setFrameShape(QFrame.StyledPanel)
        days_box.setStyleSheet("background-color: #1b1b32; border: 1px solid #28284e; border-radius: 8px;")
        box_layout = QVBoxLayout(days_box)
        box_layout.setContentsMargins(15, 15, 15, 15)

        lbl_num = QLabel(str(self.days_remaining))
        lbl_num.setAlignment(Qt.AlignCenter)
        lbl_color = "#10b981" if self.days_remaining > 7 else "#f59e0b"
        lbl_num.setStyleSheet(f"font-size: 48px; font-weight: bold; color: {lbl_color};")
        box_layout.addWidget(lbl_num)

        lbl_text = QLabel("Days Remaining")
        lbl_text.setAlignment(Qt.AlignCenter)
        lbl_text.setStyleSheet("font-size: 13px; color: #94a3b8; font-weight: bold;")
        box_layout.addWidget(lbl_text)

        layout.addWidget(days_box)

        info_lbl = QLabel("You can use all software features during the 30-day trial.\nDouble click here to enter Vendor Activation.")
        info_lbl.setAlignment(Qt.AlignCenter)
        info_lbl.setStyleSheet("font-size: 11px; color: #64748b;")
        layout.addWidget(info_lbl)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_activate = QPushButton("Activate License")
        self.btn_activate.setFixedHeight(40)
        self.btn_activate.clicked.connect(self.handle_activation_flow)
        btn_layout.addWidget(self.btn_activate)

        self.btn_continue = QPushButton("Continue Trial")
        self.btn_continue.setFixedHeight(40)
        self.btn_continue.setProperty("class", "btn-secondary")
        self.btn_continue.setStyleSheet("background-color: #334155; color: #ffffff;")
        self.btn_continue.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_continue)

        layout.addLayout(btn_layout)

    def handle_activation_flow(self):
        act_dlg = ActivationDialog(self)
        if act_dlg.exec() == QDialog.Accepted:
            self.accept()


class ActivationDialog(BaseLicensedDialog):
    """Dialog displayed when license is expired or tampered, blocking standard app access."""
    def __init__(self, parent=None, is_blocked=False, block_msg=""):
        super().__init__(parent)
        self.setWindowTitle("License Activation Required")
        self.setFixedSize(500, 360)
        self.is_blocked = is_blocked
        self.block_msg = block_msg
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 35, 30, 35)
        layout.setSpacing(15)

        title = QLabel("ACTIVATION REQUIRED")
        title.setAlignment(Qt.AlignCenter)
        color = "#ef4444" if self.is_blocked else "#6366f1"
        title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {color}; letter-spacing: 1px;")
        layout.addWidget(title)

        desc = QLabel(self.block_msg if self.is_blocked else "Your trial has expired. Please enter an activation key to continue using the application.")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet("font-size: 13px; color: #e2e8f0;")
        layout.addWidget(desc)

        # Machine ID Box
        mid_layout = QHBoxLayout()
        mid_label = QLabel("Machine ID:")
        mid_label.setStyleSheet("font-weight: bold; color: #94a3b8;")
        
        self.mid_edit = QLineEdit(manager.generate_machine_id())
        self.mid_edit.setReadOnly(True)
        self.mid_edit.setFixedHeight(35)
        self.mid_edit.setStyleSheet("background-color: #141426; border: 1px solid #2c2c54; padding: 5px; font-family: monospace; font-size: 14px; color: #38bdf8;")
        
        btn_copy = QPushButton("Copy")
        btn_copy.setFixedWidth(60)
        btn_copy.setFixedHeight(35)
        btn_copy.setStyleSheet("background-color: #334155; font-size: 11px;")
        btn_copy.clicked.connect(self.copy_machine_id)
        
        mid_layout.addWidget(mid_label)
        mid_layout.addWidget(self.mid_edit)
        mid_layout.addWidget(btn_copy)
        layout.addLayout(mid_layout)

        # License Key Box
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("Enter Activation Key")
        self.key_edit.setFixedHeight(40)
        layout.addWidget(self.key_edit)

        # Error / Status message
        self.status_lbl = QLabel("")
        self.status_lbl.setAlignment(Qt.AlignCenter)
        self.status_lbl.setStyleSheet("color: #ef4444; font-size: 12px; font-weight: bold;")
        layout.addWidget(self.status_lbl)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        btn_activate = QPushButton("Activate Now")
        btn_activate.setFixedHeight(42)
        btn_activate.clicked.connect(self.handle_activation)
        btn_layout.addWidget(btn_activate)

        btn_cancel = QPushButton("Exit Application")
        btn_cancel.setFixedHeight(42)
        btn_cancel.setStyleSheet("background-color: #ef4444; color: #ffffff;")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        layout.addLayout(btn_layout)

    def copy_machine_id(self):
        QApplication.clipboard().setText(self.mid_edit.text())
        QMessageBox.information(self, "Success", "Machine ID copied to clipboard.")

    def handle_activation(self):
        key = self.key_edit.text().strip()
        if not key:
            self.status_lbl.setText("Please enter the activation key.")
            return

        if manager.activate_software(key):
            QMessageBox.information(self, "Activated", "Thank you! The application has been successfully activated.")
            self.accept()
        else:
            self.status_lbl.setText("Invalid activation key. Please double check.")


class VendorLoginDialog(QDialog):
    """Vendor credentials dialog."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Vendor Security Login")
        self.setFixedSize(380, 240)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(12)

        title = QLabel("VENDOR ACTIVATION LOGIN")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #f59e0b;")
        layout.addWidget(title)

        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Vendor Username")
        self.user_input.setFixedHeight(35)
        layout.addWidget(self.user_input)

        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Vendor Password")
        self.pass_input.setEchoMode(QLineEdit.Password)
        self.pass_input.setFixedHeight(35)
        layout.addWidget(self.pass_input)

        self.err_lbl = QLabel("")
        self.err_lbl.setAlignment(Qt.AlignCenter)
        self.err_lbl.setStyleSheet("color: #ef4444; font-size: 11px;")
        layout.addWidget(self.err_lbl)

        btn_layout = QHBoxLayout()
        btn_login = QPushButton("Log In")
        btn_login.setFixedHeight(36)
        btn_login.clicked.connect(self.handle_login)
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setFixedHeight(36)
        btn_cancel.setStyleSheet("background-color: #334155;")
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(btn_login)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

        self.user_input.returnPressed.connect(self.handle_login)
        self.pass_input.returnPressed.connect(self.handle_login)

    def handle_login(self):
        user = self.user_input.text().strip()
        pwd = self.pass_input.text()

        u_hash = hashlib.sha256(user.encode('utf-8')).hexdigest()
        p_hash = hashlib.sha256(pwd.encode('utf-8')).hexdigest()

        if u_hash == VENDOR_USER_HASH and p_hash == VENDOR_PASS_HASH:
            self.accept()
        else:
            self.err_lbl.setText("Incorrect vendor credentials.")


class VendorGeneratorDialog(QDialog):
    """Embedded vendor dashboard to generate activation keys and view activation history."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Vendor License Generator")
        self.setFixedSize(650, 480)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)

        title = QLabel("VENDOR ACTIVATION MANAGEMENT")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #f59e0b; letter-spacing: 1px;")
        layout.addWidget(title)

        # Section 1: Generate Key
        gen_frame = QFrame()
        gen_frame.setStyleSheet("background-color: #1b1b32; border: 1px solid #28284e; border-radius: 8px;")
        gen_layout = QVBoxLayout(gen_frame)
        gen_layout.setContentsMargins(15, 15, 15, 15)
        gen_layout.setSpacing(10)

        sec_lbl = QLabel("Generate Activation Key")
        sec_lbl.setStyleSheet("font-weight: bold; color: #ffffff; font-size: 12px;")
        gen_layout.addWidget(sec_lbl)

        h_layout = QHBoxLayout()
        self.mid_input = QLineEdit()
        self.mid_input.setPlaceholderText("Enter Machine ID (XXXX-XXXX-XXXX-XXXX)")
        self.mid_input.setFixedHeight(35)
        self.mid_input.setStyleSheet("font-family: monospace; font-size: 13px;")
        
        btn_gen = QPushButton("Generate Key")
        btn_gen.setFixedWidth(120)
        btn_gen.setFixedHeight(35)
        btn_gen.setStyleSheet("background-color: #f59e0b;")
        btn_gen.clicked.connect(self.generate_key)
        
        h_layout.addWidget(self.mid_input)
        h_layout.addWidget(btn_gen)
        gen_layout.addLayout(h_layout)

        key_layout = QHBoxLayout()
        self.key_output = QLineEdit()
        self.key_output.setPlaceholderText("Generated Activation Key")
        self.key_output.setReadOnly(True)
        self.key_output.setFixedHeight(35)
        self.key_output.setStyleSheet("font-family: monospace; font-size: 12px; color: #10b981; background-color: #141426;")
        
        btn_copy = QPushButton("Copy Key")
        btn_copy.setFixedWidth(100)
        btn_copy.setFixedHeight(35)
        btn_copy.setStyleSheet("background-color: #334155;")
        btn_copy.clicked.connect(self.copy_key)

        key_layout.addWidget(self.key_output)
        key_layout.addWidget(btn_copy)
        gen_layout.addLayout(key_layout)

        layout.addWidget(gen_frame)

        # Section 2: Activation History Table
        hist_lbl = QLabel("Activation Key History")
        hist_lbl.setStyleSheet("font-weight: bold; color: #94a3b8; font-size: 12px;")
        layout.addWidget(hist_lbl)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Timestamp", "Machine ID", "Activation Key"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet("QTableWidget { background-color: #1b1b32; border: 1px solid #28284e; } QHeaderView::section { background-color: #141426; }")
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        btn_reset_trial = QPushButton("Reset Trial Period")
        btn_reset_trial.setFixedHeight(38)
        btn_reset_trial.setStyleSheet("background-color: #ef4444; color: #ffffff;")
        btn_reset_trial.clicked.connect(self.handle_reset_trial)
        btn_layout.addWidget(btn_reset_trial)

        btn_close = QPushButton("Close Panel")
        btn_close.setFixedHeight(38)
        btn_close.setStyleSheet("background-color: #334155;")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)

        self.load_history()

    def generate_key(self):
        machine_id = self.mid_input.text().strip().upper()
        if not machine_id:
            QMessageBox.warning(self, "Validation Error", "Please enter a Machine ID.")
            return

        # Simple verification of format
        parts = machine_id.split("-")
        if len(parts) != 4 or any(len(p) != 4 for p in parts):
            QMessageBox.warning(self, "Validation Error", "Machine ID must be in the format XXXX-XXXX-XXXX-XXXX.")
            return

        try:
            # Sign the Machine ID using the private key
            act_key = crypto_utils.sign_data(crypto_utils.DEFAULT_PRIVATE_KEY, machine_id.encode('utf-8'))
            self.key_output.setText(act_key)
            
            # Save history entry
            add_history_entry(machine_id, act_key)
            self.load_history()
            
            QMessageBox.information(self, "Key Generated", "Activation Key successfully generated and recorded.")
        except Exception as e:
            QMessageBox.critical(self, "Cryptographic Error", f"Failed to sign Machine ID: {e}")

    def copy_key(self):
        key = self.key_output.text().strip()
        if key:
            QApplication.clipboard().setText(key)
            QMessageBox.information(self, "Copied", "Activation Key copied to clipboard.")
        else:
            QMessageBox.warning(self, "Error", "No key to copy. Generate a key first.")

    def load_history(self):
        self.table.setRowCount(0)
        rows = get_history_entries()
        self.table.setRowCount(len(rows))
        
        for idx, (timestamp, mid, key) in enumerate(rows):
            # Parse timestamp to a prettier local format
            try:
                dt = datetime.fromisoformat(timestamp)
                ts_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                ts_str = timestamp
                
            self.table.setItem(idx, 0, QTableWidgetItem(ts_str))
            self.table.setItem(idx, 1, QTableWidgetItem(mid))
            self.table.setItem(idx, 2, QTableWidgetItem(key[:15] + "..."))
            
            # Align items
            for col in range(3):
                self.table.item(idx, col).setTextAlignment(Qt.AlignCenter)

    def handle_reset_trial(self):
        confirm = QMessageBox.question(
            self, "Confirm Reset",
            "Are you sure you want to reset the trial period on this machine?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            if manager.reset_trial():
                QMessageBox.information(self, "Success", "Trial period has been successfully reset to 30 days.\nPlease restart the application to apply changes.")
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "Failed to reset trial period.")
