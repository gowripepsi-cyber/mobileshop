from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from PySide6.QtCore import Qt

from ui.masters.products import ProductsView
from ui.masters.categories import CategoriesView
from ui.masters.customers import CustomersView
from ui.masters.suppliers import SuppliersView
from ui.masters.units import UnitsView

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
        self.categories_view = CategoriesView(self)
        self.customers_view = CustomersView(self)
        self.suppliers_view = SuppliersView(self)
        self.units_view = UnitsView(self)

        # Add tabs
        self.tabs.addTab(self.products_view, "📦 Products (Ctrl+Shift+P)")
        self.tabs.addTab(self.categories_view, "📁 Item Categories (Ctrl+Shift+K)")
        self.tabs.addTab(self.customers_view, "👤 Customer (Ctrl+Shift+C)")
        self.tabs.addTab(self.suppliers_view, "🚛 Supplier (Ctrl+Shift+S)")
        self.tabs.addTab(self.units_view, "📏 Units (Ctrl+Shift+U)")

        self.tabs.setTabToolTip(0, "Products (Ctrl+Shift+P / Ctrl+Alt+1)")
        self.tabs.setTabToolTip(1, "Item Categories (Ctrl+Shift+K / Ctrl+Alt+2)")
        self.tabs.setTabToolTip(2, "Customer (Ctrl+Shift+C / Ctrl+Alt+3)")
        self.tabs.setTabToolTip(3, "Supplier (Ctrl+Shift+S / Ctrl+Alt+4)")
        self.tabs.setTabToolTip(4, "Units (Ctrl+Shift+U / Ctrl+Alt+5)")

        # Connect tab change signal
        self.tabs.currentChanged.connect(self.on_tab_changed)

        layout.addWidget(self.tabs)

    def trigger_add_action(self):
        current_widget = self.tabs.currentWidget()
        if current_widget == self.products_view:
            self.products_view.add_product()
        elif current_widget == self.categories_view:
            self.categories_view.add_category()
        elif current_widget == self.customers_view:
            self.customers_view.add_customer()
        elif current_widget == self.suppliers_view:
            self.suppliers_view.add_supplier()
        elif current_widget == self.units_view:
            self.units_view.add_unit()

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

    def retranslate_ui(self):
        from utils.translator import tr
        self.tabs.setTabText(0, f"📦 {tr('Products')} (Ctrl+Shift+P)")
        self.tabs.setTabText(1, f"📁 {tr('Item Categories')} (Ctrl+Shift+K)")
        self.tabs.setTabText(2, f"👤 {tr('Customer')} (Ctrl+Shift+C)")
        self.tabs.setTabText(3, f"🚛 {tr('Supplier')} (Ctrl+Shift+S)")
        self.tabs.setTabText(4, f"📏 {tr('Units')} (Ctrl+Shift+U)")
        self.tabs.setTabToolTip(0, f"{tr('Products')} (Ctrl+Shift+P / Ctrl+Alt+1)")
        self.tabs.setTabToolTip(1, f"{tr('Item Categories')} (Ctrl+Shift+K / Ctrl+Alt+2)")
        self.tabs.setTabToolTip(2, f"{tr('Customer')} (Ctrl+Shift+C / Ctrl+Alt+3)")
        self.tabs.setTabToolTip(3, f"{tr('Supplier')} (Ctrl+Shift+S / Ctrl+Alt+4)")
        self.tabs.setTabToolTip(4, f"{tr('Units')} (Ctrl+Shift+U / Ctrl+Alt+5)")
        # Forward to children if they implement retranslate_ui
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if hasattr(w, 'retranslate_ui'):
                w.retranslate_ui()
