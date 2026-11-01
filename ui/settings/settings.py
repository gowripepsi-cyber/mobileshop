from PySide6.QtWidgets import (QApplication, QWidget, QColorDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QMessageBox, QFrame, QFormLayout, QTabWidget, QFileDialog,
                             QCheckBox, QInputDialog, QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
                             QScrollArea, QGridLayout, QSizePolicy)
import os
import shutil
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from database import Session, Setting, User, get_hash, engine, init_db
from utils.db_backup import backup_db, restore_db
from utils.ui_helpers import setup_password_toggle
from utils.translator import tr
from ui.settings.user_management import UserManagementView


class LicenseInfoCard(QFrame):
    """
    Clean, responsive hardware binding & license information grid.
    Supports consistent desktop side-by-side columns and mobile stacked layout.
    """
    def __init__(self, cur_mid, status_text, status_color, license_file, on_copy_mid, parent=None):
        super().__init__(parent)
        self.setObjectName("license_info_card")
        self.setStyleSheet("""
            QFrame#license_info_card {
                background-color: #fbfdf9;
                border: 1.5px solid #8fd53b;
                border-radius: 14px;
            }
        """)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setMinimumWidth(280)

        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(18, 18, 18, 18)
        self.grid.setHorizontalSpacing(14)
        self.grid.setVerticalSpacing(14)

        box_css = "background-color: #ffffff; border: 1.5px solid #8fd53b; border-radius: 10px;"
        lbl_style = f"{box_css} color: #334155; font-size: 13px; font-weight: 600; padding: 0 16px;"

        # --- Row 1: Machine ID ---
        self.lbl_mid = QLabel("Machine ID (Hardware Bound):")
        self.lbl_mid.setFixedHeight(44)
        self.lbl_mid.setStyleSheet(lbl_style)
        self.lbl_mid.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        self.val_box_mid = QFrame()
        self.val_box_mid.setFixedHeight(44)
        self.val_box_mid.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.val_box_mid.setStyleSheet(f"QFrame {{ {box_css} }}")
        val_l_mid = QHBoxLayout(self.val_box_mid)
        val_l_mid.setContentsMargins(16, 0, 10, 0)
        val_l_mid.setSpacing(12)

        self.lbl_mid_val = QLabel(cur_mid)
        self.lbl_mid_val.setStyleSheet("font-family: monospace; font-size: 14px; font-weight: bold; color: #0284c7; border: none; background: transparent;")
        self.lbl_mid_val.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        self.btn_copy_mid = QPushButton("Copy")
        self.btn_copy_mid.setCursor(Qt.PointingHandCursor)
        self.btn_copy_mid.setFixedHeight(28)
        self.btn_copy_mid.setFixedWidth(65)
        self.btn_copy_mid.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #ffffff;
                font-size: 11px;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 0 8px;
            }
            QPushButton:hover {
                background-color: #334155;
            }
            QPushButton:pressed {
                background-color: #0f172a;
            }
        """)
        self.btn_copy_mid.clicked.connect(on_copy_mid)

        val_l_mid.addWidget(self.lbl_mid_val)
        val_l_mid.addWidget(self.btn_copy_mid)
        val_l_mid.addStretch()

        # --- Row 2: Status ---
        self.lbl_status = QLabel("License Status:")
        self.lbl_status.setFixedHeight(44)
        self.lbl_status.setStyleSheet(lbl_style)
        self.lbl_status.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        self.val_box_status = QFrame()
        self.val_box_status.setFixedHeight(44)
        self.val_box_status.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.val_box_status.setStyleSheet(f"QFrame {{ {box_css} }}")
        val_l_status = QHBoxLayout(self.val_box_status)
        val_l_status.setContentsMargins(16, 0, 16, 0)

        self.lbl_status_val = QLabel(status_text)
        self.lbl_status_val.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {status_color}; border: none; background: transparent;")
        self.lbl_status_val.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        val_l_status.addWidget(self.lbl_status_val)

        # --- Row 3: File Path ---
        self.lbl_path = QLabel("License File Path:")
        self.lbl_path.setFixedHeight(44)
        self.lbl_path.setStyleSheet(lbl_style)
        self.lbl_path.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        self.val_box_path = QFrame()
        self.val_box_path.setFixedHeight(44)
        self.val_box_path.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.val_box_path.setStyleSheet(f"QFrame {{ {box_css} }}")
        val_l_path = QHBoxLayout(self.val_box_path)
        val_l_path.setContentsMargins(16, 0, 16, 0)

        self.lbl_file = QLabel(license_file)
        self.lbl_file.setStyleSheet("color: #64748b; font-size: 11px; font-family: monospace; border: none; background: transparent;")
        self.lbl_file.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        val_l_path.addWidget(self.lbl_file)

        self.is_stacked = None
        self.set_layout_mode(stacked=False)

    def set_layout_mode(self, stacked: bool):
        if self.is_stacked == stacked:
            return
        self.is_stacked = stacked

        self.grid.removeWidget(self.lbl_mid)
        self.grid.removeWidget(self.val_box_mid)
        self.grid.removeWidget(self.lbl_status)
        self.grid.removeWidget(self.val_box_status)
        self.grid.removeWidget(self.lbl_path)
        self.grid.removeWidget(self.val_box_path)

        if stacked:
            self.lbl_mid.setMinimumWidth(0)
            self.lbl_mid.setMaximumWidth(16777215)
            self.lbl_status.setMinimumWidth(0)
            self.lbl_status.setMaximumWidth(16777215)
            self.lbl_path.setMinimumWidth(0)
            self.lbl_path.setMaximumWidth(16777215)

            self.grid.addWidget(self.lbl_mid, 0, 0)
            self.grid.addWidget(self.val_box_mid, 1, 0)
            self.grid.addWidget(self.lbl_status, 2, 0)
            self.grid.addWidget(self.val_box_status, 3, 0)
            self.grid.addWidget(self.lbl_path, 4, 0)
            self.grid.addWidget(self.val_box_path, 5, 0)

            self.grid.setColumnStretch(0, 1)
            self.grid.setColumnStretch(1, 0)
            self.grid.setVerticalSpacing(8)
        else:
            self.lbl_mid.setMinimumWidth(230)
            self.lbl_mid.setMaximumWidth(230)
            self.lbl_status.setMinimumWidth(230)
            self.lbl_status.setMaximumWidth(230)
            self.lbl_path.setMinimumWidth(230)
            self.lbl_path.setMaximumWidth(230)

            self.grid.addWidget(self.lbl_mid, 0, 0)
            self.grid.addWidget(self.val_box_mid, 0, 1)
            self.grid.addWidget(self.lbl_status, 1, 0)
            self.grid.addWidget(self.val_box_status, 1, 1)
            self.grid.addWidget(self.lbl_path, 2, 0)
            self.grid.addWidget(self.val_box_path, 2, 1)

            self.grid.setColumnStretch(0, 0)
            self.grid.setColumnStretch(1, 1)
            self.grid.setVerticalSpacing(14)

    def check_responsive(self, available_width: int):
        should_stack = (available_width < 560)
        self.set_layout_mode(stacked=should_stack)

    def update_status(self, text: str, color: str):
        self.lbl_status_val.setText(text)
        self.lbl_status_val.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {color}; border: none; background: transparent;")


class SettingsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_logo_path = None
        self.logo_removed = False
        self.selected_theme_color = "#8fd53b"
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
        tab_layout = QVBoxLayout(self.shop_tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; } QScrollArea > QWidget > QWidget { background: transparent; }")

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(10, 10, 10, 10)
        container_layout.setSpacing(14)
        container_layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)

        card = QFrame()
        card.setProperty("class", "CardFrame")
        card.setMinimumWidth(820)
        card.setMaximumWidth(880)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(16)

        # ---------------------------------------------------------------------
        # Top Row: Shop Logo (Left) and Theme Color Picker (Right) Side-by-Side
        # ---------------------------------------------------------------------
        top_row = QHBoxLayout()
        top_row.setSpacing(14)

        # 1. Shop Logo Section (Centered Inside Card)
        logo_section = QFrame()
        logo_section.setObjectName("logo_section")
        logo_section.setStyleSheet("""
            QFrame#logo_section {
                background-color: #f8fafc;
                border: 1.5px dashed #cbd5e1;
                border-radius: 14px;
            }
        """)
        logo_section_layout = QVBoxLayout(logo_section)
        logo_section_layout.setContentsMargins(14, 14, 14, 14)
        logo_section_layout.setAlignment(Qt.AlignCenter)
        logo_section_layout.setSpacing(8)

        lbl_logo_sec_title = QLabel("Shop Logo / Emblem (கடை லோகோ)")
        lbl_logo_sec_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #334155;")
        lbl_logo_sec_title.setAlignment(Qt.AlignCenter)
        logo_section_layout.addWidget(lbl_logo_sec_title, alignment=Qt.AlignCenter)

        # Centered Circular Logo Preview (68x68)
        self.logo_preview_lbl = QLabel("☀️")
        self.logo_preview_lbl.setFixedSize(68, 68)
        self.logo_preview_lbl.setAlignment(Qt.AlignCenter)
        self.logo_preview_lbl.setStyleSheet("""
            QLabel {
                background-color: #fffbeb;
                border: 2.5px dashed #f59e0b;
                border-radius: 34px;
                font-size: 30px;
            }
        """)
        logo_section_layout.addWidget(self.logo_preview_lbl, alignment=Qt.AlignCenter)

        # Centered Buttons Row (Upload & Remove)
        logo_btn_row = QHBoxLayout()
        logo_btn_row.setAlignment(Qt.AlignCenter)
        logo_btn_row.setSpacing(8)

        self.btn_upload_logo = QPushButton("📁 Upload Logo")
        self.btn_upload_logo.setObjectName("btn_theme_primary")
        self.btn_upload_logo.setProperty("class", "btn-success")
        self.btn_upload_logo.setCursor(Qt.PointingHandCursor)
        self.btn_upload_logo.setFixedHeight(32)
        self.btn_upload_logo.clicked.connect(self.choose_shop_logo)

        self.btn_remove_logo = QPushButton("✖ Remove")
        self.btn_remove_logo.setProperty("class", "btn-danger")
        self.btn_remove_logo.setCursor(Qt.PointingHandCursor)
        self.btn_remove_logo.setFixedHeight(32)
        self.btn_remove_logo.clicked.connect(self.remove_shop_logo)

        logo_btn_row.addWidget(self.btn_upload_logo)
        logo_btn_row.addWidget(self.btn_remove_logo)
        logo_section_layout.addLayout(logo_btn_row)

        lbl_hint = QLabel("PNG, JPG, WEBP. Centered on sidebar & PDF.")
        lbl_hint.setStyleSheet("color: #64748b; font-size: 11px;")
        lbl_hint.setAlignment(Qt.AlignCenter)
        logo_section_layout.addWidget(lbl_hint, alignment=Qt.AlignCenter)

        top_row.addWidget(logo_section, 1)

        # 2. Software Theme Color Section (Color Picker Option)
        theme_section = QFrame()
        theme_section.setObjectName("theme_section")
        theme_section.setStyleSheet("""
            QFrame#theme_section {
                background-color: #f8fafc;
                border: 1.5px solid #e2e8f0;
                border-radius: 14px;
            }
        """)
        theme_section_layout = QVBoxLayout(theme_section)
        theme_section_layout.setContentsMargins(14, 14, 14, 14)
        theme_section_layout.setSpacing(10)

        theme_header = QHBoxLayout()
        lbl_theme_title = QLabel("🎨 Theme Color (தீம் நிறம்)")
        lbl_theme_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #0f172a;")
        theme_header.addWidget(lbl_theme_title)
        theme_header.addStretch()

        self.theme_preview_badge = QLabel("Theme Preview")
        self.theme_preview_badge.setFixedHeight(24)
        self.theme_preview_badge.setAlignment(Qt.AlignCenter)
        self.theme_preview_badge.setStyleSheet(
            "background-color: #8fd53b; color: #0f172a; font-weight: bold; font-size: 11px; padding: 2px 12px; border-radius: 12px;"
        )
        theme_header.addWidget(self.theme_preview_badge)
        theme_section_layout.addLayout(theme_header)

        # Color controls row
        picker_row = QHBoxLayout()
        picker_row.setSpacing(8)

        self.color_swatch = QLabel()
        self.color_swatch.setFixedSize(32, 32)
        self.color_swatch.setCursor(Qt.PointingHandCursor)
        self.color_swatch.setStyleSheet("background-color: #8fd53b; border: 2px solid #cbd5e1; border-radius: 16px;")

        self.hex_input = QLineEdit("#8fd53b")
        self.hex_input.setFixedWidth(85)
        self.hex_input.setFixedHeight(32)
        self.hex_input.setAlignment(Qt.AlignCenter)
        self.hex_input.setStyleSheet("font-family: monospace; font-size: 12px; font-weight: bold;")
        self.hex_input.textChanged.connect(self.on_hex_input_changed)

        self.btn_pick_color = QPushButton("🎨 Pick")
        self.btn_pick_color.setToolTip("Open Color Picker Dialog")
        self.btn_pick_color.setProperty("class", "btn-secondary")
        self.btn_pick_color.setCursor(Qt.PointingHandCursor)
        self.btn_pick_color.setFixedHeight(32)
        self.btn_pick_color.clicked.connect(self.open_color_picker)

        self.btn_apply_theme = QPushButton("⚡ Apply")
        self.btn_apply_theme.setToolTip("Apply Theme Color to Entire Software")
        self.btn_apply_theme.setObjectName("btn_theme_primary")
        self.btn_apply_theme.setProperty("class", "btn-success")
        self.btn_apply_theme.setCursor(Qt.PointingHandCursor)
        self.btn_apply_theme.setFixedHeight(32)
        self.btn_apply_theme.clicked.connect(self.apply_selected_theme)

        self.btn_reset_theme = QPushButton("↺")
        self.btn_reset_theme.setToolTip("Reset to Default Lime Green (#8fd53b)")
        self.btn_reset_theme.setProperty("class", "btn-secondary")
        self.btn_reset_theme.setCursor(Qt.PointingHandCursor)
        self.btn_reset_theme.setFixedSize(32, 32)
        self.btn_reset_theme.clicked.connect(lambda: self.set_theme_color("#8fd53b"))

        picker_row.addWidget(self.color_swatch)
        picker_row.addWidget(self.hex_input)
        picker_row.addWidget(self.btn_pick_color)
        picker_row.addWidget(self.btn_apply_theme)
        picker_row.addWidget(self.btn_reset_theme)
        picker_row.addStretch()
        theme_section_layout.addLayout(picker_row)

        # Quick Preset Palette Chips
        preset_row = QHBoxLayout()
        preset_row.setSpacing(6)
        lbl_presets = QLabel("Presets:")
        lbl_presets.setStyleSheet("font-size: 11px; color: #64748b; font-weight: 600;")
        preset_row.addWidget(lbl_presets)

        presets = [
            ("#8fd53b", "Fresh Lime"),
            ("#10b981", "Emerald Green"),
            ("#2563eb", "Royal Blue"),
            ("#7c3aed", "Modern Violet"),
            ("#f59e0b", "Warm Amber"),
            ("#ef4444", "Crimson Red"),
            ("#06b6d4", "Ocean Cyan"),
            ("#334155", "Slate Charcoal"),
        ]
        for hex_val, name in presets:
            chip = QPushButton()
            chip.setFixedSize(22, 22)
            chip.setCursor(Qt.PointingHandCursor)
            chip.setToolTip(f"{name} ({hex_val})")
            chip.setStyleSheet(f"background-color: {hex_val}; border-radius: 11px; border: 1.5px solid #cbd5e1;")
            chip.clicked.connect(lambda _, c=hex_val: self.set_theme_color(c))
            preset_row.addWidget(chip)
        preset_row.addStretch()
        theme_section_layout.addLayout(preset_row)

        top_row.addWidget(theme_section, 1)
        card_layout.addLayout(top_row)

        # ---------------------------------------------------------------------
        # Bottom: Shop Profile Details Form
        # ---------------------------------------------------------------------
        form_layout = QFormLayout()
        form_layout.setContentsMargins(0, 4, 0, 0)
        form_layout.setSpacing(12)

        lbl_profile_title = QLabel("Modify Shop Business Profile")
        lbl_profile_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #0f172a; margin-bottom: 4px;")
        form_layout.addRow(lbl_profile_title)

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
        self.save_shop_btn.setObjectName("btn_theme_primary")
        self.save_shop_btn.setProperty("class", "btn-success")
        self.save_shop_btn.setFixedHeight(36)
        self.save_shop_btn.clicked.connect(self.save_shop_details)
        form_layout.addRow("", self.save_shop_btn)

        card_layout.addLayout(form_layout)
        container_layout.addWidget(card)
        scroll.setWidget(container)

        tab_layout.addWidget(scroll)
        self.update_theme_ui_elements()

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

            s_logo = session.query(Setting).filter_by(key='shop_logo').first()
            if s_logo and s_logo.value and os.path.exists(s_logo.value):
                self.selected_logo_path = s_logo.value
                self.logo_removed = False
                self.update_logo_preview(s_logo.value)
            else:
                self.selected_logo_path = ""
                self.logo_removed = False
                self.update_logo_preview(None)

            s_theme = session.query(Setting).filter_by(key='theme_color').first()
            if s_theme and s_theme.value:
                self.set_theme_color(s_theme.value)
            else:
                self.set_theme_color("#8fd53b")

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

            # Save Shop Logo
            s_logo = session.query(Setting).filter_by(key='shop_logo').first()
            if not s_logo:
                s_logo = Setting(key='shop_logo', value='')
                session.add(s_logo)

            if getattr(self, 'logo_removed', False):
                s_logo.value = ''
                self.selected_logo_path = ''
            elif getattr(self, 'selected_logo_path', None) and os.path.exists(self.selected_logo_path):
                os.makedirs("assets", exist_ok=True)
                ext = os.path.splitext(self.selected_logo_path)[1].lower() or ".png"
                dest_path = os.path.abspath(f"assets/shop_logo{ext}")
                if os.path.abspath(self.selected_logo_path) != dest_path:
                    import shutil
                    shutil.copy2(self.selected_logo_path, dest_path)
                s_logo.value = dest_path
                self.selected_logo_path = dest_path
            
            # Save theme color
            s_theme = session.query(Setting).filter_by(key='theme_color').first()
            theme_val = getattr(self, 'selected_theme_color', '#8fd53b') or '#8fd53b'
            if not s_theme:
                s_theme = Setting(key='theme_color', value=theme_val)
                session.add(s_theme)
            else:
                s_theme.value = theme_val

            if not enable_gst_setting:
                enable_gst_setting = Setting(key='enable_gst', value='false')
                session.add(enable_gst_setting)
            enable_gst_setting.value = 'true' if self.enable_gst_checkbox.isChecked() else 'false'

            session.commit()
            QMessageBox.information(self, "Success", "Shop profile details updated successfully.")

            # Apply theme globally across application
            from styles import get_theme_stylesheet
            app = QApplication.instance()
            if app:
                app.setStyleSheet(get_theme_stylesheet(theme_val))

            # Update shop name and theme in main window sidebar dynamically
            main_window = self.window()
            if main_window:
                if hasattr(main_window, 'update_theme'):
                    main_window.update_theme(theme_val)
                elif hasattr(main_window, 'update_shop_name'):
                    main_window.update_shop_name()

            self.refresh_data()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save details: {e}")
        finally:
            session.close()

    def update_theme_ui_elements(self):
        theme_hex = getattr(self, 'selected_theme_color', '#8fd53b') or '#8fd53b'
        c = QColor(theme_hex)
        if not c.isValid():
            c = QColor('#8fd53b')
        lum = (0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()) / 255.0
        text_c = "#0f172a" if lum > 0.55 else "#ffffff"
        hover_c = c.darker(110).name()

        primary_btn_css = f"""
            QPushButton {{
                background-color: {theme_hex};
                color: {text_c};
                font-weight: bold;
                border: none;
                border-radius: 10px;
                padding: 6px 16px;
            }}
            QPushButton:hover {{
                background-color: {hover_c};
            }}
        """

        if hasattr(self, 'btn_upload_logo'):
            self.btn_upload_logo.setStyleSheet(primary_btn_css)
        if hasattr(self, 'btn_apply_theme'):
            self.btn_apply_theme.setStyleSheet(primary_btn_css)
        if hasattr(self, 'save_shop_btn'):
            self.save_shop_btn.setStyleSheet(primary_btn_css)
        if hasattr(self, 'color_swatch'):
            self.color_swatch.setStyleSheet(f"background-color: {theme_hex}; border: 2px solid #cbd5e1; border-radius: 16px;")
        if hasattr(self, 'theme_preview_badge'):
            self.theme_preview_badge.setStyleSheet(
                f"background-color: {theme_hex}; color: {text_c}; "
                f"font-weight: bold; font-size: 11px; padding: 2px 12px; border-radius: 12px;"
            )
        self.update_logo_preview(self.selected_logo_path if not getattr(self, 'logo_removed', False) else None)

    def on_hex_input_changed(self, text):
        val = text.strip()
        if not val.startswith('#'):
            val = '#' + val
        c = QColor(val)
        if c.isValid():
            self.selected_theme_color = c.name()
            self.color_swatch.setStyleSheet(f"background-color: {self.selected_theme_color}; border: 2px solid #cbd5e1; border-radius: 17px;")
            lum = (0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()) / 255.0
            text_c = "#0f172a" if lum > 0.55 else "#ffffff"
            self.theme_preview_badge.setStyleSheet(
                f"background-color: {self.selected_theme_color}; color: {text_c}; "
                f"font-weight: bold; font-size: 11px; padding: 3px 14px; border-radius: 13px;"
            )
            self.update_theme_ui_elements()

    def set_theme_color(self, hex_val):
        c = QColor(hex_val)
        if c.isValid():
            self.selected_theme_color = c.name()
            if hasattr(self, 'hex_input') and self.hex_input.text() != self.selected_theme_color:
                self.hex_input.setText(self.selected_theme_color)
            self.update_theme_ui_elements()

    def open_color_picker(self):
        curr = QColor(getattr(self, 'selected_theme_color', '#8fd53b') or "#8fd53b")
        picked = QColorDialog.getColor(curr, self, "Select Software Theme Color")
        if picked.isValid():
            self.set_theme_color(picked.name())

    def apply_selected_theme(self):
        theme_hex = self.hex_input.text().strip()
        if not theme_hex.startswith('#'):
            theme_hex = '#' + theme_hex
        c = QColor(theme_hex)
        if not c.isValid():
            QMessageBox.warning(self, "Invalid Color", "Please enter a valid hex color code (e.g. #8FD53B).")
            return
        
        self.selected_theme_color = c.name()

        # Save to database
        session = Session()
        try:
            t_setting = session.query(Setting).filter_by(key='theme_color').first()
            if not t_setting:
                t_setting = Setting(key='theme_color', value=self.selected_theme_color)
                session.add(t_setting)
            else:
                t_setting.value = self.selected_theme_color
            session.commit()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save theme: {e}")
            return
        finally:
            session.close()

        # Apply globally
        from styles import get_theme_stylesheet
        app = QApplication.instance()
        if app:
            app.setStyleSheet(get_theme_stylesheet(self.selected_theme_color))

        main_window = self.window()
        if main_window:
            if hasattr(main_window, 'update_theme'):
                main_window.update_theme(self.selected_theme_color)
            elif hasattr(main_window, 'update_shop_name'):
                main_window.update_shop_name()

        self.update_logo_preview(self.selected_logo_path if not getattr(self, 'logo_removed', False) else None)
        QMessageBox.information(self, "Theme Applied", f"Software theme color updated to {self.selected_theme_color} successfully!")

    def choose_shop_logo(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Shop Logo", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.ico *.webp)"
        )
        if file_path:
            from utils.ui_helpers import get_circular_pixmap
            circ_pix = get_circular_pixmap(file_path, size=72)
            if circ_pix and not circ_pix.isNull():
                self.selected_logo_path = file_path
                self.logo_removed = False
                border_c = getattr(self, 'selected_theme_color', '#8fd53b') or '#8fd53b'
                self.logo_preview_lbl.clear()
                self.logo_preview_lbl.setPixmap(circ_pix)
                self.logo_preview_lbl.setStyleSheet(f"border: 2.5px solid {border_c}; border-radius: 36px; background-color: #ffffff;")
                self.btn_remove_logo.setEnabled(True)
            else:
                QMessageBox.warning(self, "Invalid Image", "Could not load the selected image file.")

    def remove_shop_logo(self):
        self.selected_logo_path = ""
        self.logo_removed = True
        self.update_logo_preview(None)

    def update_logo_preview(self, logo_path):
        border_c = getattr(self, 'selected_theme_color', '#8fd53b') or '#8fd53b'
        if hasattr(self, 'logo_preview_lbl'):
            if logo_path and os.path.exists(logo_path):
                from utils.ui_helpers import get_circular_pixmap
                circ_pix = get_circular_pixmap(logo_path, size=72)
                if circ_pix and not circ_pix.isNull():
                    self.logo_preview_lbl.clear()
                    self.logo_preview_lbl.setPixmap(circ_pix)
                    self.logo_preview_lbl.setStyleSheet(f"border: 2.5px solid {border_c}; border-radius: 36px; background-color: #ffffff;")
                    if hasattr(self, 'btn_remove_logo'):
                        self.btn_remove_logo.setEnabled(True)
                    return
            self.logo_preview_lbl.clear()
            self.logo_preview_lbl.setText("☀️")
            self.logo_preview_lbl.setStyleSheet("""
                QLabel {
                    background-color: #fffbeb;
                    border: 2.5px dashed #f59e0b;
                    border-radius: 36px;
                    font-size: 32px;
                }
            """)
            if hasattr(self, 'btn_remove_logo'):
                self.btn_remove_logo.setEnabled(False)


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
        card_frame.setMinimumWidth(320)
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

        # Hardware & License Info Card (Responsive Grid)
        info = manager.get_license_info()
        cur_mid = info["machine_id"]
        status = info["status"]

        # Status Badge
        if status == "active":
            status_text = "● ACTIVE (Permanent License)"
            status_color = "#8fd53b"
        elif status == "trial":
            days = info["days_remaining"]
            status_text = f"● FREE TRIAL ({days} Days Remaining)"
            status_color = "#f59e0b"
        else:
            status_text = "● UNACTIVATED / EXPIRED"
            status_color = "#ef4444"

        self.license_info_card = LicenseInfoCard(
            cur_mid=cur_mid,
            status_text=status_text,
            status_color=status_color,
            license_file=info["license_file"],
            on_copy_mid=lambda: self.copy_to_clipboard(cur_mid, "Machine ID"),
            parent=card_frame
        )
        self.lbl_mid_val = self.license_info_card.lbl_mid_val
        self.lbl_status_val = self.license_info_card.lbl_status_val
        card_layout.addWidget(self.license_info_card)

        orig_resize = card_frame.resizeEvent
        def on_card_resize(event):
            self.license_info_card.check_responsive(event.size().width())
            if orig_resize:
                orig_resize(event)
        card_frame.resizeEvent = on_card_resize

        # Section: Self-Service Transfer
        sec_title = QLabel("License Actions")
        sec_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #475569; margin-top: 10px;")
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
        danger_frame.setMinimumWidth(320)
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
            status_color = "#8fd53b"
        elif status == "trial":
            days = info["days_remaining"]
            status_text = f"● FREE TRIAL ({days} Days Remaining)"
            status_color = "#f59e0b"
        else:
            status_text = "● UNACTIVATED / EXPIRED"
            status_color = "#ef4444"
        if hasattr(self, 'license_info_card'):
            self.license_info_card.update_status(status_text, status_color)
        elif hasattr(self, 'lbl_status_val'):
            self.lbl_status_val.setText(status_text)
            self.lbl_status_val.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {status_color}; border: none; background: transparent;")

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


