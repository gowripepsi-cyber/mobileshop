import sys
import os

# Add parent directory to sys.path to allow imports from root modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PySide6.QtWidgets import QApplication, QDialog

from styles import GLOBAL_STYLE
from licensing.ui_activation import VendorLoginDialog, VendorGeneratorDialog

def main():
    app = QApplication(sys.argv)
    
    # Apply global mobile shop styling to vendor tool
    app.setStyleSheet(GLOBAL_STYLE)
    
    # 1. Require vendor login
    login_dlg = VendorLoginDialog()
    if login_dlg.exec() == QDialog.Accepted:
        # 2. Open Vendor License Generator Panel
        gen_dlg = VendorGeneratorDialog()
        gen_dlg.show()
        sys.exit(app.exec())
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
