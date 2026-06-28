from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QWidget
from PySide6.QtCore import Qt
from database import Session, User, get_hash, Setting

class LoginWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Login - SUN INVENTORY & SERVICE LITE")
        self.setFixedSize(484, 350)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.user_data = None
        self.init_ui()

    def init_ui(self):
        # Main Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 40, 30, 40)
        layout.setSpacing(15)

        # Title Label
        title_label = QLabel("SUN INVENTORY & SERVICE LITE")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #6366f1; letter-spacing: 1px;")
        layout.addWidget(title_label)

        # Subtitle
        sub_label = QLabel("Management System Login")
        sub_label.setAlignment(Qt.AlignCenter)
        sub_label.setStyleSheet("font-size: 13px; color: #94a3b8; margin-bottom: 15px;")
        layout.addWidget(sub_label)

        # Username Input
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.username_input.setFixedHeight(40)
        layout.addWidget(self.username_input)

        # Password Input
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFixedHeight(40)
        layout.addWidget(self.password_input)

        # Error label
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #ef4444; font-size: 12px;")
        self.error_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.error_label)

        # Login Button
        self.login_btn = QPushButton("Log In")
        self.login_btn.setFixedHeight(42)
        self.login_btn.clicked.connect(self.handle_login)
        layout.addWidget(self.login_btn)

        # Trigger login on return key
        self.username_input.returnPressed.connect(self.handle_login)
        self.password_input.returnPressed.connect(self.handle_login)

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
