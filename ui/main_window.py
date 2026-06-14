from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QStackedWidget, QMessageBox, QSpacerItem, QSizePolicy
from PySide6.QtCore import Qt, QSize, QTimer

# Import views
from ui.dashboard import DashboardView
from ui.masters.products import ProductsView
from ui.masters.customers import CustomersView
from ui.masters.suppliers import SuppliersView
from ui.masters.bank_accounts import BankAccountsView
from ui.inventory.purchase import PurchaseView
from ui.sales.sales import SalesView
from ui.services.jobs import ServicesView
from ui.payments.payments import PaymentsView
from ui.reports.reports import ReportsView
from ui.settings.settings import SettingsView
from ui.money_transfer import MoneyTransferView

class MainWindow(QMainWindow):
    def __init__(self, user_data, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.setWindowTitle("Mobile Shop Management System")
        self.setMinimumSize(1200, 750)
        self.init_ui()
        QTimer.singleShot(100, self.check_low_stock_alert)

    def init_ui(self):
        # Central widget and horizontal layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Sidebar Setup
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # Shop Logo / Title
        self.logo_label = QLabel("GALAXY MOBILES")
        self.logo_label.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(self.logo_label)
        self.update_shop_name()

        # Navigation buttons mapping and shortcuts
        self.nav_buttons = {}
        nav_items = [
            ("Dashboard", 0),
            ("Products", 1),
            ("Customers", 2),
            ("Suppliers", 3),
            ("Bank Accounts", 4),
            ("Purchase Entry", 5),
            ("Sales Invoice", 6),
            ("Service Cards", 7),
            ("Payments", 8),
            ("Reports", 9),
            ("Settings", 10),
            ("UPI / Money Transfer", 11),
        ]

        # Map index to shortcut key
        shortcuts = {
            0: "Ctrl+1",
            1: "Ctrl+2",
            2: "Ctrl+3",
            3: "Ctrl+4",
            4: "Ctrl+5",
            5: "Ctrl+6",
            6: "Ctrl+7",
            7: "Ctrl+8",
            8: "Ctrl+9",
            9: "Ctrl+0",
            10: "Ctrl+,",
            11: "Ctrl+Shift+M"
        }

        for text, index in nav_items:
            shortcut_key = shortcuts.get(index)
            btn = QPushButton()
            btn.setCheckable(True)
            
            # Create horizontal layout inside the button to align title and shortcut
            btn_layout = QHBoxLayout(btn)
            btn_layout.setContentsMargins(15, 0, 15, 0)
            btn_layout.setSpacing(8)
            
            # Title Label (left side)
            lbl_text = QLabel(text)
            lbl_text.setObjectName("btn_label")
            lbl_text.setAttribute(Qt.WA_TransparentForMouseEvents)
            btn_layout.addWidget(lbl_text)
            
            # Stretch spacer to push shortcut label to the right
            btn_layout.addStretch()
            
            # Shortcut Badge (right side)
            if shortcut_key:
                btn.setShortcut(shortcut_key)
                btn.setToolTip(f"{text} ({shortcut_key})")
                
                lbl_shortcut = QLabel(shortcut_key)
                lbl_shortcut.setObjectName("shortcut_label")
                lbl_shortcut.setAttribute(Qt.WA_TransparentForMouseEvents)
                btn_layout.addWidget(lbl_shortcut)
                
            btn.clicked.connect(lambda checked, idx=index: self.switch_view(idx))
            sidebar_layout.addWidget(btn)
            self.nav_buttons[index] = btn

        # Spacer to push logout button to bottom
        sidebar_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Logout Button
        self.logout_btn = QPushButton("Log Out")
        self.logout_btn.setObjectName("logout_btn")
        self.logout_btn.setStyleSheet("color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.2); margin-bottom: 20px;")
        self.logout_btn.clicked.connect(self.handle_logout)
        sidebar_layout.addWidget(self.logout_btn)

        main_layout.addWidget(sidebar)

        # 2. Main Content Wrapper
        content_wrapper = QWidget()
        content_wrapper_layout = QVBoxLayout(content_wrapper)
        content_wrapper_layout.setContentsMargins(0, 0, 0, 0)
        content_wrapper_layout.setSpacing(0)

        # Header Area
        header = QWidget()
        header.setObjectName("header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)

        self.header_title = QLabel("Dashboard")
        header_layout.addWidget(self.header_title)

        header_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        user_info = QLabel(f"Welcome, {self.user_data['username']} ({self.user_data['role']})")
        user_info.setStyleSheet("color: #94a3b8; font-size: 13px; font-weight: 500;")
        header_layout.addWidget(user_info)

        content_wrapper_layout.addWidget(header)

        # Main Stacked Widget
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setObjectName("content_area")

        # Instantiate all Views
        self.dashboard_view = DashboardView(self)
        self.products_view = ProductsView(self)
        self.customers_view = CustomersView(self)
        self.suppliers_view = SuppliersView(self)
        self.bank_accounts_view = BankAccountsView(self)
        self.purchase_view = PurchaseView(self)
        self.sales_view = SalesView(self)
        self.services_view = ServicesView(self)
        self.payments_view = PaymentsView(self)
        self.reports_view = ReportsView(self)
        self.settings_view = SettingsView(self)
        self.money_transfer_view = MoneyTransferView(self)

        # Add Views to Stacked Widget in order
        self.stacked_widget.addWidget(self.dashboard_view)      # 0
        self.stacked_widget.addWidget(self.products_view)       # 1
        self.stacked_widget.addWidget(self.customers_view)      # 2
        self.stacked_widget.addWidget(self.suppliers_view)      # 3
        self.stacked_widget.addWidget(self.bank_accounts_view)   # 4
        self.stacked_widget.addWidget(self.purchase_view)       # 5
        self.stacked_widget.addWidget(self.sales_view)          # 6
        self.stacked_widget.addWidget(self.services_view)       # 7
        self.stacked_widget.addWidget(self.payments_view)       # 8
        self.stacked_widget.addWidget(self.reports_view)        # 9
        self.stacked_widget.addWidget(self.settings_view)       # 10
        self.stacked_widget.addWidget(self.money_transfer_view)  # 11

        content_wrapper_layout.addWidget(self.stacked_widget)
        main_layout.addWidget(content_wrapper)

        # Set default view
        self.switch_view(0)

    def update_shop_name(self):
        from database import Session, Setting
        session = Session()
        try:
            shop_name_setting = session.query(Setting).filter_by(key='shop_name').first()
            name = shop_name_setting.value.upper() if shop_name_setting else "GALAXY MOBILES"
            self.logo_label.setText(name)
        except Exception:
            self.logo_label.setText("GALAXY MOBILES")
        finally:
            session.close()

    def switch_view(self, index):
        # Check corresponding nav button
        for idx, btn in self.nav_buttons.items():
            btn.setChecked(idx == index)

        self.stacked_widget.setCurrentIndex(index)
        
        # Update Header Title
        title_map = {
            0: "Dashboard",
            1: "Products Master",
            2: "Customers Master",
            3: "Suppliers Master",
            4: "Bank Accounts Master",
            5: "Purchase Entry (Inventory)",
            6: "Sales Invoice",
            7: "Repair Center Job Cards",
            8: "Payments Ledger",
            9: "Reports & Financial Analysis",
            10: "System Settings & Database Admin",
            11: "UPI / Money Transfer"
        }
        self.header_title.setText(title_map.get(index, "Mobile Shop"))

        # Refresh the view data when selected
        widget = self.stacked_widget.widget(index)
        if hasattr(widget, "refresh_data"):
            widget.refresh_data()

    def handle_logout(self):
        confirm = QMessageBox.question(
            self, "Confirm Logout", "Are you sure you want to log out?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.close()

    def check_low_stock_alert(self, manual=False):
        from database import Session
        from models import Product
        session = Session()
        try:
            low_stock_products = session.query(Product).filter(Product.stock_qty <= Product.low_stock_limit).all()
            if low_stock_products:
                msg = "The following items are low in stock:\n\n"
                for p in low_stock_products:
                    status = "OUT OF STOCK" if p.stock_qty == 0 else f"Qty: {p.stock_qty} (Limit: {p.low_stock_limit})"
                    msg += f"• {p.name} ({p.brand} {p.model}) - {status}\n"
                
                QMessageBox.warning(
                    self,
                    "Low Stock Alert",
                    msg
                )
            elif manual:
                QMessageBox.information(
                    self,
                    "Low Stock Alert",
                    "All products are well stocked!\n(No items below their individual low stock limits)."
                )
        except Exception as e:
            print(f"Error checking low stock alert: {e}")
        finally:
            session.close()
