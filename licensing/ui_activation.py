import os
import sqlite3
import hashlib
from datetime import datetime

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QMessageBox, QWidget, QTableWidget, QTableWidgetItem, QHeaderView, 
    QApplication, QFrame, QCheckBox, QTextEdit, QFileDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QClipboard

from licensing import manager
from licensing import crypto_utils
from utils.ui_helpers import setup_password_toggle

# Sha256 hashes of vendor credentials:
# Username: vendor
# Passwords accepted:
#   admin@mobileshop2026 (primary)
#   admin@inventory2026  (compatibility)
VENDOR_USER_HASH = "630ba09448af522154f38ef7685ef1f44b0f3e9430f80829a03ce24f400f3754"
VENDOR_PASS_HASHES = {
    "eb81458ed6233107869846cba983748999d33ed7bbaa275d376dd1e87a485d66",  # admin@mobileshop2026
    "79bb8b115d58e709b5db5bf9a6913eaa8bdb8c77f5f2c3db75b8eba473f7670c",  # admin@inventory2026
}
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
        self.setWindowTitle("Inventory & Accounting Management - Free Trial")
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

        desc_text = self.block_msg if self.block_msg else "Please enter an activation key to continue using the application."
        desc = QLabel(desc_text)
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
        setup_password_toggle(self.pass_input)
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
        pwd = self.pass_input.text().strip()

        u_hash = hashlib.sha256(user.encode('utf-8')).hexdigest()
        p_hash = hashlib.sha256(pwd.encode('utf-8')).hexdigest()

        if u_hash == VENDOR_USER_HASH and (p_hash in VENDOR_PASS_HASHES or p_hash == VENDOR_PASS_HASH):
            self.accept()
        else:
            self.err_lbl.setText("Incorrect vendor credentials.")


class VendorGeneratorDialog(QDialog):
    """Embedded vendor dashboard to generate activation keys and view activation history."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Vendor License Generator")
        self.setFixedSize(680, 680)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(12)

        title = QLabel("VENDOR ACTIVATION MANAGEMENT")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #f59e0b; letter-spacing: 1px;")
        layout.addWidget(title)

        # Section 1: Generate Key
        gen_frame = QFrame()
        gen_frame.setStyleSheet("background-color: #1b1b32; border: 1px solid #28284e; border-radius: 8px;")
        gen_layout = QVBoxLayout(gen_frame)
        gen_layout.setContentsMargins(15, 12, 15, 12)
        gen_layout.setSpacing(8)

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

        # Section 2: Feature Adaptability Settings
        feat_frame = QFrame()
        feat_frame.setStyleSheet("background-color: #1b1b32; border: 1px solid #28284e; border-radius: 8px;")
        feat_layout = QVBoxLayout(feat_frame)
        feat_layout.setContentsMargins(15, 12, 15, 12)
        feat_layout.setSpacing(8)

        feat_lbl = QLabel("Feature Adaptability Settings")
        feat_lbl.setStyleSheet("font-weight: bold; color: #ffffff; font-size: 12px;")
        feat_layout.addWidget(feat_lbl)

        self.chk_repair = QCheckBox("Enable Repair Service Desk (Shows/hides Service Cards UI)")
        self.chk_money = QCheckBox("Enable Financial Remittance (Shows/hides UPI/Money Transfer UI)")
        self.chk_imei = QCheckBox("Enable Unique Identifier Tracking (Shows/hides IMEI/Serial Number inputs)")

        self.chk_repair.setStyleSheet("color: #ffffff; font-size: 12px;")
        self.chk_money.setStyleSheet("color: #ffffff; font-size: 12px;")
        self.chk_imei.setStyleSheet("color: #ffffff; font-size: 12px;")

        feat_layout.addWidget(self.chk_repair)
        feat_layout.addWidget(self.chk_money)
        feat_layout.addWidget(self.chk_imei)

        btn_save_feat = QPushButton("Save Feature Settings")
        btn_save_feat.setFixedHeight(32)
        btn_save_feat.setStyleSheet("background-color: #10b981; color: #ffffff; font-weight: bold;")
        btn_save_feat.clicked.connect(self.save_feature_settings)
        feat_layout.addWidget(btn_save_feat)

        layout.addWidget(feat_frame)

        # Section 3: Activation History Table
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

        btn_revoke_lic = QPushButton("Revoke Active License")
        btn_revoke_lic.setFixedHeight(38)
        btn_revoke_lic.setStyleSheet("background-color: #dc2626; color: #ffffff; font-weight: bold;")
        btn_revoke_lic.clicked.connect(self.handle_revoke_license)
        btn_layout.addWidget(btn_revoke_lic)

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
        self.load_feature_settings()

    def load_feature_settings(self):
        try:
            from database import Session
            from models import Setting
            session = Session()
            try:
                r = session.query(Setting).filter_by(key='enable_repair_service').first()
                m = session.query(Setting).filter_by(key='enable_money_transfer').first()
                i = session.query(Setting).filter_by(key='enable_imei_tracking').first()
                
                self.chk_repair.setChecked(r.value.lower() == 'true' if r else True)
                self.chk_money.setChecked(m.value.lower() == 'true' if m else True)
                self.chk_imei.setChecked(i.value.lower() == 'true' if i else True)
            finally:
                session.close()
        except Exception as e:
            print(f"Error loading feature settings in vendor panel: {e}")

    def save_feature_settings(self):
        try:
            from database import Session
            from models import Setting
            session = Session()
            try:
                r_val = 'true' if self.chk_repair.isChecked() else 'false'
                m_val = 'true' if self.chk_money.isChecked() else 'false'
                i_val = 'true' if self.chk_imei.isChecked() else 'false'

                def update_key(k, v):
                    sett = session.query(Setting).filter_by(key=k).first()
                    if sett:
                        sett.value = v
                    else:
                        session.add(Setting(key=k, value=v))

                update_key('enable_repair_service', r_val)
                update_key('enable_money_transfer', m_val)
                update_key('enable_imei_tracking', i_val)

                session.commit()
                QMessageBox.information(self, "Success", "Feature adaptability settings updated successfully.")

                # Dynamically update open application main window if running
                for widget in QApplication.topLevelWidgets():
                    if hasattr(widget, 'apply_feature_settings'):
                        widget.apply_feature_settings()
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Error", f"Failed to save feature settings: {e}")
            finally:
                session.close()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Database error: {e}")

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

    def handle_revoke_license(self):
        confirm = QMessageBox.question(
            self, "Confirm Revocation",
            "Are you sure you want to REVOKE the active license on this machine?\n\n"
            "The software will immediately revert to an unactivated state and require activation on next launch.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            if manager.deactivate_software():
                QMessageBox.information(
                    self, "License Revoked",
                    "The license has been successfully revoked from this machine.\n"
                    "The application will now require activation."
                )
                self.accept()
            else:
                QMessageBox.warning(self, "Notice", "No active license file was found to revoke.")


class TransferSuccessDialog(QDialog):
    """Dialog displayed after a successful license transfer showing the new key & certificate."""
    def __init__(self, transfer_data: dict, parent=None):
        super().__init__(parent)
        self.transfer_data = transfer_data
        self.setWindowTitle("License Transfer Completed Successfully")
        self.setFixedSize(650, 520)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)

        title = QLabel("LICENSE TRANSFERRED SUCCESSFULLY")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 17px; font-weight: bold; color: #10b981; letter-spacing: 1px;")
        layout.addWidget(title)

        info_box = QFrame()
        info_box.setStyleSheet("background-color: #1b1b32; border: 1px solid #28284e; border-radius: 8px; padding: 12px;")
        info_layout = QVBoxLayout(info_box)
        info_layout.setSpacing(8)

        lbl_desc = QLabel(
            "The license on <b>THIS computer has been deactivated</b>.<br>"
            "A new activation key has been cryptographically generated for the target computer."
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #e2e8f0; font-size: 13px;")
        info_layout.addWidget(lbl_desc)

        lbl_mid = QLabel(f"<b>Target Machine ID:</b> <code style='color:#38bdf8;'>{self.transfer_data.get('to_machine_id')}</code>")
        lbl_mid.setStyleSheet("color: #cbd5e1; font-size: 13px;")
        info_layout.addWidget(lbl_mid)

        layout.addWidget(info_box)

        # Key Section
        lbl_key_title = QLabel("New Activation Key (Copy & Paste on New PC):")
        lbl_key_title.setStyleSheet("font-weight: bold; color: #f59e0b; font-size: 12px;")
        layout.addWidget(lbl_key_title)

        self.key_edit = QTextEdit()
        self.key_edit.setPlainText(self.transfer_data.get("new_activation_key", ""))
        self.key_edit.setReadOnly(True)
        self.key_edit.setFixedHeight(75)
        self.key_edit.setStyleSheet("font-family: monospace; font-size: 12px; background-color: #141426; color: #10b981; border: 1px solid #28284e; padding: 6px;")
        layout.addWidget(self.key_edit)

        # Action buttons for certificate and copying
        tools_layout = QHBoxLayout()
        btn_copy_key = QPushButton("📋 Copy Activation Key")
        btn_copy_key.setFixedHeight(38)
        btn_copy_key.setStyleSheet("background-color: #6366f1; color: #ffffff; font-weight: bold;")
        btn_copy_key.clicked.connect(self.copy_key)
        tools_layout.addWidget(btn_copy_key)

        btn_save_cert = QPushButton("💾 Save Certificate (.txt)")
        btn_save_cert.setFixedHeight(38)
        btn_save_cert.setStyleSheet("background-color: #334155; color: #ffffff;")
        btn_save_cert.clicked.connect(self.save_certificate)
        tools_layout.addWidget(btn_save_cert)
        layout.addLayout(tools_layout)

        # Instructions
        inst_lbl = QLabel(
            "<b>Next Steps:</b><br>"
            "1. Launch the application on the <b>New PC</b>.<br>"
            "2. When prompted with 'Activation Required', paste this key and click <b>Activate Now</b>.<br>"
            "<i>Note: A backup copy of this certificate was also saved on this computer at:<br>"
            f"<code style='color:#94a3b8;'>{self.transfer_data.get('cert_path', '')}</code></i>"
        )
        inst_lbl.setWordWrap(True)
        inst_lbl.setStyleSheet("color: #94a3b8; font-size: 12px; margin-top: 5px;")
        layout.addWidget(inst_lbl)

        layout.addStretch()

        # Exit application button
        btn_exit = QPushButton("Close and Exit Application")
        btn_exit.setFixedHeight(42)
        btn_exit.setStyleSheet("background-color: #ef4444; color: #ffffff; font-weight: bold;")
        btn_exit.clicked.connect(self.handle_exit)
        layout.addWidget(btn_exit)

    def copy_key(self):
        key = self.key_edit.toPlainText().strip()
        QApplication.clipboard().setText(key)
        QMessageBox.information(self, "Copied", "New Activation Key has been copied to your clipboard!")

    def save_certificate(self):
        cert_text = self.transfer_data.get("certificate_text", "")
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Transfer Certificate",
            os.path.join(os.path.expanduser("~"), "Desktop", "License_Transfer_Certificate.txt"),
            "Text Files (*.txt);;All Files (*)"
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(cert_text)
                QMessageBox.information(self, "Saved", f"Transfer certificate saved successfully to:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Could not save certificate: {e}")

    def handle_exit(self):
        self.accept()
        QApplication.quit()


class TransferLicenseDialog(QDialog):
    """Dialog allowing users to self-service transfer their active license to a new PC."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Self-Service License Transfer")
        self.setFixedSize(580, 500)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(14)

        title = QLabel("TRANSFER LICENSE TO ANOTHER PC")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #6366f1; letter-spacing: 1px;")
        layout.addWidget(title)

        # Instructions Frame
        guide_box = QFrame()
        guide_box.setStyleSheet("background-color: #1b1b32; border: 1px solid #28284e; border-radius: 8px; padding: 12px;")
        guide_layout = QVBoxLayout(guide_box)
        guide_layout.setSpacing(6)

        step_lbl = QLabel(
            "<b>How to transfer your license:</b><br>"
            "1. Install and launch this software on your <b>New Computer</b>.<br>"
            "2. On the New Computer's activation screen, copy its <b>Machine ID</b>.<br>"
            "3. Paste the New Machine ID below and click <b>Transfer & Deactivate</b>."
        )
        step_lbl.setWordWrap(True)
        step_lbl.setStyleSheet("color: #e2e8f0; font-size: 12px;")
        guide_layout.addWidget(step_lbl)
        layout.addWidget(guide_box)

        # Current Machine ID
        cur_mid = manager.generate_machine_id()
        cur_layout = QHBoxLayout()
        lbl_cur = QLabel("This PC Machine ID:")
        lbl_cur.setFixedWidth(160)
        lbl_cur.setStyleSheet("font-weight: bold; color: #94a3b8;")
        self.cur_mid_edit = QLineEdit(cur_mid)
        self.cur_mid_edit.setReadOnly(True)
        self.cur_mid_edit.setFixedHeight(35)
        self.cur_mid_edit.setStyleSheet("background-color: #141426; color: #38bdf8; font-family: monospace; font-size: 13px; border: 1px solid #28284e; padding: 4px;")
        cur_layout.addWidget(lbl_cur)
        cur_layout.addWidget(self.cur_mid_edit)
        layout.addLayout(cur_layout)

        # Target Machine ID Input
        tgt_layout = QHBoxLayout()
        lbl_tgt = QLabel("New PC Machine ID *:")
        lbl_tgt.setFixedWidth(160)
        lbl_tgt.setStyleSheet("font-weight: bold; color: #ffffff;")
        self.tgt_mid_edit = QLineEdit()
        self.tgt_mid_edit.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        self.tgt_mid_edit.setFixedHeight(38)
        self.tgt_mid_edit.setStyleSheet("font-family: monospace; font-size: 14px; padding: 5px; border: 1px solid #6366f1;")
        tgt_layout.addWidget(lbl_tgt)
        tgt_layout.addWidget(self.tgt_mid_edit)
        layout.addLayout(tgt_layout)

        # Warning Card
        warn_box = QFrame()
        warn_box.setStyleSheet("background-color: #2a1515; border: 1px solid #7f1d1d; border-radius: 6px; padding: 10px;")
        warn_layout = QVBoxLayout(warn_box)
        warn_text = QLabel(
            "⚠️ <b>WARNING - PERMANENT ACTION:</b><br>"
            "This will immediately <b>REVOKE and deactivate</b> the license on THIS computer.<br>"
            "You will not be able to run the software on this machine without a new license key."
        )
        warn_text.setWordWrap(True)
        warn_text.setStyleSheet("color: #fca5a5; font-size: 12px;")
        warn_layout.addWidget(warn_text)
        layout.addWidget(warn_box)

        layout.addStretch()

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_transfer = QPushButton("Transfer & Deactivate This PC")
        self.btn_transfer.setFixedHeight(42)
        self.btn_transfer.setStyleSheet("background-color: #f59e0b; color: #000000; font-weight: bold; font-size: 13px;")
        self.btn_transfer.clicked.connect(self.handle_transfer)
        btn_layout.addWidget(self.btn_transfer)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setFixedHeight(42)
        btn_cancel.setStyleSheet("background-color: #334155; color: #ffffff;")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        layout.addLayout(btn_layout)

    def handle_transfer(self):
        target_mid = self.tgt_mid_edit.text().strip().upper()
        if not target_mid:
            QMessageBox.warning(self, "Validation Error", "Please enter the Target Machine ID from the new computer.")
            return

        clean = target_mid.replace("-", "").replace(" ", "")
        if len(clean) != 16 or not clean.isalnum():
            QMessageBox.warning(
                self, "Invalid Machine ID",
                "Machine ID must consist of 16 characters in format XXXX-XXXX-XXXX-XXXX."
            )
            return

        cur_mid = manager.generate_machine_id()
        formatted_target = f"{clean[0:4]}-{clean[4:8]}-{clean[8:12]}-{clean[12:16]}"
        if formatted_target == cur_mid:
            QMessageBox.warning(
                self, "Invalid Target",
                "The target Machine ID cannot be the same as this computer's Machine ID."
            )
            return

        confirm = QMessageBox.question(
            self, "Confirm Permanent License Transfer",
            f"Are you sure you want to transfer your license to:\n\n"
            f"Target Machine ID: {formatted_target}\n\n"
            "This computer will be immediately DEACTIVATED and closed.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        result = manager.transfer_license(formatted_target)
        if not result.get("success"):
            QMessageBox.critical(self, "Transfer Failed", result.get("error", "An error occurred during transfer."))
            return

        self.hide()
        success_dlg = TransferSuccessDialog(result, self.parent())
        success_dlg.exec()
        self.accept()

