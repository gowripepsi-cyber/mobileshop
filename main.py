import sys
import pandas as pd  # Pre-load pandas to bypass PySide6 shibokensupport six.moves import hook crash
from PySide6.QtWidgets import QApplication
from database import init_db
from styles import GLOBAL_STYLE
from ui.login_window import LoginWindow
from ui.main_window import MainWindow

def main():
    # 1. Initialize DB Schema and Seed Records
    init_db()

    # 2. Run GUI App
    app = QApplication(sys.argv)
    
    # Apply modern custom stylesheet globally
    app.setStyleSheet(GLOBAL_STYLE)

    # 3. Authenticate User
    login = LoginWindow()
    if login.exec() == LoginWindow.Accepted:
        # Successful login, spin up dashboard main window
        user_data = login.user_data
        window = MainWindow(user_data=user_data)
        window.showMaximized()
        sys.exit(app.exec())
    else:
        # User closed login dialog
        sys.exit(0)

if __name__ == "__main__":
    main()
