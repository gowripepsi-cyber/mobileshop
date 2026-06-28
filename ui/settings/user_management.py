from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
                             QPushButton, QLineEdit, QLabel, QDialog, QFormLayout, QMessageBox, QHeaderView,
                             QComboBox, QTreeWidget, QTreeWidgetItem, QGroupBox, QHeaderView)
from PySide6.QtCore import Qt
import datetime
import json
from database import Session, User, get_hash
from utils.permissions import MODULE_CATEGORIES, get_default_admin_permissions

from PySide6.QtGui import QFont, QColor, QBrush

class ResetPasswordDialog(QDialog):
    def __init__(self, username, parent=None):
        super().__init__(parent)
        self.username = username
        self.setWindowTitle(f"Reset Password - {username}")
        self.setFixedSize(380, 220)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        form_layout = QFormLayout()
        self.new_pass_input = QLineEdit()
        self.new_pass_input.setEchoMode(QLineEdit.Password)
        self.conf_pass_input = QLineEdit()
        self.conf_pass_input.setEchoMode(QLineEdit.Password)

        form_layout.addRow("New Password *:", self.new_pass_input)
        form_layout.addRow("Confirm Password *:", self.conf_pass_input)
        layout.addLayout(form_layout)

        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Reset Password")
        self.save_btn.clicked.connect(self.handle_save)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setProperty("class", "btn-secondary")
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

    def handle_save(self):
        new_pass = self.new_pass_input.text()
        conf_pass = self.conf_pass_input.text()

        if not new_pass:
            QMessageBox.warning(self, "Validation Error", "Password cannot be empty.")
            return
        if new_pass != conf_pass:
            QMessageBox.warning(self, "Validation Error", "Passwords do not match.")
            return

        session = Session()
        try:
            user = session.query(User).filter_by(username=self.username).first()
            if user:
                user.password_hash = get_hash(new_pass)
                session.commit()
                QMessageBox.information(self, "Success", f"Password for '{self.username}' reset successfully.")
                self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to reset password: {e}")
        finally:
            session.close()


class UserEditDialog(QDialog):
    def __init__(self, user_obj=None, current_user_data=None, parent=None):
        super().__init__(parent)
        self.user_obj = user_obj
        self.current_user_data = current_user_data or {}
        self.setWindowTitle("Edit User Profile" if user_obj else "Add New User Profile")
        self.resize(650, 680)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Form Layout
        form_layout = QFormLayout()
        self.full_name_input = QLineEdit()
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.conf_password_input = QLineEdit()
        self.conf_password_input.setEchoMode(QLineEdit.Password)

        self.role_combo = QComboBox()
        self.role_combo.addItems(["Standard User", "Administrator"])

        self.status_combo = QComboBox()
        self.status_combo.addItems(["Active", "Disabled"])

        form_layout.addRow("Full Name *:", self.full_name_input)
        form_layout.addRow("Login ID (Username) *:", self.username_input)
        if not self.user_obj:
            form_layout.addRow("Password *:", self.password_input)
            form_layout.addRow("Confirm Password *:", self.conf_password_input)
        else:
            self.username_input.setEnabled(False) # Prevent altering username on edit

        form_layout.addRow("System Role *:", self.role_combo)
        form_layout.addRow("Account Status *:", self.status_combo)

        layout.addLayout(form_layout)

        # Permissions Group
        perm_group = QGroupBox("Module Access Permissions (RBAC)")
        perm_layout = QVBoxLayout(perm_group)

        self.perm_tree = QTreeWidget()
        self.perm_tree.setHeaderLabels(["Module / Sub-system", "View", "Add", "Edit", "Delete"])
        self.perm_tree.setStyleSheet("""
            QTreeWidget, QTreeView {
                background-color: #141426;
                alternate-background-color: #18182e;
                border: 1px solid #28284e;
                border-radius: 6px;
                color: #f1f5f9;
            }
            QTreeWidget:disabled, QTreeView:disabled {
                background-color: #141426;
                color: #e2e8f0;
            }
            QTreeWidget::item, QTreeView::item {
                padding: 6px 4px;
                color: #f1f5f9;
                border-bottom: 1px solid #1e1e38;
            }
            QTreeWidget::item:hover, QTreeView::item:hover {
                background-color: #20203c;
                color: #ffffff;
            }
            QTreeWidget::item:selected, QTreeView::item:selected {
                background-color: #4f46e5;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #1c1c36;
                color: #818cf8;
                padding: 8px;
                font-weight: bold;
                border: none;
                border-bottom: 2px solid #2c2c54;
            }
            QTreeWidget::indicator, QCheckBox::indicator {
                width: 18px;
                height: 18px;
                background-color: #1e1e38;
                border: 2px solid #475569;
                border-radius: 4px;
            }
            QTreeWidget::indicator:hover, QCheckBox::indicator:hover {
                border: 2px solid #818cf8;
                background-color: #28284e;
            }
            QTreeWidget::indicator:checked, QCheckBox::indicator:checked {
                background-color: #6366f1;
                border: 2px solid #818cf8;
            }
            QTreeWidget::indicator:unchecked, QCheckBox::indicator:unchecked {
                background-color: #141426;
                border: 2px solid #475569;
            }
            QTreeWidget::indicator:disabled, QCheckBox::indicator:disabled {
                background-color: #18182e;
                border: 2px solid #334155;
            }
            QTreeWidget::indicator:checked:disabled, QCheckBox::indicator:checked:disabled {
                background-color: #3730a3;
                border: 2px solid #818cf8;
            }
        """)
        self.perm_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 5):
            self.perm_tree.header().setSectionResizeMode(i, QHeaderView.ResizeToContents)

        self.populate_permissions_tree()
        perm_layout.addWidget(self.perm_tree)
        layout.addWidget(perm_group)

        # Populate initial values if editing
        if self.user_obj:
            self.full_name_input.setText(self.user_obj.full_name or "")
            self.username_input.setText(self.user_obj.username)
            idx = self.role_combo.findText(self.user_obj.role)
            if idx >= 0: self.role_combo.setCurrentIndex(idx)
            self.status_combo.setCurrentText("Active" if self.user_obj.is_active else "Disabled")
            self.load_permissions_into_tree(self.user_obj.get_permissions())

        self.role_combo.currentIndexChanged.connect(self.on_role_changed)
        self.on_role_changed()

        # Buttons
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save User Profile")
        self.save_btn.clicked.connect(self.handle_save)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setProperty("class", "btn-secondary")
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

    def populate_permissions_tree(self):
        self.tree_items = {} # mod_key -> dict of action -> QTreeWidgetItem
        bold_font = QFont()
        bold_font.setBold(True)

        for cat_name, modules in MODULE_CATEGORIES.items():
            cat_item = QTreeWidgetItem(self.perm_tree, [cat_name])
            cat_item.setExpanded(True)
            cat_item.setFont(0, bold_font)
            cat_item.setForeground(0, QBrush(QColor('#818cf8')))
            cat_item.setBackground(0, QBrush(QColor('#1e1e38')))
            for i in range(1, 5):
                cat_item.setBackground(i, QBrush(QColor('#1e1e38')))

            for mod_key, mod_label, actions in modules:
                mod_item = QTreeWidgetItem(cat_item, [mod_label])
                mod_item.setData(0, Qt.UserRole, mod_key)
                mod_item.setForeground(0, QBrush(QColor('#f1f5f9')))

                item_actions = {}
                for col_idx, act in [(1, 'view'), (2, 'add'), (3, 'edit'), (4, 'delete')]:
                    if act in actions:
                        mod_item.setCheckState(col_idx, Qt.Unchecked)
                        item_actions[act] = col_idx
                    else:
                        mod_item.setText(col_idx, "-")
                        mod_item.setForeground(col_idx, QBrush(QColor('#64748b')))
                        mod_item.setTextAlignment(col_idx, Qt.AlignCenter)
                self.tree_items[mod_key] = (mod_item, item_actions)

    def on_role_changed(self):
        is_admin = self.role_combo.currentText() == "Administrator"
        # If Admin, check all and disable tree editing
        for mod_key, (mod_item, item_actions) in self.tree_items.items():
            for act, col_idx in item_actions.items():
                if is_admin:
                    mod_item.setCheckState(col_idx, Qt.Checked)
        self.perm_tree.setEnabled(not is_admin)

    def load_permissions_into_tree(self, perms):
        is_admin = self.role_combo.currentText() == "Administrator"
        for mod_key, (mod_item, item_actions) in self.tree_items.items():
            mod_perms = perms.get(mod_key, {})
            for act, col_idx in item_actions.items():
                checked = is_admin or mod_perms.get(act, False)
                mod_item.setCheckState(col_idx, Qt.Checked if checked else Qt.Unchecked)

    def get_permissions_from_tree(self):
        perms = {}
        for mod_key, (mod_item, item_actions) in self.tree_items.items():
            perms[mod_key] = {}
            for act, col_idx in item_actions.items():
                perms[mod_key][act] = (mod_item.checkState(col_idx) == Qt.Checked)
        return perms

    def handle_save(self):
        full_name = self.full_name_input.text().strip()
        username = self.username_input.text().strip()
        role = self.role_combo.currentText()
        is_active = (self.status_combo.currentText() == "Active")

        if not full_name or not username:
            QMessageBox.warning(self, "Validation Error", "Full Name and Login ID are required.")
            return

        session = Session()
        try:
            # Check self modification safety
            curr_user_id = self.current_user_data.get("id")
            if self.user_obj and self.user_obj.id == curr_user_id:
                if not is_active:
                    QMessageBox.warning(self, "Security Restriction", "You cannot disable your own active account.")
                    return
                if role != "Administrator":
                    QMessageBox.warning(self, "Security Restriction", "You cannot demote your own Administrator account.")
                    return

            # Check if attempting to demote or disable the last admin
            if self.user_obj and self.user_obj.role == "Administrator" and (role != "Administrator" or not is_active):
                admin_count = session.query(User).filter_by(role="Administrator", is_active=True).count()
                if admin_count <= 1:
                    QMessageBox.warning(self, "Security Restriction", "At least one active Administrator must exist in the system.")
                    return

            if not self.user_obj:
                # Check unique username
                existing = session.query(User).filter_by(username=username).first()
                if existing:
                    QMessageBox.warning(self, "Validation Error", f"Username '{username}' already exists.")
                    return

                pwd = self.password_input.text()
                conf = self.conf_password_input.text()
                if not pwd:
                    QMessageBox.warning(self, "Validation Error", "Password is required for new users.")
                    return
                if pwd != conf:
                    QMessageBox.warning(self, "Validation Error", "Passwords do not match.")
                    return

                user = User(
                    username=username,
                    password_hash=get_hash(pwd),
                    full_name=full_name,
                    role=role,
                    is_active=is_active,
                    created_at=datetime.datetime.now()
                )
                if role == "Administrator":
                    user.set_permissions(get_default_admin_permissions())
                else:
                    user.set_permissions(self.get_permissions_from_tree())
                session.add(user)
            else:
                user = session.query(User).get(self.user_obj.id)
                user.full_name = full_name
                user.role = role
                user.is_active = is_active
                if role == "Administrator":
                    user.set_permissions(get_default_admin_permissions())
                else:
                    user.set_permissions(self.get_permissions_from_tree())

            session.commit()
            QMessageBox.information(self, "Success", "User profile saved successfully.")
            self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save user profile: {e}")
        finally:
            session.close()


class UserManagementView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Top Toolbar
        top_bar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search users by name or username...")
        self.search_input.textChanged.connect(self.refresh_data)
        top_bar.addWidget(self.search_input, 3)

        self.add_btn = QPushButton("Add User Profile")
        self.add_btn.clicked.connect(self.add_user)
        top_bar.addWidget(self.add_btn, 1)

        self.edit_btn = QPushButton("Edit User Profile")
        self.edit_btn.setProperty("class", "btn-secondary")
        self.edit_btn.clicked.connect(self.edit_user)
        top_bar.addWidget(self.edit_btn, 1)

        self.reset_pass_btn = QPushButton("Reset Password")
        self.reset_pass_btn.setProperty("class", "btn-warning")
        self.reset_pass_btn.clicked.connect(self.reset_password)
        top_bar.addWidget(self.reset_pass_btn, 1)

        self.toggle_status_btn = QPushButton("Enable / Disable")
        self.toggle_status_btn.setProperty("class", "btn-secondary")
        self.toggle_status_btn.clicked.connect(self.toggle_user_status)
        top_bar.addWidget(self.toggle_status_btn, 1)

        self.delete_btn = QPushButton("Delete Profile")
        self.delete_btn.setProperty("class", "btn-danger")
        self.delete_btn.clicked.connect(self.delete_user)
        top_bar.addWidget(self.delete_btn, 1)

        layout.addLayout(top_bar)

        # Users Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID", "Full Name", "Login ID", "Role", "Status", "Last Login", "Created Date"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.doubleClicked.connect(self.edit_user)
        layout.addWidget(self.table)

    def refresh_data(self):
        search_txt = self.search_input.text().strip()
        session = Session()
        try:
            query = session.query(User)
            if search_txt:
                query = query.filter(
                    User.full_name.like(f"%{search_txt}%") |
                    User.username.like(f"%{search_txt}%")
                )
            users = query.all()

            self.table.setRowCount(len(users))
            for i, u in enumerate(users):
                self.table.setItem(i, 0, QTableWidgetItem(str(u.id)))
                self.table.setItem(i, 1, QTableWidgetItem(u.full_name or u.username))
                self.table.setItem(i, 2, QTableWidgetItem(u.username))
                self.table.setItem(i, 3, QTableWidgetItem(u.role))
                
                status_item = QTableWidgetItem("Active" if u.is_active else "Disabled")
                if not u.is_active:
                    status_item.setForeground(Qt.red)
                else:
                    status_item.setForeground(Qt.green)
                self.table.setItem(i, 4, status_item)

                last_login_str = u.last_login.strftime("%Y-%m-%d %H:%M:%S") if u.last_login else "Never"
                self.table.setItem(i, 5, QTableWidgetItem(last_login_str))

                created_str = u.created_at.strftime("%Y-%m-%d") if u.created_at else "N/A"
                self.table.setItem(i, 6, QTableWidgetItem(created_str))

        except Exception as e:
            print(f"Error loading users: {e}")
        finally:
            session.close()

    def get_selected_user_id(self):
        selected = self.table.selectedItems()
        if not selected:
            return None
        return int(self.table.item(selected[0].row(), 0).text())

    def get_current_user_data(self):
        main_win = self.window()
        if hasattr(main_win, 'user_data') and main_win.user_data:
            return main_win.user_data
        return {}

    def add_user(self):
        dlg = UserEditDialog(current_user_data=self.get_current_user_data(), parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_data()

    def edit_user(self):
        uid = self.get_selected_user_id()
        if uid is None:
            QMessageBox.information(self, "No Selection", "Please select a user to edit.")
            return

        session = Session()
        try:
            u = session.query(User).get(uid)
            if u:
                dlg = UserEditDialog(user_obj=u, current_user_data=self.get_current_user_data(), parent=self)
                if dlg.exec() == QDialog.Accepted:
                    self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load user profile: {e}")
        finally:
            session.close()

    def reset_password(self):
        uid = self.get_selected_user_id()
        if uid is None:
            QMessageBox.information(self, "No Selection", "Please select a user to reset password.")
            return

        session = Session()
        try:
            u = session.query(User).get(uid)
            if u:
                dlg = ResetPasswordDialog(username=u.username, parent=self)
                dlg.exec()
        finally:
            session.close()

    def toggle_user_status(self):
        uid = self.get_selected_user_id()
        if uid is None:
            QMessageBox.information(self, "No Selection", "Please select a user.")
            return

        curr_user = self.get_current_user_data()
        if curr_user.get("id") == uid:
            QMessageBox.warning(self, "Security Restriction", "You cannot disable your own active account.")
            return

        session = Session()
        try:
            u = session.query(User).get(uid)
            if u:
                if u.is_active and u.role == "Administrator":
                    admin_count = session.query(User).filter_by(role="Administrator", is_active=True).count()
                    if admin_count <= 1:
                        QMessageBox.warning(self, "Security Restriction", "At least one active Administrator must exist in the system.")
                        return

                u.is_active = not u.is_active
                session.commit()
                self.refresh_data()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to update status: {e}")
        finally:
            session.close()

    def delete_user(self):
        uid = self.get_selected_user_id()
        if uid is None:
            QMessageBox.information(self, "No Selection", "Please select a user to delete.")
            return

        curr_user = self.get_current_user_data()
        if curr_user.get("id") == uid:
            QMessageBox.warning(self, "Security Restriction", "You cannot delete your own logged-in account.")
            return

        session = Session()
        try:
            u = session.query(User).get(uid)
            if u:
                if u.role == "Administrator" and u.is_active:
                    admin_count = session.query(User).filter_by(role="Administrator", is_active=True).count()
                    if admin_count <= 1:
                        QMessageBox.warning(self, "Security Restriction", "At least one active Administrator must exist in the system.")
                        return

                confirm = QMessageBox.question(
                    self, "Confirm Delete User",
                    f"Are you sure you want to permanently delete user '{u.username}' ({u.full_name})?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if confirm == QMessageBox.Yes:
                    session.delete(u)
                    session.commit()
                    self.refresh_data()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to delete user: {e}")
        finally:
            session.close()
