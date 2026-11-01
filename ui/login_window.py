import datetime
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QMessageBox, QCheckBox, QFrame, QGraphicsDropShadowEffect)
from PySide6.QtCore import Qt, QTimer, QEvent
from PySide6.QtGui import QColor
from database import Session, User, get_hash, Setting
from utils.ui_helpers import setup_password_toggle

class LoginWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Login - SUN INVENTORY & SERVICE LITE")
        self.setFixedSize(510, 440)
        # Frameless window without native OS top title bar & transparent background for true rounded corners
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.user_data = None
        self._drag_pos = None

        self.init_ui()
        self.load_remembered_credentials()

    def get_theme_color(self):
        session = Session()
        try:
            t = session.query(Setting).filter_by(key='theme_color').first()
            if t and t.value:
                return t.value
        except Exception:
            pass
        finally:
            session.close()
        return "#8fd53b"

    def init_ui(self):
        theme_hex = self.get_theme_color()
        c = QColor(theme_hex)
        if not c.isValid():
            c = QColor("#8fd53b")
        theme_hex = c.name()
        hover_hex = c.darker(110).name()
        lum = (0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()) / 255.0
        btn_text_color = "#0f172a" if lum > 0.55 else "#ffffff"

        # Outer Layout with margins to allow drop shadow and smooth anti-aliased rounded corners
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(10, 10, 10, 10)

        # Rounded Capsule Card Container
        self.card = QFrame(self)
        self.card.setObjectName("login_card")
        self.card.setStyleSheet(f"""
            QFrame#login_card {{
                background-color: #ffffff;
                border: 2px solid {theme_hex};
                border-radius: 24px;
            }}
        """)

        # Soft drop shadow for floating modal aesthetic
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 45))
        shadow.setOffset(0, 4)
        self.card.setGraphicsEffect(shadow)

        # Inner Card Layout
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(28, 14, 28, 26)
        card_layout.setSpacing(10)

        # Top Bar with Close Button
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        top_bar.addStretch()

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(28, 28)
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setToolTip("Close / மூடு (Esc)")
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #94a3b8;
                font-size: 14px;
                font-weight: bold;
                border: none;
                border-radius: 14px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #fee2e2;
                color: #ef4444;
            }
        """)
        self.close_btn.clicked.connect(self.reject)
        top_bar.addWidget(self.close_btn)
        card_layout.addLayout(top_bar)

        # Title Label
        title_label = QLabel("SUN INVENTORY & SERVICE LITE")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 21px; font-weight: 800; color: #142b05; letter-spacing: 0.5px;")
        card_layout.addWidget(title_label)

        # Subtitle
        sub_label = QLabel("Management System Login")
        sub_label.setAlignment(Qt.AlignCenter)
        sub_label.setStyleSheet("font-size: 13px; color: #64748b; margin-bottom: 6px;")
        card_layout.addWidget(sub_label)

        # Username Input
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.username_input.setFixedHeight(40)
        self.username_input._skip_enter_nav = True
        self.username_input.returnPressed.connect(self.handle_username_return)
        card_layout.addWidget(self.username_input)

        # Password Input
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFixedHeight(40)
        setup_password_toggle(self.password_input)
        self.password_input._skip_enter_nav = True
        self.password_input.returnPressed.connect(self.handle_password_return)
        card_layout.addWidget(self.password_input)

        # Remember Login Credentials Checkbox
        self.remember_cb = QCheckBox("Remember login credentials")
        self.remember_cb.setCursor(Qt.PointingHandCursor)
        self.remember_cb.setStyleSheet(f"""
            QCheckBox {{
                color: #475569;
                font-size: 13px;
                padding-top: 2px;
                padding-bottom: 2px;
            }}
            QCheckBox:hover {{
                color: #0f172a;
            }}
            QCheckBox::indicator {{
                width: 17px;
                height: 17px;
                border-radius: 4px;
                border: 1.5px solid #cbd5e1;
                background-color: #ffffff;
            }}
            QCheckBox::indicator:hover {{
                border-color: {theme_hex};
                background-color: rgba({c.red()}, {c.green()}, {c.blue()}, 0.08);
            }}
            QCheckBox::indicator:checked {{
                background-color: {theme_hex};
                border-color: {hover_hex};
            }}
        """)
        card_layout.addWidget(self.remember_cb)

        # Error label
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #ef4444; font-size: 12px;")
        self.error_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(self.error_label)

        # Login Button
        self.login_btn = QPushButton("Log In")
        self.login_btn.setFixedHeight(42)
        self.login_btn.setDefault(True)
        self.login_btn.setAutoDefault(True)
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme_hex};
                color: {btn_text_color};
                font-weight: bold;
                font-size: 14px;
                border: none;
                border-radius: 12px;
            }}
            QPushButton:hover {{
                background-color: {hover_hex};
            }}
        """)
        self.login_btn.clicked.connect(self.handle_login)
        card_layout.addWidget(self.login_btn)

        outer_layout.addWidget(self.card)

        # Tab Order
        self.setTabOrder(self.username_input, self.password_input)
        self.setTabOrder(self.password_input, self.remember_cb)
        self.setTabOrder(self.remember_cb, self.login_btn)

        # Intercept Enter on remember_cb to advance to login_btn
        self.remember_cb.installEventFilter(self)

    # Window Dragging for Frameless Dialog
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()

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
