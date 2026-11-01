import os
import sys
import builtins

# Save original import function to bypass PySide6 shibokensupport global import hook
_original_import = builtins.__import__

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

# Restore original import function
builtins.__import__ = _original_import

from database import init_db
from styles import GLOBAL_STYLE
from ui.login_window import LoginWindow
from ui.main_window import MainWindow
from utils.ui_helpers import setup_global_enter_navigation

def main():
    # Ensure current working directory is the application directory when running as an executable
    if getattr(sys, 'frozen', False):
        os.chdir(os.path.dirname(sys.executable))

    # 1. Run GUI App
    app = QApplication(sys.argv)
    setup_global_enter_navigation(app)
    
    # Set application icon (supports PyInstaller onefile temp dir and local dev)
    icon_path = os.path.join(getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__))), "icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Apply modern custom stylesheet globally
    app.setStyleSheet(GLOBAL_STYLE)

    # 2. Offline Licensing and Activation Checks
    from licensing import manager
    from licensing.ui_activation import TrialStatusDialog, ActivationDialog
    from PySide6.QtWidgets import QDialog

    lic_status = manager.check_license_status()
    status = lic_status["status"]

    if status == "tampered":
        # System blocked due to date rollback or file tampering
        dlg = ActivationDialog(is_blocked=True, block_msg=lic_status["message"])
        dlg.exec()
        sys.exit(0)
    elif status in ("expired", "unactivated"):
        # Activation required
        dlg = ActivationDialog(is_blocked=False, block_msg=lic_status["message"])
        if dlg.exec() != QDialog.Accepted:
            sys.exit(0)
    elif status == "trial":
        # Active trial - show remaining days warning
        days = lic_status["days_remaining"]
        dlg = TrialStatusDialog(days_remaining=days)
        if dlg.exec() != QDialog.Accepted:
            sys.exit(0)
    elif status == "active":
        # Permanently activated - proceed quietly
        pass

    # 3. Initialize DB Schema and Seed Records (only if licensed/trial)
    init_db()
    # Apply persisted theme color if configured
    try:
        from database import Session, Setting
        from styles import get_theme_stylesheet
        _db_sess = Session()
        _theme_set = _db_sess.query(Setting).filter_by(key='theme_color').first()
        if _theme_set and _theme_set.value:
            app.setStyleSheet(get_theme_stylesheet(_theme_set.value))
        _db_sess.close()
    except Exception:
        pass

    # 4. Authenticate User
    login = LoginWindow()
    if login.exec() == LoginWindow.Accepted:
        # Successful login, spin up dashboard main window
        user_data = login.user_data
        try:
            window = MainWindow(user_data=user_data)
            window.showMaximized()
            sys.exit(app.exec())
        except Exception as e:
            import traceback
            traceback.print_exc()
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(None, "Application Startup Error", f"An unexpected error occurred while loading the main window:\n\n{e}")
            sys.exit(1)
    else:
        # User closed login dialog
        sys.exit(0)

if __name__ == "__main__":
    main()
