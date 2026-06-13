import sys
import builtins

# Save original import function to bypass PySide6 shibokensupport global import hook
_original_import = builtins.__import__

from PySide6.QtWidgets import QApplication

# Restore original import function
builtins.__import__ = _original_import

from database import init_db
from styles import GLOBAL_STYLE
from ui.login_window import LoginWindow
from ui.main_window import MainWindow

def main():
    # 1. Run GUI App
    app = QApplication(sys.argv)
    
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
    elif status == "expired":
        # Trial expired - require activation
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

    # 4. Authenticate User
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
