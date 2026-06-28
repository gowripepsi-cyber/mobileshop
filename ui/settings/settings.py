from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QMessageBox, QFrame, QFormLayout, QTabWidget, QFileDialog,
                             QCheckBox, QInputDialog)
from PySide6.QtCore import Qt
from database import Session, Setting, User, get_hash, engine, init_db
from utils.db_backup import backup_db, restore_db

class SettingsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self.tabs = QTabWidget()

        # Tab 1: Shop details
        self.shop_tab = QWidget()
        self.setup_shop_tab()
        self.tabs.addTab(self.shop_tab, "Shop Profile Details")

        # Tab 2: Security
        self.security_tab = QWidget()
        self.setup_security_tab()
        self.tabs.addTab(self.security_tab, "Change Password")

        # Tab 3: Database Admin
        self.db_tab = QWidget()
        self.setup_db_tab()
        self.tabs.addTab(self.db_tab, "Database Admin (Backup & Restore)")

        # Tab 4: System Maintenance & Factory Reset
        self.feature_tab = QWidget()
        self.setup_feature_tab()
        self.tabs.addTab(self.feature_tab, "System Maintenance")

        layout.addWidget(self.tabs)

    def setup_shop_tab(self):
        layout = QVBoxLayout(self.shop_tab)
        layout.setContentsMargins(15, 15, 15, 15)

        form_frame = QFrame()
        form_frame.setProperty("class", "CardFrame")
        form_frame.setMinimumWidth(700)
        form_frame.setMaximumWidth(800)
        form_layout = QFormLayout(form_frame)
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setSpacing(15)

        title = QLabel("Modify Shop Business Profile")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff; margin-bottom: 10px;")
        form_layout.addRow(title)

        self.shop_name_input = QLineEdit()
        self.shop_contact_input = QLineEdit()
        self.shop_address_input = QLineEdit()
        self.shop_gst_input = QLineEdit()

        form_layout.addRow("Shop / Business Name *:", self.shop_name_input)
        form_layout.addRow("Contact Number *:", self.shop_contact_input)
        form_layout.addRow("Billing Address:", self.shop_address_input)
        form_layout.addRow("Shop GSTIN:", self.shop_gst_input)

        self.save_shop_btn = QPushButton("Save Details")
        self.save_shop_btn.setProperty("class", "btn-success")
        self.save_shop_btn.clicked.connect(self.save_shop_details)
        form_layout.addRow("", self.save_shop_btn)

        layout.addWidget(form_frame, 0, Qt.AlignCenter)
        layout.addStretch()

    def setup_security_tab(self):
        layout = QVBoxLayout(self.security_tab)
        layout.setContentsMargins(15, 15, 15, 15)

        form_frame = QFrame()
        form_frame.setProperty("class", "CardFrame")
        form_frame.setMinimumWidth(800)
        form_frame.setMaximumWidth(900)
        form_layout = QFormLayout(form_frame)
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setSpacing(15)

        title = QLabel("Update Credentials")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff; margin-bottom: 10px;")
        form_layout.addRow(title)

        self.old_pass_input = QLineEdit()
        self.old_pass_input.setEchoMode(QLineEdit.Password)
        self.new_pass_input = QLineEdit()
        self.new_pass_input.setEchoMode(QLineEdit.Password)
        self.conf_pass_input = QLineEdit()
        self.conf_pass_input.setEchoMode(QLineEdit.Password)

        form_layout.addRow("Current Password *:", self.old_pass_input)
        form_layout.addRow("New Password *:", self.new_pass_input)
        form_layout.addRow("Confirm New Password *:", self.conf_pass_input)

        self.save_pass_btn = QPushButton("Update Password")
        self.save_pass_btn.clicked.connect(self.update_password)
        form_layout.addRow("", self.save_pass_btn)

        layout.addWidget(form_frame, 0, Qt.AlignCenter)
        layout.addStretch()

    def setup_db_tab(self):
        layout = QVBoxLayout(self.db_tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)

        db_frame = QFrame()
        db_frame.setProperty("class", "CardFrame")
        db_frame.setMinimumHeight(280)
        db_frame.setMinimumWidth(800)
        db_frame.setMaximumWidth(900)
        db_layout = QVBoxLayout(db_frame)
        db_layout.setContentsMargins(20, 20, 20, 20)
        db_layout.setSpacing(15)

        title = QLabel("Database Actions")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff; margin-bottom: 10px;")
        db_layout.addWidget(title)

        desc = QLabel(
            "It is highly recommended to perform backups periodically.<br/>"
            "Restoring a previous backup database will overwrite your current dataset entirely."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #94a3b8;")
        db_layout.addWidget(desc)

        db_layout.addSpacing(10)

        # Buttons
        self.backup_btn = QPushButton("Create Database Backup")
        self.backup_btn.setProperty("class", "btn-success")
        self.backup_btn.clicked.connect(self.create_backup)
        db_layout.addWidget(self.backup_btn)

        self.restore_btn = QPushButton("Restore Database Backup File")
        self.restore_btn.setProperty("class", "btn-danger")
        self.restore_btn.clicked.connect(self.execute_restore)
        db_layout.addWidget(self.restore_btn)

        layout.addWidget(db_frame, 0, Qt.AlignCenter)
        layout.addStretch()

    def refresh_data(self):
        session = Session()
        try:
            # Load settings
            s_name = session.query(Setting).filter_by(key='shop_name').first()
            s_contact = session.query(Setting).filter_by(key='shop_contact').first()
            s_address = session.query(Setting).filter_by(key='shop_address').first()
            s_gst = session.query(Setting).filter_by(key='shop_gst').first()

            if s_name: self.shop_name_input.setText(s_name.value)
            if s_contact: self.shop_contact_input.setText(s_contact.value)
            if s_address: self.shop_address_input.setText(s_address.value)
            if s_gst: self.shop_gst_input.setText(s_gst.value)

        except Exception as e:
            print(f"Error loading settings: {e}")
        finally:
            session.close()

    def save_shop_details(self):
        name = self.shop_name_input.text().strip()
        contact = self.shop_contact_input.text().strip()
        address = self.shop_address_input.text().strip()
        gst = self.shop_gst_input.text().strip()

        if not name or not contact:
            QMessageBox.warning(self, "Validation Error", "Shop name and contact number are mandatory.")
            return

        session = Session()
        try:
            s_name = session.query(Setting).filter_by(key='shop_name').first()
            s_contact = session.query(Setting).filter_by(key='shop_contact').first()
            s_address = session.query(Setting).filter_by(key='shop_address').first()
            s_gst = session.query(Setting).filter_by(key='shop_gst').first()

            s_name.value = name
            s_contact.value = contact
            s_address.value = address
            s_gst.value = gst

            session.commit()
            QMessageBox.information(self, "Success", "Shop profile details updated successfully.")
            self.refresh_data()

            # Update shop name in main window sidebar dynamically
            main_window = self.window()
            if hasattr(main_window, 'update_shop_name'):
                main_window.update_shop_name()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save details: {e}")
        finally:
            session.close()

    def update_password(self):
        old_pass = self.old_pass_input.text()
        new_pass = self.new_pass_input.text()
        conf_pass = self.conf_pass_input.text()

        if not old_pass or not new_pass or not conf_pass:
            QMessageBox.warning(self, "Validation Error", "All fields are required.")
            return

        if new_pass != conf_pass:
            QMessageBox.warning(self, "Validation Error", "New password and confirmation password do not match.")
            return

        session = Session()
        try:
            main_window = self.window()
            username = 'admin'
            if hasattr(main_window, 'user_data') and main_window.user_data:
                username = main_window.user_data['username']

            hashed_old = get_hash(old_pass)
            user = session.query(User).filter_by(username=username, password_hash=hashed_old).first()
            if not user:
                QMessageBox.warning(self, "Validation Error", "Incorrect current password.")
                session.close()
                return

            user.password_hash = get_hash(new_pass)
            session.commit()
            QMessageBox.information(self, "Success", "Password updated successfully.")
            
            # Clear fields
            self.old_pass_input.clear()
            self.new_pass_input.clear()
            self.conf_pass_input.clear()

        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to update password: {e}")
        finally:
            session.close()

    def create_backup(self):
        # Open file dialog to choose directory
        dir_path = QFileDialog.getExistingDirectory(self, "Select Backup Destination Folder")
        if not dir_path:
            return

        success, result = backup_db(dir_path)
        if success:
            QMessageBox.information(self, "Backup Success", f"Database backed up successfully to:\n{result}")
        else:
            QMessageBox.critical(self, "Backup Failed", f"An error occurred: {result}")

    def execute_restore(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select SQLite Database Backup to Restore", 
            "", "Database Files (*.db);;All Files (*)"
        )
        if not file_path:
            return

        confirm = QMessageBox.question(
            self, "Confirm Overwrite Restore", 
            "WARNING: This will completely replace the active database.\n"
            "All current data will be overwritten and lost. Proceed?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            # Run restore
            success, msg = restore_db(file_path)
            if success:
                QMessageBox.information(self, "Restore Completed", msg)
                # Terminate the application immediately so user restarts
                main_window = self.window()
                main_window.close()
            else:
                QMessageBox.critical(self, "Restore Failed", msg)

    def setup_feature_tab(self):
        layout = QVBoxLayout(self.feature_tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)

        # Danger Zone / Factory Reset Panel
        danger_frame = QFrame()
        danger_frame.setProperty("class", "CardFrame")
        danger_frame.setStyleSheet("QFrame { border: 1px solid #ef4444; background-color: #1a0b0b; }")
        danger_frame.setMinimumWidth(800)
        danger_frame.setMaximumWidth(900)
        danger_layout = QVBoxLayout(danger_frame)
        danger_layout.setContentsMargins(20, 20, 20, 20)
        danger_layout.setSpacing(10)

        danger_title = QLabel("Danger Zone (Factory Reset)")
        danger_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #ef4444; border: none; background: transparent;")
        danger_layout.addWidget(danger_title)

        danger_desc = QLabel("Wiping all database data will delete all customers, suppliers, products, stock, cash/bank transactions, money transfers, and company settings. This action is permanent and cannot be undone.")
        danger_desc.setWordWrap(True)
        danger_desc.setStyleSheet("color: #f87171; font-size: 12px; border: none; background: transparent;")
        danger_layout.addWidget(danger_desc)

        self.wipe_btn = QPushButton("Wipe All Data / Factory Reset")
        self.wipe_btn.setStyleSheet("background-color: #ef4444; color: #ffffff; font-weight: bold; padding: 12px 20px; border-radius: 6px;")
        self.wipe_btn.setMinimumHeight(45)
        self.wipe_btn.clicked.connect(self.wipe_all_data)
        danger_layout.addWidget(self.wipe_btn)

        layout.addWidget(danger_frame, 0, Qt.AlignCenter)
        layout.addStretch()

    def wipe_all_data(self):
        confirm1 = QMessageBox.question(
            self, "WARNING: Permanent Factory Reset",
            "Are you sure you want to delete ALL data?\n\n"
            "This will permanently erase all customers, suppliers, products, stock, cash/bank transactions, money transfers, and company settings.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm1 != QMessageBox.Yes:
            return

        text, ok = QInputDialog.getText(
            self, "Confirm Factory Reset",
            "This action cannot be undone.\n\n"
            "To confirm deletion, please type 'WIPE' (all caps):"
        )
        if not ok or text.strip() != "WIPE":
            QMessageBox.warning(self, "Cancelled", "Confirmation code incorrect. Data wipe cancelled.")
            return

        session = Session()
        try:
            session.close()
            
            # Dispose of engine connections to release locks
            engine.dispose()
            
            from models import Base
            Base.metadata.drop_all(engine)
            
            # Recreate all tables and re-seed defaults
            init_db()
            
            QMessageBox.information(
                self, "Reset Completed",
                "All data has been successfully wiped. The application will now close."
            )
            # Close the main window
            main_window = self.window()
            main_window.close()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to wipe data: {e}")
        finally:
            session.close()
