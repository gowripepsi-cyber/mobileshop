from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QMessageBox, QFrame, QFormLayout, QTabWidget, QFileDialog,
                             QCheckBox, QInputDialog, QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
                             QScrollArea)
from PySide6.QtCore import Qt
from database import Session, Setting, User, get_hash, engine, init_db
from utils.db_backup import backup_db, restore_db
from utils.ui_helpers import setup_password_toggle
from utils.translator import tr
from ui.settings.user_management import UserManagementView

class SettingsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self.tabs = QTabWidget()

        # Tab 1: Shop Details
        self.shop_tab = QWidget()
        self.setup_shop_tab()
        self.tabs.addTab(self.shop_tab, tr("Shop Details"))

        # Tab 2: User Management
        self.user_mgmt_tab = UserManagementView(self)
        self.tabs.addTab(self.user_mgmt_tab, tr("User Management"))

        # Tab 3: Security
        self.security_tab = QWidget()
        self.setup_security_tab()
        self.tabs.addTab(self.security_tab, tr("Change Password"))

        # Tab 4: Backup & Restore
        self.db_tab = QWidget()
        self.setup_db_tab()
        self.tabs.addTab(self.db_tab, tr("Backup & Restore"))

        # Tab 5: License & System Maintenance (Merged Tab)
        self.maintenance_tab = QWidget()
        self.feature_tab = self.maintenance_tab
        self.license_tab = self.maintenance_tab
        self.setup_maintenance_tab()
        self.tabs.addTab(self.maintenance_tab, tr("License & Maintenance"))

        # Tab 6: Language Dictionary
        self.lang_dict_tab = QWidget()
        self.setup_lang_dict_tab()
        self.tabs.addTab(self.lang_dict_tab, tr("Language Dictionary"))

        layout.addWidget(self.tabs)

    def retranslate_ui(self):
        """Updates tab headers and labels when active language changes."""
        self.tabs.setTabText(0, tr("Shop Details"))
        self.tabs.setTabText(1, tr("User Management"))
        self.tabs.setTabText(2, tr("Change Password"))
        self.tabs.setTabText(3, tr("Backup & Restore"))
        self.tabs.setTabText(4, tr("License & Maintenance"))
        self.tabs.setTabText(5, tr("Language Dictionary"))

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
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #0f172a; margin-bottom: 10px;")
        form_layout.addRow(title)

        self.shop_name_input = QLineEdit()
        self.shop_contact_input = QLineEdit()
        self.shop_address_input = QLineEdit()
        self.shop_gst_input = QLineEdit()
        self.enable_gst_checkbox = QCheckBox("Enable GST Taxation System")

        form_layout.addRow("Shop / Business Name *:", self.shop_name_input)
        form_layout.addRow("Contact Number *:", self.shop_contact_input)
        form_layout.addRow("Billing Address:", self.shop_address_input)
        form_layout.addRow("Shop GSTIN:", self.shop_gst_input)
        form_layout.addRow("", self.enable_gst_checkbox)

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
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #0f172a; margin-bottom: 10px;")
        form_layout.addRow(title)

        self.old_pass_input = QLineEdit()
        self.old_pass_input.setEchoMode(QLineEdit.Password)
        setup_password_toggle(self.old_pass_input)
        self.new_pass_input = QLineEdit()
        self.new_pass_input.setEchoMode(QLineEdit.Password)
        setup_password_toggle(self.new_pass_input)
        self.conf_pass_input = QLineEdit()
        self.conf_pass_input.setEchoMode(QLineEdit.Password)
        setup_password_toggle(self.conf_pass_input)

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
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #0f172a; margin-bottom: 10px;")
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
            enable_gst_setting = session.query(Setting).filter_by(key='enable_gst').first()

            if s_name: self.shop_name_input.setText(s_name.value)
            if s_contact: self.shop_contact_input.setText(s_contact.value)
            if s_address: self.shop_address_input.setText(s_address.value)
            if s_gst: self.shop_gst_input.setText(s_gst.value)
            if enable_gst_setting:
                self.enable_gst_checkbox.setChecked(enable_gst_setting.value == 'true')

            if hasattr(self, 'user_mgmt_tab'):
                self.user_mgmt_tab.refresh_data()

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
            enable_gst_setting = session.query(Setting).filter_by(key='enable_gst').first()

            s_name.value = name
            s_contact.value = contact
            s_address.value = address
            s_gst.value = gst
            
            if not enable_gst_setting:
                enable_gst_setting = Setting(key='enable_gst', value='false')
                session.add(enable_gst_setting)
            enable_gst_setting.value = 'true' if self.enable_gst_checkbox.isChecked() else 'false'

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

    def setup_maintenance_tab(self):
        from licensing import manager

        main_layout = QVBoxLayout(self.maintenance_tab)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(20, 15, 20, 20)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        # -------------------------------------------------------------
        # Part 1: Hardware Binding & License Management Card
        # -------------------------------------------------------------
        card_frame = QFrame()
        card_frame.setProperty("class", "CardFrame")
        card_frame.setMinimumWidth(750)
        card_frame.setMaximumWidth(850)
        card_layout = QVBoxLayout(card_frame)
        card_layout.setContentsMargins(25, 25, 25, 25)
        card_layout.setSpacing(18)

        title = QLabel("Hardware Binding & License Management")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0f172a;")
        card_layout.addWidget(title)

        subtitle = QLabel("Manage your software license, review hardware binding, or transfer your license to a new PC.")
        subtitle.setStyleSheet("color: #94a3b8; font-size: 12px; margin-bottom: 5px;")
        card_layout.addWidget(subtitle)

        # Info Box Frame
        info_frame = QFrame()
        info_frame.setStyleSheet("background-color: #fbfdf9; border: 1.5px solid #8fd53b; border-radius: 12px; padding: 15px;")
        info_layout = QFormLayout(info_frame)
        info_layout.setSpacing(12)

        info = manager.get_license_info()
        cur_mid = info["machine_id"]
        status = info["status"]

        # Machine ID row with Copy
        mid_row = QHBoxLayout()
        self.lbl_mid_val = QLabel(cur_mid)
        self.lbl_mid_val.setStyleSheet("font-family: monospace; font-size: 14px; font-weight: bold; color: #38bdf8;")
        btn_copy_mid = QPushButton("Copy")
        btn_copy_mid.setFixedWidth(65)
        btn_copy_mid.setFixedHeight(28)
        btn_copy_mid.setStyleSheet("background-color: #334155; font-size: 11px;")
        btn_copy_mid.clicked.connect(lambda: self.copy_to_clipboard(cur_mid, "Machine ID"))
        mid_row.addWidget(self.lbl_mid_val)
        mid_row.addWidget(btn_copy_mid)
        mid_row.addStretch()

        # Status Badge
        if status == "active":
            status_text = "● ACTIVE (Permanent License)"
            status_color = "#10b981"
        elif status == "trial":
            days = info["days_remaining"]
            status_text = f"● FREE TRIAL ({days} Days Remaining)"
            status_color = "#f59e0b"
        else:
            status_text = "● UNACTIVATED / EXPIRED"
            status_color = "#ef4444"

        self.lbl_status_val = QLabel(status_text)
        self.lbl_status_val.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {status_color};")

        # Storage Path
        lbl_file = QLabel(info["license_file"])
        lbl_file.setStyleSheet("color: #64748b; font-size: 11px; font-family: monospace;")
        lbl_file.setWordWrap(True)

        info_layout.addRow("Machine ID (Hardware Bound):", mid_row)
        info_layout.addRow("License Status:", self.lbl_status_val)
        info_layout.addRow("License File Path:", lbl_file)

        card_layout.addWidget(info_frame)

        # Section: Self-Service Transfer
        sec_title = QLabel("License Actions")
        sec_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #cbd5e1; margin-top: 10px;")
        card_layout.addWidget(sec_title)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        # 1. Transfer License
        self.btn_transfer_lic = QPushButton("🔄 Transfer License to Another PC")
        self.btn_transfer_lic.setFixedHeight(42)
        self.btn_transfer_lic.setStyleSheet("background-color: #6366f1; color: #ffffff; font-weight: bold; font-size: 12px;")
        self.btn_transfer_lic.clicked.connect(self.open_transfer_dialog)
        btn_row.addWidget(self.btn_transfer_lic)

        # 2. Revoke License
        self.btn_revoke_lic = QPushButton("⚠️ Revoke / Deactivate License")
        self.btn_revoke_lic.setFixedHeight(42)
        self.btn_revoke_lic.setStyleSheet("background-color: #dc2626; color: #ffffff; font-weight: bold; font-size: 12px;")
        self.btn_revoke_lic.clicked.connect(self.revoke_license)
        btn_row.addWidget(self.btn_revoke_lic)

        # 3. Vendor Portal
        self.btn_vendor_portal = QPushButton("🛠️ Vendor Portal")
        self.btn_vendor_portal.setFixedHeight(42)
        self.btn_vendor_portal.setStyleSheet("background-color: #334155; color: #ffffff; font-size: 12px;")
        self.btn_vendor_portal.clicked.connect(self.open_vendor_portal)
        btn_row.addWidget(self.btn_vendor_portal)

        card_layout.addLayout(btn_row)
        layout.addWidget(card_frame)

        # -------------------------------------------------------------
        # Part 2: Danger Zone / Factory Reset Panel
        # -------------------------------------------------------------
        danger_frame = QFrame()
        danger_frame.setProperty("class", "CardFrame")
        danger_frame.setStyleSheet("QFrame { border: 1px solid #ef4444; background-color: #1a0b0b; }")
        danger_frame.setMinimumWidth(750)
        danger_frame.setMaximumWidth(850)
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

        layout.addWidget(danger_frame)

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

    def setup_feature_tab(self):
        pass

    def setup_license_tab(self):
        pass

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

    def copy_to_clipboard(self, text, label):
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, "Copied", f"{label} copied to clipboard.")

    def open_transfer_dialog(self):
        from licensing.ui_activation import TransferLicenseDialog
        dlg = TransferLicenseDialog(self)
        dlg.exec()
        self.refresh_license_tab()

    def revoke_license(self):
        from licensing import manager
        confirm = QMessageBox.question(
            self, "Confirm Revocation",
            "Are you sure you want to REVOKE the license on this machine?\n\n"
            "The application will immediately lose its activation and will require an activation key to run.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            if manager.deactivate_software():
                QMessageBox.information(
                    self, "License Revoked",
                    "License has been successfully revoked.\nThe application will now close."
                )
                main_window = self.window()
                main_window.close()
            else:
                QMessageBox.warning(self, "Notice", "No active license file was found to revoke.")

    def open_vendor_portal(self):
        from licensing.ui_activation import VendorLoginDialog, VendorGeneratorDialog
        login_dlg = VendorLoginDialog(self)
        if login_dlg.exec() == VendorLoginDialog.Accepted:
            gen_dlg = VendorGeneratorDialog(self)
            gen_dlg.exec()
            self.refresh_license_tab()

    def refresh_license_tab(self):
        from licensing import manager
        info = manager.get_license_info()
        status = info["status"]
        if status == "active":
            status_text = "● ACTIVE (Permanent License)"
            status_color = "#10b981"
        elif status == "trial":
            days = info["days_remaining"]
            status_text = f"● FREE TRIAL ({days} Days Remaining)"
            status_color = "#f59e0b"
        else:
            status_text = "● UNACTIVATED / EXPIRED"
            status_color = "#ef4444"
        if hasattr(self, 'lbl_status_val'):
            self.lbl_status_val.setText(status_text)
            self.lbl_status_val.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {status_color};")

    def setup_lang_dict_tab(self):
        layout = QVBoxLayout(self.lang_dict_tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        card_frame = QFrame()
        card_frame.setProperty("class", "CardFrame")
        card_layout = QVBoxLayout(card_frame)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(12)

        # Header Title
        title = QLabel("Language Dictionary / ஆங்கிலம் - தமிழ் மொழிப் பட்டியல்")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0f172a;")
        card_layout.addWidget(title)

        subtitle = QLabel(
            "English வார்த்தைகளுக்கு இணையான தமிழ் மொழிபெயர்ப்பை இங்கே தேவைக்கேற்ப மாற்றிக் கொள்ளலாம்.\n"
            "• தமிழ் வார்த்தையை மாற்ற: அந்த கட்டத்தில் Double-click செய்து புதிய வார்த்தையை தட்டச்சு செய்யவும்.\n"
            "• மாற்றிய பிறகு கீழே உள்ள 'Save Dictionary' பட்டனை அழுத்தவும்."
        )
        subtitle.setStyleSheet("color: #94a3b8; font-size: 12px; margin-bottom: 5px;")
        card_layout.addWidget(subtitle)

        # Action & Search Bar
        action_bar = QHBoxLayout()
        action_bar.setSpacing(10)

        self.dict_search_input = QLineEdit()
        self.dict_search_input.setPlaceholderText("Search English or Tamil word / வார்த்தைகளைத் தேடுக...")
        self.dict_search_input.setFixedHeight(35)
        self.dict_search_input.textChanged.connect(self.filter_dict_table)
        action_bar.addWidget(self.dict_search_input, 2)

        btn_add = QPushButton("+ Add Word (புதிய சொல்)")
        btn_add.setFixedHeight(35)
        btn_add.setStyleSheet("background-color: #6366f1; color: #ffffff; font-weight: bold; font-size: 11px;")
        btn_add.clicked.connect(self.handle_add_dict_word)
        action_bar.addWidget(btn_add)

        btn_save = QPushButton("💾 Save Dictionary (சேமிக்க)")
        btn_save.setFixedHeight(35)
        btn_save.setProperty("class", "btn-success")
        btn_save.setStyleSheet("font-size: 11px; font-weight: bold;")
        btn_save.clicked.connect(self.save_dict_table_changes)
        action_bar.addWidget(btn_save)

        btn_reset = QPushButton("🔄 Reset to Defaults (மீட்டமை)")
        btn_reset.setFixedHeight(35)
        btn_reset.setStyleSheet("background-color: #334155; color: #ffffff; font-size: 11px;")
        btn_reset.clicked.connect(self.reset_dict_to_defaults)
        action_bar.addWidget(btn_reset)

        card_layout.addLayout(action_bar)

        # Interactive Table
        self.dict_table = QTableWidget()
        self.dict_table.setColumnCount(3)
        self.dict_table.setHorizontalHeaderLabels([
            "English Word / Label (Key)", "Tamil Translation (தமிழ்)", "Action"
        ])
        self.dict_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.dict_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
        self.dict_table.setColumnWidth(0, 320)
        self.dict_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.dict_table.setColumnWidth(2, 70)
        self.dict_table.verticalHeader().setVisible(False)
        self.dict_table.verticalHeader().setDefaultSectionSize(40)
        card_layout.addWidget(self.dict_table)

        layout.addWidget(card_frame)

        self.populate_dict_table()

    def populate_dict_table(self):
        from utils import translator
        translations = translator.load_translations()
        search_txt = self.dict_search_input.text().strip().lower()

        # Filter items
        filtered = []
        for eng, tam in sorted(translations.items()):
            if not search_txt or (search_txt in eng.lower() or search_txt in tam.lower()):
                filtered.append((eng, tam))

        self.dict_table.setRowCount(len(filtered))
        for row, (eng, tam) in enumerate(filtered):
            # Column 0: English (Read-only)
            item_eng = QTableWidgetItem(eng)
            item_eng.setFlags(item_eng.flags() & ~Qt.ItemIsEditable)
            item_eng.setForeground(Qt.cyan)
            self.dict_table.setItem(row, 0, item_eng)

            # Column 1: Tamil (Editable)
            item_tam = QTableWidgetItem(tam)
            item_tam.setToolTip("Double click to edit Tamil translation")
            self.dict_table.setItem(row, 1, item_tam)

            # Column 2: Delete Button
            del_btn = QPushButton("🗑️")
            del_btn.setToolTip("Delete this translation")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setProperty("class", "btn-action-icon-delete")
            del_btn.clicked.connect(lambda checked, k=eng: self.delete_dict_word(k))
            self.dict_table.setCellWidget(row, 2, del_btn)

    def filter_dict_table(self):
        self.populate_dict_table()

    def save_dict_table_changes(self):
        from utils import translator
        all_translations = translator.load_translations()

        # Update in-memory dict with values from currently displayed table
        for row in range(self.dict_table.rowCount()):
            eng_item = self.dict_table.item(row, 0)
            tam_item = self.dict_table.item(row, 1)
            if eng_item and tam_item:
                eng_key = eng_item.text().strip()
                tam_val = tam_item.text().strip()
                if eng_key:
                    all_translations[eng_key] = tam_val

        if translator.save_translations(all_translations):
            QMessageBox.information(
                self, "Saved",
                "Language dictionary updated successfully!\n"
                "மொழிப் பட்டியல் வெற்றிகரமாகச் சேமிக்கப்பட்டது."
            )
            # Retranslate open main window
            main_win = self.window()
            if hasattr(main_win, 'apply_language_change'):
                main_win.apply_language_change()
            self.populate_dict_table()
        else:
            QMessageBox.critical(self, "Error", "Failed to save dictionary changes.")

    def handle_add_dict_word(self):
        from utils import translator
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Word to Dictionary / புதிய சொல் சேர்க்க")
        dialog.setFixedSize(420, 220)
        d_layout = QVBoxLayout(dialog)
        d_layout.setContentsMargins(20, 20, 20, 20)
        d_layout.setSpacing(12)

        form = QFormLayout()
        eng_input = QLineEdit()
        eng_input.setPlaceholderText("e.g. Discount, Net Total, Warranty")
        tam_input = QLineEdit()
        tam_input.setPlaceholderText("e.g. தள்ளுபடி, நிகர மொத்தம், உத்தரவாதம்")

        form.addRow("English Word *:", eng_input)
        form.addRow("Tamil Translation *:", tam_input)
        d_layout.addLayout(form)

        btn_box = QHBoxLayout()
        btn_ok = QPushButton("Add to Dictionary")
        btn_ok.setProperty("class", "btn-success")
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setProperty("class", "btn-secondary")
        btn_cancel.clicked.connect(dialog.reject)

        def do_add():
            k = eng_input.text().strip()
            v = tam_input.text().strip()
            if not k or not v:
                QMessageBox.warning(dialog, "Validation Error", "Please fill in both English and Tamil words.")
                return
            translator.update_single_translation(k, v)
            dialog.accept()

        btn_ok.clicked.connect(do_add)
        btn_box.addWidget(btn_ok)
        btn_box.addWidget(btn_cancel)
        d_layout.addLayout(btn_box)

        if dialog.exec() == QDialog.Accepted:
            self.populate_dict_table()
            main_win = self.window()
            if hasattr(main_win, 'apply_language_change'):
                main_win.apply_language_change()

    def delete_dict_word(self, english_key: str):
        from utils import translator
        confirm = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to remove '{english_key}' from the dictionary?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            translator.delete_single_translation(english_key)
            self.populate_dict_table()
            main_win = self.window()
            if hasattr(main_win, 'apply_language_change'):
                main_win.apply_language_change()

    def reset_dict_to_defaults(self):
        from utils import translator
        confirm = QMessageBox.question(
            self, "Confirm Reset",
            "Are you sure you want to reset the dictionary to factory defaults?\nAny custom words added will be reset.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            translator.reset_to_defaults()
            self.populate_dict_table()
            main_win = self.window()
            if hasattr(main_win, 'apply_language_change'):
                main_win.apply_language_change()
            QMessageBox.information(self, "Reset", "Dictionary restored to defaults.")


