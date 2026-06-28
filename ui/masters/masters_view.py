from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from PySide6.QtCore import Qt

from ui.masters.products import ProductsView
from ui.masters.customers import CustomersView
from ui.masters.suppliers import SuppliersView
from ui.masters.bank_accounts import BankAccountsView

class MastersView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Tab Widget for Master Modules
        self.tabs = QTabWidget()
        self.tabs.setObjectName("masters_tab_widget")

        # Instantiate Master Sub-Views
        self.products_view = ProductsView(self)
        self.customers_view = CustomersView(self)
        self.suppliers_view = SuppliersView(self)
        self.bank_accounts_view = BankAccountsView(self)

        # Add tabs
        self.tabs.addTab(self.products_view, "📦 Products Master (Ctrl+Shift+P)")
        self.tabs.addTab(self.customers_view, "👤 Customers Master (Ctrl+Shift+C)")
        self.tabs.addTab(self.suppliers_view, "🚛 Suppliers Master (Ctrl+Shift+S)")
        self.tabs.addTab(self.bank_accounts_view, "🏦 Bank Accounts Master (Ctrl+Shift+B)")

        self.tabs.setTabToolTip(0, "Products Master (Ctrl+Shift+P / Ctrl+Alt+1)")
        self.tabs.setTabToolTip(1, "Customers Master (Ctrl+Shift+C / Ctrl+Alt+2)")
        self.tabs.setTabToolTip(2, "Suppliers Master (Ctrl+Shift+S / Ctrl+Alt+3)")
        self.tabs.setTabToolTip(3, "Bank Accounts Master (Ctrl+Shift+B / Ctrl+Alt+4)")

        # Connect tab change signal
        self.tabs.currentChanged.connect(self.on_tab_changed)

        layout.addWidget(self.tabs)

    def on_tab_changed(self, index):
        widget = self.tabs.widget(index)
        if hasattr(widget, "refresh_data"):
            widget.refresh_data()

    def refresh_data(self):
        widget = self.tabs.currentWidget()
        if hasattr(widget, "refresh_data"):
            widget.refresh_data()

    def set_active_tab(self, index):
        if 0 <= index < self.tabs.count():
            self.tabs.setCurrentIndex(index)
            self.refresh_data()
