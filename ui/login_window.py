from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QMessageBox, QCheckBox)
from PySide6.QtCore import Qt, QTimer, QEvent
from database import Session, User, get_hash, Setting
from utils.ui_helpers import setup_password_toggle

class LoginWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Login - SUN INVENTORY & SERVICE LITE")
        self.setFixedSize(484, 400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.user_data = None
        self.init_ui()
        self.load_remembered_credentials()

    def init_ui(self):
        # Main Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 35, 30, 35)
        layout.setSpacing(12)

        # Title Label
        title_label = QLabel("SUN INVENTORY & SERVICE LITE")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #6366f1; letter-spacing: 1px;")
        layout.addWidget(title_label)

        # Subtitle
        sub_label = QLabel("Management System Login")
        sub_label.setAlignment(Qt.AlignCenter)
        sub_label.setStyleSheet("font-size: 13px; color: #94a3b8; margin-bottom: 10px;")
        layout.addWidget(sub_label)

        # Username Input
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.username_input.setFixedHeight(40)
        self.username_input._skip_enter_nav = True
        self.username_input.returnPressed.connect(self.handle_username_return)
        layout.addWidget(self.username_input)

        # Password Input
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFixedHeight(40)
        setup_password_toggle(self.password_input)
        self.password_input._skip_enter_nav = True
        self.password_input.returnPressed.connect(self.handle_password_return)
        layout.addWidget(self.password_input)

        # Remember Login Credentials Checkbox
        self.remember_cb = QCheckBox("Remember login credentials")
        self.remember_cb.setCursor(Qt.PointingHandCursor)
        self.remember_cb.setStyleSheet("""
            QCheckBox {
                color: #94a3b8;
                font-size: 13px;
                padding-top: 2px;
                padding-bottom: 2px;
            }
            QCheckBox:hover {
                color: #e2e8f0;
            }
            QCheckBox::indicator {
                width: 17px;
                height: 17px;
                border-radius: 4px;
                border: 1px solid #3b3b54;
                background-color: #141426;
            }
            QCheckBox::indicator:hover {
                border-color: #6366f1;
            }
            QCheckBox::indicator:checked {
                background-color: #6366f1;
                border-color: #6366f1;
            }
        """)
        layout.addWidget(self.remember_cb)

        # Error label
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #ef4444; font-size: 12px;")
        self.error_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.error_label)

        # Login Button
        self.login_btn = QPushButton("Log In")
        self.login_btn.setFixedHeight(42)
        self.login_btn.setDefault(True)
        self.login_btn.setAutoDefault(True)
        self.login_btn.clicked.connect(self.handle_login)
        layout.addWidget(self.login_btn)

        # Tab Order
        self.setTabOrder(self.username_input, self.password_input)
        self.setTabOrder(self.password_input, self.remember_cb)
        self.setTabOrder(self.remember_cb, self.login_btn)

        # Intercept Enter on remember_cb to advance to login_btn
        self.remember_cb.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj == self.remember_cb and event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.login_btn.setFocus()
            return True
        return super().eventFilter(obj, event)

    def handle_username_return(self):
        self.password_input.setFocus()
        self.password_input.selectAll()

    def handle_password_return(self):
        self.login_btn.setFocus()

    def load_remembered_credentials(self):
        session = Session()
        try:
            rem_setting = session.query(Setting).filter_by(key='remember_credentials').first()
            if rem_setting and rem_setting.value == 'true':
                self.remember_cb.setChecked(True)
                user_setting = session.query(Setting).filter_by(key='remembered_username').first()
                pass_setting = session.query(Setting).filter_by(key='remembered_password').first()
                if user_setting and user_setting.value:
                    self.username_input.setText(user_setting.value)
                if pass_setting and pass_setting.value:
                    self.password_input.setText(pass_setting.value)

                if self.username_input.text() and self.password_input.text():
                    QTimer.singleShot(0, self.login_btn.setFocus)
                elif self.username_input.text():
                    QTimer.singleShot(0, self.password_input.setFocus)
        except Exception as e:
            print(f"Error loading remembered credentials: {e}")
        finally:
            session.close()

    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            self.error_label.setText("Please enter both username and password.")
            return

        session = Session()
        try:
            import datetime
            hashed_pwd = get_hash(password)
            user = session.query(User).filter_by(username=username, password_hash=hashed_pwd).first()
            if user:
                if not user.is_active:
                    self.error_label.setText("Your account has been disabled. Please contact an administrator.")
                    return

                user.last_login = datetime.datetime.now()

                # Save or clear remembered credentials based on checkbox
                self._save_credentials_setting(session, username, password)

                session.commit()

                self.user_data = {
                    "id": user.id,
                    "username": user.username,
                    "full_name": user.full_name or user.username,
                    "role": user.role,
                    "permissions": user.get_permissions()
                }
                self.accept()
            else:
                self.error_label.setText("Invalid username or password.")
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"An error occurred: {e}")
        finally:
            session.close()

    def _save_credentials_setting(self, session, username, password):
        def set_val(k, v):
            s = session.query(Setting).filter_by(key=k).first()
            if not s:
                s = Setting(key=k, value=v)
                session.add(s)
            else:
                s.value = v

        if self.remember_cb.isChecked():
            set_val('remember_credentials', 'true')
            set_val('remembered_username', username)
            set_val('remembered_password', password)
        else:
            set_val('remember_credentials', 'false')
            set_val('remembered_username', '')
            set_val('remembered_password', '')
