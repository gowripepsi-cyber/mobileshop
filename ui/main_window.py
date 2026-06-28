from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QStackedWidget, QMessageBox, QSpacerItem, QSizePolicy
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QShortcut, QKeySequence
from functools import partial

# Import views
from ui.dashboard import DashboardView
from ui.masters.masters_view import MastersView
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
        self.setWindowTitle("Inventory & Accounting Management System")
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
        self.logo_label = QLabel("SUN COMPUTERS,")
        self.logo_label.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(self.logo_label)
        self.update_shop_name()

        # Navigation buttons mapping and shortcuts
        self.nav_buttons = {}
        nav_items = [
            ("Dashboard", 0),
            ("Master Records", 1),
            ("Purchase Entry", 2),
            ("Sales Invoice", 3),
            ("Service Cards", 4),
            ("Payments", 5),
            ("Reports", 6),
            ("Settings", 7),
            ("UPI / Money Transfer", 8),
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
            7: "Ctrl+,",
            8: "Ctrl+Shift+M"
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
        self.masters_view = MastersView(self)
        self.products_view = self.masters_view.products_view
        self.customers_view = self.masters_view.customers_view
        self.suppliers_view = self.masters_view.suppliers_view
        self.bank_accounts_view = self.masters_view.bank_accounts_view
        self.purchase_view = PurchaseView(self)
        self.sales_view = SalesView(self)
        self.services_view = ServicesView(self)
        self.payments_view = PaymentsView(self)
        self.reports_view = ReportsView(self)
        self.settings_view = SettingsView(self)
        self.money_transfer_view = MoneyTransferView(self)

        # Add Views to Stacked Widget in order
        self.stacked_widget.addWidget(self.dashboard_view)      # 0
        self.stacked_widget.addWidget(self.masters_view)        # 1
        self.stacked_widget.addWidget(self.purchase_view)       # 2
        self.stacked_widget.addWidget(self.sales_view)          # 3
        self.stacked_widget.addWidget(self.services_view)       # 4
        self.stacked_widget.addWidget(self.payments_view)       # 5
        self.stacked_widget.addWidget(self.reports_view)        # 6
        self.stacked_widget.addWidget(self.settings_view)       # 7
        self.stacked_widget.addWidget(self.money_transfer_view)  # 8

        content_wrapper_layout.addWidget(self.stacked_widget)
        main_layout.addWidget(content_wrapper)

        # Setup master record sub-tab shortcuts
        master_shortcuts = [
            ("Ctrl+Shift+P", 0),
            ("Ctrl+Alt+1", 0),
            ("Ctrl+Shift+C", 1),
            ("Ctrl+Alt+2", 1),
            ("Ctrl+Shift+S", 2),
            ("Ctrl+Alt+3", 2),
            ("Ctrl+Shift+B", 3),
            ("Ctrl+Alt+4", 3),
        ]
        for key, tab_idx in master_shortcuts:
            sc = QShortcut(QKeySequence(key), self)
            sc.activated.connect(partial(self.open_master_tab, tab_idx))

        # Setup universal Add shortcut (Ctrl+N) for master records
        self.universal_add_shortcut = QShortcut(QKeySequence("Ctrl+N"), self)
        self.universal_add_shortcut.activated.connect(self.handle_universal_add)

        # Set default view
        self.apply_feature_settings()
        self.switch_view(0)

    def update_shop_name(self):
        from database import Session, Setting
        session = Session()
        try:
            shop_name_setting = session.query(Setting).filter_by(key='shop_name').first()
            name = shop_name_setting.value.upper() if shop_name_setting else "SUN COMPUTERS,"
            self.logo_label.setText(name)
        except Exception:
            self.logo_label.setText("SUN COMPUTERS,")
        finally:
            session.close()

    def switch_view(self, index):
        # Prevent switching to hidden sidebar buttons (via shortcuts)
        if index in self.nav_buttons and not self.nav_buttons[index].isVisible():
            return

        # Check corresponding nav button
        for idx, btn in self.nav_buttons.items():
            btn.setChecked(idx == index)

        self.stacked_widget.setCurrentIndex(index)
        
        # Update Header Title
        title_map = {
            0: "Dashboard",
            1: "Master Records",
            2: "Purchase Entry (Inventory)",
            3: "Sales Invoice",
            4: "Repair Center Job Cards",
            5: "Payments Ledger",
            6: "Reports & Financial Analysis",
            7: "System Settings & Database Admin",
            8: "UPI / Money Transfer"
        }
        self.header_title.setText(title_map.get(index, "Inventory & Accounting"))

        # Refresh the view data when selected
        widget = self.stacked_widget.widget(index)
        if hasattr(widget, "refresh_data"):
            widget.refresh_data()

        from utils.permissions import enforce_ui_permissions
        enforce_ui_permissions(self)

    def open_master_tab(self, tab_index):
        self.switch_view(1)
        if hasattr(self, 'masters_view'):
            self.masters_view.set_active_tab(tab_index)

    def handle_universal_add(self):
        self.switch_view(1)
        if hasattr(self, 'masters_view'):
            self.masters_view.trigger_add_action()

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

    def apply_feature_settings(self):
        from database import Session, Setting
        session = Session()
        enable_repair = True
        enable_money = True
        try:
            r_val = session.query(Setting).filter_by(key='enable_repair_service').first()
            if r_val and r_val.value == 'false':
                enable_repair = False
            m_val = session.query(Setting).filter_by(key='enable_money_transfer').first()
            if m_val and m_val.value == 'false':
                enable_money = False
        except Exception as e:
            print(f"Error applying feature settings: {e}")
        finally:
            session.close()

        if 4 in self.nav_buttons and not enable_repair:
            self.nav_buttons[4].setVisible(False)
        if 8 in self.nav_buttons and not enable_money:
            self.nav_buttons[8].setVisible(False)

        # Enforce Role-Based Access Control permissions
        from utils.permissions import enforce_ui_permissions
        enforce_ui_permissions(self)

        # Fallback if the active view is now disabled
        curr_idx = self.stacked_widget.currentIndex()
        if (curr_idx == 4 and not enable_repair) or (curr_idx == 8 and not enable_money):
            self.switch_view(0)
