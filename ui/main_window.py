from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QStackedWidget, QMessageBox, QSpacerItem, QSizePolicy, QScrollArea
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
from ui.banking.bank_cash_view import BankCashView
from ui.expenses import ExpensesView
from ui.staff import StaffView
from utils.translator import tr, get_current_language, set_current_language

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
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(14)

        # 1. Sidebar Setup (Floating Lime Capsule Dock)
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 16, 10, 14)
        sidebar_layout.setSpacing(4)

        # Shop Logo / Title with circular emblem badge
        logo_container = QWidget()
        logo_layout = QVBoxLayout(logo_container)
        logo_layout.setContentsMargins(0, 4, 0, 8)
        logo_layout.setSpacing(6)
        logo_layout.setAlignment(Qt.AlignCenter)

        self.logo_icon = QLabel("☀️")
        self.logo_icon.setObjectName("shop_emblem")
        self.logo_icon.setFixedSize(48, 48)
        self.logo_icon.setAlignment(Qt.AlignCenter)
        logo_layout.addWidget(self.logo_icon, alignment=Qt.AlignCenter)

        self.logo_label = QLabel("SUN COMPUTERS,")
        self.logo_label.setObjectName("shop_title")
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.logo_label.setWordWrap(True)
        logo_layout.addWidget(self.logo_label, alignment=Qt.AlignCenter)
        sidebar_layout.addWidget(logo_container)
        self.update_shop_name()

        # Categorized Navigation Groups with Compact Styling & Smooth Scroll
        self.nav_buttons = {}
        self.nav_group_headers = []
        self.nav_groups = []

        nav_groups_data = [
            ("MAIN", [
                ("Dashboard", 0, "Ctrl+1"),
            ]),
            ("OPERATIONS & BILLING", [
                ("Sales Invoice", 3, "Ctrl+4"),
                ("Purchase Entry", 2, "Ctrl+3"),
                ("Service Cards", 4, "Ctrl+5"),
            ]),
            ("FINANCE & HR", [
                ("Payments", 5, "Ctrl+6"),
                ("Expenses", 10, "Ctrl+9"),
                ("Staff Management", 11, "Ctrl+0"),
                ("Bank & Cash", 9, "Ctrl+8"),
                ("UPI / Money Transfer", 8, "Ctrl+Shift+M"),
            ]),
            ("MANAGEMENT & REPORTS", [
                ("Reports", 6, "Ctrl+7"),
                ("Master Records", 1, "Ctrl+2"),
                ("Settings", 7, "Ctrl+,"),
            ]),
        ]

        # Smooth Scroll Area for navigation buttons
        self.sidebar_scroll = QScrollArea()
        self.sidebar_scroll.setObjectName("sidebar_scroll")
        self.sidebar_scroll.setWidgetResizable(True)
        self.sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.sidebar_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.sidebar_scroll.setStyleSheet("""
            QScrollArea#sidebar_scroll {
                background: transparent;
                border: none;
            }
            QScrollArea#sidebar_scroll > QWidget > QWidget {
                background: transparent;
            }
            QScrollBar:vertical {
                width: 4px;
                background: transparent;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.35);
                border-radius: 2px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.6);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(2)

        for group_name, items in nav_groups_data:
            # Clickable Collapsible Header Button
            header_btn = QPushButton()
            header_btn.setObjectName("sidebar_group_header_btn")
            header_btn.setCursor(Qt.PointingHandCursor)

            h_layout = QHBoxLayout(header_btn)
            h_layout.setContentsMargins(6, 0, 6, 0)
            h_layout.setSpacing(4)

            lbl_title = QLabel(tr(group_name))
            lbl_title.setObjectName("sidebar_group_title")
            lbl_title.setAttribute(Qt.WA_TransparentForMouseEvents)
            lbl_title.orig_text = group_name
            h_layout.addWidget(lbl_title)
            h_layout.addStretch()

            lbl_arrow = QLabel("▸")
            lbl_arrow.setObjectName("sidebar_group_arrow")
            lbl_arrow.setAttribute(Qt.WA_TransparentForMouseEvents)
            h_layout.addWidget(lbl_arrow)

            scroll_layout.addWidget(header_btn)
            self.nav_group_headers.append(lbl_title)

            # Container for group buttons
            group_container = QWidget()
            group_container.setStyleSheet("background: transparent;")
            group_container.setVisible(False)
            group_layout = QVBoxLayout(group_container)
            group_layout.setContentsMargins(0, 0, 0, 0)
            group_layout.setSpacing(2)

            group_btns = []
            for text, index, shortcut_key in items:
                btn = QPushButton()
                btn.setCheckable(True)
                btn.setCursor(Qt.PointingHandCursor)

                btn_layout = QHBoxLayout(btn)
                btn_layout.setContentsMargins(10, 0, 10, 0)
                btn_layout.setSpacing(6)

                lbl_text = QLabel(tr(text))
                lbl_text.setObjectName("btn_label")
                lbl_text.setAttribute(Qt.WA_TransparentForMouseEvents)
                btn_layout.addWidget(lbl_text)
                btn.label = lbl_text
                btn.orig_text = text

                btn_layout.addStretch()

                if shortcut_key:
                    btn.setShortcut(shortcut_key)
                    btn.setToolTip(f"{text} ({shortcut_key})")

                    lbl_shortcut = QLabel(shortcut_key)
                    lbl_shortcut.setObjectName("shortcut_label")
                    lbl_shortcut.setAttribute(Qt.WA_TransparentForMouseEvents)
                    btn_layout.addWidget(lbl_shortcut)

                btn.clicked.connect(lambda checked, idx=index: self.switch_view(idx))
                group_layout.addWidget(btn)
                self.nav_buttons[index] = btn
                group_btns.append(btn)

            scroll_layout.addWidget(group_container)

            header_btn.is_expanded = False
            header_btn.arrow_lbl = lbl_arrow
            header_btn.clicked.connect(lambda checked, c=group_container, h=header_btn: self.toggle_nav_group(c, h))
            self.nav_groups.append((header_btn, group_container, group_btns))

        scroll_layout.addStretch()
        self.sidebar_scroll.setWidget(scroll_content)
        sidebar_layout.addWidget(self.sidebar_scroll, 1)

        # Logout Button
        self.logout_btn = QPushButton(tr("Log Out"))
        self.logout_btn.setObjectName("logout_btn")
        self.logout_btn.setCursor(Qt.PointingHandCursor)
        self.logout_btn.clicked.connect(self.handle_logout)
        sidebar_layout.addWidget(self.logout_btn)

        main_layout.addWidget(sidebar)

        # 2. Main Content Wrapper
        content_wrapper = QWidget()
        content_wrapper.setObjectName("content_area")
        content_wrapper_layout = QVBoxLayout(content_wrapper)
        content_wrapper_layout.setContentsMargins(0, 0, 0, 0)
        content_wrapper_layout.setSpacing(12)

        # Header Area
        header = QWidget()
        header.setObjectName("header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)

        self.header_title = QLabel("Dashboard")
        header_layout.addWidget(self.header_title)

        header_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        user_info = QLabel(f"{tr('Welcome')}, {self.user_data['username']} ({self.user_data['role']})")
        user_info.setStyleSheet("color: #475569; font-size: 13px; font-weight: 600;")
        header_layout.addWidget(user_info)
        self.user_info_label = user_info

        header_layout.addSpacing(15)

        # Language Toggle Button (English ⇄ தமிழ்)
        curr_lang = get_current_language()
        self.lang_btn = QPushButton("🌐 தமிழ்" if curr_lang == 'en' else "🌐 English")
        self.lang_btn.setObjectName("lang_btn")
        self.lang_btn.setToolTip("Switch Language / மொழி மாற்றம் (English ⇄ தமிழ்)")
        self.lang_btn.setCursor(Qt.PointingHandCursor)
        self.lang_btn.setFixedHeight(34)
        self.lang_btn.clicked.connect(self.toggle_language)
        header_layout.addWidget(self.lang_btn)

        content_wrapper_layout.addWidget(header)

        # Main Stacked Widget
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setObjectName("content_area")

        # Instantiate all Views
        self.dashboard_view = DashboardView(self)
        self.masters_view = MastersView(self)
        self.products_view = self.masters_view.products_view
        self.categories_view = self.masters_view.categories_view
        self.customers_view = self.masters_view.customers_view
        self.suppliers_view = self.masters_view.suppliers_view
        self.bank_accounts_view = None  # Will be bound after BankCashView instantiation
        self.units_view = self.masters_view.units_view
        self.purchase_view = PurchaseView(self)
        self.sales_view = SalesView(self)
        self.services_view = ServicesView(self)
        self.payments_view = PaymentsView(self)
        self.reports_view = ReportsView(self)
        self.settings_view = SettingsView(self)
        self.money_transfer_view = MoneyTransferView(self)
        self.bank_cash_view = BankCashView(self)
        self.bank_accounts_view = self.bank_cash_view.bank_accounts_view
        self.expenses_view = ExpensesView(self)
        self.staff_view = StaffView(self)

        # Add Views to Stacked Widget in order
        self.stacked_widget.addWidget(self.dashboard_view)       # 0
        self.stacked_widget.addWidget(self.masters_view)         # 1
        self.stacked_widget.addWidget(self.purchase_view)        # 2
        self.stacked_widget.addWidget(self.sales_view)           # 3
        self.stacked_widget.addWidget(self.services_view)        # 4
        self.stacked_widget.addWidget(self.payments_view)        # 5
        self.stacked_widget.addWidget(self.reports_view)         # 6
        self.stacked_widget.addWidget(self.settings_view)        # 7
        self.stacked_widget.addWidget(self.money_transfer_view)   # 8
        self.stacked_widget.addWidget(self.bank_cash_view)        # 9
        self.stacked_widget.addWidget(self.expenses_view)         # 10
        self.stacked_widget.addWidget(self.staff_view)            # 11

        content_wrapper_layout.addWidget(self.stacked_widget)
        main_layout.addWidget(content_wrapper)

        # Setup master record sub-tab shortcuts
        master_shortcuts = [
            ("Ctrl+Shift+P", 0),
            ("Ctrl+Alt+1", 0),
            ("Ctrl+Shift+K", 1),
            ("Ctrl+Alt+2", 1),
            ("Ctrl+Shift+C", 2),
            ("Ctrl+Alt+3", 2),
            ("Ctrl+Shift+S", 3),
            ("Ctrl+Alt+4", 3),
            ("Ctrl+Shift+U", 4),
            ("Ctrl+Alt+5", 4),
        ]
        for key, tab_idx in master_shortcuts:
            sc = QShortcut(QKeySequence(key), self)
            sc.activated.connect(partial(self.open_master_tab, tab_idx))

        # Shortcut for Bank Accounts Master in Bank & Cash view
        for key in ["Ctrl+Shift+B", "Ctrl+Alt+6"]:
            sc = QShortcut(QKeySequence(key), self)
            sc.activated.connect(self.open_bank_master_tab)

        # Setup universal Add shortcut (Ctrl+N) for master records
        self.universal_add_shortcut = QShortcut(QKeySequence("Ctrl+N"), self)
        self.universal_add_shortcut.activated.connect(self.handle_universal_add)

        # Set default view
        self.apply_feature_settings()
        default_index = 0
        if 0 in self.nav_buttons and self.nav_buttons[0].isHidden():
            for idx in sorted(self.nav_buttons.keys()):
                if not self.nav_buttons[idx].isHidden():
                    default_index = idx
                    break
        self.apply_language_change()
        self.switch_view(default_index, auto_expand=False)

    def update_shop_name(self):
        from database import Session, Setting
        from utils.ui_helpers import get_circular_pixmap
        import os
        session = Session()
        try:
            shop_name_setting = session.query(Setting).filter_by(key='shop_name').first()
            name = shop_name_setting.value.upper() if shop_name_setting and shop_name_setting.value else "SUN COMPUTERS,"
            self.logo_label.setText(name)

            # Update shop logo / emblem
            logo_setting = session.query(Setting).filter_by(key='shop_logo').first()
            logo_path = logo_setting.value if logo_setting and logo_setting.value else None
            if logo_path and os.path.exists(logo_path):
                circ_pix = get_circular_pixmap(logo_path, size=48)
                if circ_pix and not circ_pix.isNull():
                    self.logo_icon.setPixmap(circ_pix)
                    self.logo_icon.setFixedSize(48, 48)
                    self.logo_icon.setAlignment(Qt.AlignCenter)
                    self.logo_icon.setStyleSheet("border-radius: 24px; background-color: #ffffff; border: 2px solid #ffffff;")
                else:
                    self._reset_default_emblem()
            else:
                self._reset_default_emblem()
        except Exception:
            self.logo_label.setText("SUN COMPUTERS,")
            self._reset_default_emblem()
        finally:
            session.close()

    def _reset_default_emblem(self):
        self.logo_icon.clear()
        self.logo_icon.setText("☀️")
        self.logo_icon.setFixedSize(48, 48)
        self.logo_icon.setAlignment(Qt.AlignCenter)
        self.logo_icon.setStyleSheet("""
            QLabel#shop_emblem {
                background-color: #f59e0b;
                color: #ffffff;
                font-size: 22px;
                font-weight: bold;
                border-radius: 24px;
                border: 2px solid #ffffff;
            }
        """)

    def update_theme(self, color_hex):
        from styles import get_theme_stylesheet
        app = QApplication.instance()
        if app:
            app.setStyleSheet(get_theme_stylesheet(color_hex))
        self.update_shop_name()

    def toggle_nav_group(self, container, header_btn, force_state=None):
        if force_state is not None:
            new_state = force_state
        else:
            new_state = not getattr(header_btn, 'is_expanded', False)

        header_btn.is_expanded = new_state
        container.setVisible(new_state)
        if hasattr(header_btn, 'arrow_lbl'):
            header_btn.arrow_lbl.setText("▾" if new_state else "▸")

    def switch_view(self, index, auto_expand=True):
        # Prevent switching to hidden sidebar buttons (via shortcuts)
        if index in self.nav_buttons and self.nav_buttons[index].isHidden():
            return

        # Check corresponding nav button
        for idx, btn in self.nav_buttons.items():
            btn.setChecked(idx == index)

        self.stacked_widget.setCurrentIndex(index)

        # Auto-expand active group if it was collapsed
        if auto_expand and hasattr(self, 'nav_groups'):
            for header_btn, container, group_btns in self.nav_groups:
                if any(self.nav_buttons.get(index) == b for b in group_btns):
                    if not getattr(header_btn, 'is_expanded', False):
                        self.toggle_nav_group(container, header_btn, force_state=True)
        
        # Update Header Title
        self.update_header_title_for_index(index)

        # Refresh the view data when selected
        widget = self.stacked_widget.widget(index)
        if hasattr(widget, "refresh_data"):
            widget.refresh_data()

        from utils.permissions import enforce_ui_permissions
        enforce_ui_permissions(self)

    def update_header_title_for_index(self, index):
        title_map = {
            0: "Dashboard",
            1: "Master Records",
            2: "Purchase Entry (Inventory)",
            3: "Sales Invoice",
            4: "Repair Center Job Cards",
            5: "Payments Ledger",
            6: "Reports & Financial Analysis",
            7: "System Settings & Database Admin",
            8: "UPI / Money Transfer",
            9: "Bank Accounts & Cash Drawer Management",
            10: "Daily Expenses & Cost Management",
            11: "Staff & Payroll Management"
        }
        raw_title = title_map.get(index, "Inventory & Accounting")
        self.header_title.setText(tr(raw_title))

    def toggle_language(self):
        curr = get_current_language()
        new_lang = "ta" if curr == "en" else "en"
        set_current_language(new_lang)
        self.apply_language_change()

    def apply_language_change(self):
        curr = get_current_language()
        
        # 1. Update language button text
        if hasattr(self, 'lang_btn'):
            self.lang_btn.setText("🌐 தமிழ்" if curr == 'en' else "🌐 English")

        # 2. Update sidebar buttons and group headers
        if hasattr(self, 'nav_group_headers'):
            for lbl in self.nav_group_headers:
                if hasattr(lbl, 'orig_text'):
                    lbl.setText(tr(lbl.orig_text))

        if hasattr(self, 'nav_buttons'):
            for idx, btn in self.nav_buttons.items():
                if hasattr(btn, 'label') and hasattr(btn, 'orig_text'):
                    btn.label.setText(tr(btn.orig_text))

        # 3. Update logout button
        if hasattr(self, 'logout_btn'):
            self.logout_btn.setText(tr("Log Out"))

        # 4. Update user welcome label
        if hasattr(self, 'user_info_label'):
            self.user_info_label.setText(f"{tr('Welcome')}, {self.user_data['username']} ({self.user_data['role']})")

        # 5. Update header title
        curr_idx = self.stacked_widget.currentIndex()
        self.update_header_title_for_index(curr_idx)

        # 6. Retranslate views if supported
        for idx in range(self.stacked_widget.count()):
            w = self.stacked_widget.widget(idx)
            if hasattr(w, 'retranslate_ui'):
                w.retranslate_ui()

    def open_master_tab(self, tab_index):
        self.switch_view(1)
        if hasattr(self, 'masters_view'):
            self.masters_view.set_active_tab(tab_index)

    def open_bank_master_tab(self):
        self.switch_view(9)
        if hasattr(self, 'bank_cash_view'):
            idx = self.bank_cash_view.tabs.indexOf(getattr(self.bank_cash_view, 'bank_master_tab', None))
            if idx >= 0:
                self.bank_cash_view.set_active_tab(idx)
            else:
                self.bank_cash_view.set_active_tab(5)

    def handle_universal_add(self):
        if self.stacked_widget.currentIndex() == 9:
            if hasattr(self, 'bank_cash_view'):
                self.bank_cash_view.handle_add_bank()
        else:
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
            from utils.ui_helpers import show_modern_alert
            if low_stock_products:
                msg = "The following items are low in stock:\n\n"
                for p in low_stock_products:
                    status = "OUT OF STOCK" if p.stock_qty == 0 else f"Qty: {p.stock_qty} (Limit: {p.low_stock_limit})"
                    msg += f"• {p.name} ({p.brand} {p.model}) - {status}\n"
                
                show_modern_alert(
                    self,
                    "Low Stock Alert",
                    msg,
                    icon_type="warning"
                )
            elif manual:
                show_modern_alert(
                    self,
                    "Low Stock Alert",
                    "All products are well stocked!\n(No items below their individual low stock limits).",
                    icon_type="success"
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
