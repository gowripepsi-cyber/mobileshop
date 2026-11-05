import datetime
import os
import subprocess
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QComboBox, 
                             QDateEdit, QSpinBox, QDoubleSpinBox, QPushButton, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QMessageBox, QFrame, QFormLayout, 
                             QFileDialog, QTabWidget, QDialog, QDialogButtonBox, QCompleter, QCheckBox)
from PySide6.QtCore import Qt, QDate, Signal, QEvent, QTimer, QSortFilterProxyModel
from PySide6.QtGui import QStandardItemModel, QStandardItem
from utils.formatters import format_inr
from database import Session, Setting
from models import Customer, Product, BankAccount, SalesMaster, SalesItem, CashTransaction, BankTransaction, Category
from utils.pdf_generator import generate_sales_pdf
from utils.ui_helpers import enable_quick_add_auto_select, SearchableProductComboBox, SearchableComboBox, AutoClearSearchableComboBox


class SalesView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.invoice_items = []  # list of dicts: {"product_id": int, "name": str, "qty": int, "rate": float, "discount": float}
        self.editing_sales_id = None  # Tracks if we are editing an invoice
        self.products_cache = {}      # Cache of products to prevent early signal errors during reload
        self.gst_globally_enabled = False
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Tabs for operations
        self.tabs = QTabWidget()

        # Tab 1: New Invoice Entry
        self.entry_tab = QWidget()
        self.setup_entry_tab()
        self.tabs.addTab(self.entry_tab, "New Sales Invoice")

        # Tab 2: Sales Invoice History
        self.history_tab = QWidget()
        self.setup_history_tab()
        self.tabs.addTab(self.history_tab, "Sales Invoice History")

        # Tab 3 & 4: Sales Return Entry & History
        from ui.sales.sales_return import SalesReturnEntryWidget, SalesReturnHistoryWidget
        self.return_history_tab = SalesReturnHistoryWidget(self)
        self.return_entry_tab = SalesReturnEntryWidget(self, self.return_history_tab)
        self.tabs.addTab(self.return_entry_tab, "New Sales Return")
        self.tabs.addTab(self.return_history_tab, "Sales Return History")

        layout.addWidget(self.tabs)

    def setup_entry_tab(self):
        # Vertical stacked layout: Top = Block 1 (Sales Invoice Parameters), Bottom = Block 2 (Items Entry & Table)
        main_layout = QVBoxLayout(self.entry_tab)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        def make_field(label_text, widget, width=None, stretch=0):
            w = QWidget()
            vl = QVBoxLayout(w)
            vl.setContentsMargins(0, 0, 0, 0)
            vl.setSpacing(3)
            lbl_f = QLabel(label_text)
            lbl_f.setStyleSheet("font-size: 11.5px; font-weight: 600; color: #475569;")
            vl.addWidget(lbl_f)
            vl.addWidget(widget)
            if width:
                w.setFixedWidth(width)
            return w

        input_style = "min-height: 28px; padding: 2px 8px;"

        # =========================================================================
        # BLOCK 1 (Top Block): Sales Invoice Parameters Card
        # =========================================================================
        top_panel = QFrame()
        top_panel.setProperty("class", "CardFrame")
        top_layout = QVBoxLayout(top_panel)
        top_layout.setContentsMargins(16, 12, 16, 12)
        top_layout.setSpacing(10)

        # Header Row
        top_title_row = QHBoxLayout()
        top_title_row.setContentsMargins(0, 0, 0, 0)
        title_lbl = QLabel("Sales Invoice Details")
        title_lbl.setStyleSheet("font-size: 14.5px; font-weight: bold; color: #0f172a;")
        top_title_row.addWidget(title_lbl)
        top_title_row.addStretch()
        top_layout.addLayout(top_title_row)

        # Top Grid: 4 Columns x 2 Rows
        top_grid = QGridLayout()
        top_grid.setContentsMargins(0, 0, 0, 0)
        top_grid.setHorizontalSpacing(14)
        top_grid.setVerticalSpacing(8)

        top_grid.setColumnStretch(0, 1)
        top_grid.setColumnStretch(1, 1)
        top_grid.setColumnStretch(2, 2)
        top_grid.setColumnStretch(3, 1)

        # 1. Invoice Number
        self.invoice_input = QLineEdit()
        self.invoice_input.setPlaceholderText("e.g. INV-1004")
        self.invoice_input.setStyleSheet(input_style)
        f_invoice = make_field("Invoice Number *", self.invoice_input)

        # 2. Invoice Date
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setStyleSheet(input_style)
        f_date = make_field("Invoice Date", self.date_input)

        # 3. Customer (combo + add button)
        self.customer_combo = AutoClearSearchableComboBox()
        self.customer_combo.currentTextChanged.connect(self.check_customer_match)
        if self.customer_combo.lineEdit():
            self.customer_combo.lineEdit().textChanged.connect(self.check_customer_match)

        self.add_customer_btn = QPushButton("+")
        self.add_customer_btn.setToolTip("Add new customer")
        self.add_customer_btn.setProperty("class", "btn-quick-add")
        self.add_customer_btn.setStyleSheet("min-height: 36px; max-height: 36px; margin: 0px; padding: 0px; font-size: 18px; font-weight: bold; border-radius: 6px;")
        self.add_customer_btn.setFixedWidth(34)
        self.add_customer_btn.setCursor(Qt.PointingHandCursor)
        self.add_customer_btn.clicked.connect(self.handle_add_customer_click)
        self.add_customer_btn.hide()

        cust_widget = QWidget()
        cust_layout = QHBoxLayout(cust_widget)
        cust_layout.setContentsMargins(0, 0, 0, 0)
        cust_layout.setSpacing(4)
        cust_layout.addWidget(self.customer_combo, 1)
        cust_layout.addWidget(self.add_customer_btn)
        f_cust = make_field("Customer", cust_widget)

        # 4. Tax Invoice (GST)
        self.gst_enabled_checkbox = QCheckBox("Tax Invoice (GST)")
        self.gst_enabled_checkbox.setStyleSheet("font-size: 12px; font-weight: 500;")
        self.gst_enabled_checkbox.stateChanged.connect(self.on_gst_checkbox_changed)
        self.gst_enabled_label = QLabel("Tax Invoicing")
        self.gst_enabled_label.setStyleSheet("font-size: 11.5px; font-weight: 600; color: #475569;")

        self.gst_top_container = QWidget()
        gst_top_vl = QVBoxLayout(self.gst_top_container)
        gst_top_vl.setContentsMargins(0, 0, 0, 0)
        gst_top_vl.setSpacing(3)
        gst_top_vl.addWidget(self.gst_enabled_label)
        gst_cb_wrap = QWidget()
        gst_cb_wrap_l = QHBoxLayout(gst_cb_wrap)
        gst_cb_wrap_l.setContentsMargins(0, 0, 0, 0)
        gst_cb_wrap_l.addWidget(self.gst_enabled_checkbox)
        gst_top_vl.addWidget(gst_cb_wrap)

        # 5. Payment Mode
        self.pay_mode_combo = QComboBox()
        self.pay_mode_combo.addItems(["Cash", "Bank"])
        self.pay_mode_combo.setStyleSheet(input_style)
        self.pay_mode_combo.currentTextChanged.connect(self.toggle_bank_account)
        self.pay_mode_combo.currentIndexChanged.connect(lambda: self.toggle_bank_account())
        f_mode = make_field("Payment Mode", self.pay_mode_combo)

        # 6. Select Bank A/c
        self.bank_combo = QComboBox()
        self.bank_combo.setStyleSheet(input_style)
        self.bank_combo.setEnabled(False)
        f_bank = make_field("Select Bank A/c", self.bank_combo)

        # 7. Paid Amount (₹)
        self.paid_input = QDoubleSpinBox()
        self.paid_input.setRange(0, 9999999)
        self.paid_input.setValue(0.0)
        self.paid_input.setDecimals(2)
        self.paid_input.setStyleSheet(input_style)
        self.paid_input.valueChanged.connect(self.update_summary)
        f_paid = make_field("Paid Amount (₹)", self.paid_input)

        # 8. Save / Cancel Buttons in Top Block
        self.save_btn = QPushButton("Save && Print Invoice")
        self.save_btn.setProperty("class", "btn-success")
        self.save_btn.setStyleSheet("min-height: 36px; max-height: 36px; padding: 0px 14px; font-weight: bold; border-radius: 6px;")
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.clicked.connect(self.save_sales_invoice)

        self.cancel_edit_btn = QPushButton("Cancel Edit")
        self.cancel_edit_btn.setProperty("class", "btn-secondary")
        self.cancel_edit_btn.setStyleSheet("min-height: 36px; max-height: 36px; padding: 0px 12px; font-weight: bold; border-radius: 6px;")
        self.cancel_edit_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_edit_btn.setVisible(False)
        self.cancel_edit_btn.clicked.connect(self.cancel_edit_mode)

        top_btn_container = QWidget()
        top_btn_vl = QVBoxLayout(top_btn_container)
        top_btn_vl.setContentsMargins(0, 0, 0, 0)
        top_btn_vl.setSpacing(3)
        top_btn_spacer = QLabel(" ")
        top_btn_spacer.setStyleSheet("font-size: 11.5px;")
        top_btn_vl.addWidget(top_btn_spacer)
        top_btn_hl = QHBoxLayout()
        top_btn_hl.setContentsMargins(0, 0, 0, 0)
        top_btn_hl.setSpacing(6)
        top_btn_hl.addWidget(self.save_btn, 1)
        top_btn_hl.addWidget(self.cancel_edit_btn, 1)
        top_btn_vl.addLayout(top_btn_hl)

        # Row 0: Invoice Number, Date, Customer, Tax Invoice
        top_grid.addWidget(f_invoice, 0, 0)
        top_grid.addWidget(f_date, 0, 1)
        top_grid.addWidget(f_cust, 0, 2)
        top_grid.addWidget(self.gst_top_container, 0, 3)

        # Row 1: Payment Mode, Bank A/c, Paid Amount, Save Button
        top_grid.addWidget(f_mode, 1, 0)
        top_grid.addWidget(f_bank, 1, 1)
        top_grid.addWidget(f_paid, 1, 2)
        top_grid.addWidget(top_btn_container, 1, 3)

        top_layout.addLayout(top_grid)
        main_layout.addWidget(top_panel)

        # =========================================================================
        # BLOCK 2 (Bottom Block): Items Entry & Table Card
        # =========================================================================
        bottom_panel = QFrame()
        bottom_panel.setProperty("class", "CardFrame")
        bottom_layout = QVBoxLayout(bottom_panel)
        bottom_layout.setContentsMargins(16, 12, 16, 14)
        bottom_layout.setSpacing(10)

        entry_title = QLabel("Add Items to Invoice")
        entry_title.setStyleSheet("font-size: 13.5px; font-weight: bold; color: #0f172a;")
        bottom_layout.addWidget(entry_title)

        # Hidden discount input
        self.discount_input = QDoubleSpinBox()
        self.discount_input.hide()

        # Item Entry Row (Clean single horizontal row)
        item_row = QHBoxLayout()
        item_row.setContentsMargins(0, 0, 0, 0)
        item_row.setSpacing(8)

        # 1. Product Code
        self.product_code_input = QLineEdit()
        self.product_code_input.setPlaceholderText("Code")
        self.product_code_input.setStyleSheet(input_style)
        self.product_code_input.returnPressed.connect(self.handle_product_code_entry)
        self.product_code_input._skip_enter_nav = True
        f_pcode = make_field("Product Code", self.product_code_input, width=90)
        item_row.addWidget(f_pcode)

        # 2. Category Filter (160px width)
        self.category_combo = SearchableComboBox()
        self.category_combo.setPlaceholderText("Select Category")
        self.category_combo.setStyleSheet(input_style)
        self.category_combo.currentIndexChanged.connect(self.filter_products_by_category)
        f_pcat = make_field("Category", self.category_combo, width=160)
        item_row.addWidget(f_pcat)

        # 3. Item Name + Quick Add Button
        self.product_combo = SearchableProductComboBox()
        self.product_combo.setPlaceholderText("Select / Search Product")
        self.product_combo.currentIndexChanged.connect(self.update_rate_on_product_change)
        self.product_combo.currentTextChanged.connect(self.check_product_match)
        if self.product_combo.lineEdit():
            self.product_combo.lineEdit().textChanged.connect(self.check_product_match)

        self.add_product_btn = QPushButton("+")
        self.add_product_btn.setToolTip("Add new product to master records")
        self.add_product_btn.setProperty("class", "btn-quick-add")
        self.add_product_btn.setStyleSheet("min-height: 36px; max-height: 36px; margin: 0px; padding: 0px; font-size: 18px; font-weight: bold; border-radius: 6px;")
        self.add_product_btn.setFixedWidth(32)
        self.add_product_btn.setCursor(Qt.PointingHandCursor)
        self.add_product_btn.clicked.connect(self.handle_add_product_click)
        self.add_product_btn.hide()

        prod_item_widget = QWidget()
        prod_item_layout = QHBoxLayout(prod_item_widget)
        prod_item_layout.setContentsMargins(0, 0, 0, 0)
        prod_item_layout.setSpacing(4)
        prod_item_layout.addWidget(self.product_combo, 1)
        prod_item_layout.addWidget(self.add_product_btn)

        f_pname = make_field("Item Name *", prod_item_widget)
        item_row.addWidget(f_pname, 1)

        # 4. Quantity
        self.qty_input = QSpinBox()
        self.qty_input.setRange(1, 100000)
        self.qty_input.setValue(1)
        self.qty_input.setStyleSheet(input_style)
        f_pqty = make_field("Quantity", self.qty_input, width=70)
        item_row.addWidget(f_pqty)

        # 5. Unit
        self.unit_combo = QComboBox()
        self.unit_combo.setStyleSheet(input_style)
        self.load_units()
        f_punit = make_field("Unit", self.unit_combo, width=75)
        item_row.addWidget(f_punit)

        # 6. Rate (per unit)
        self.rate_input = QDoubleSpinBox()
        self.rate_input.setRange(0.0, 9999999.0)
        self.rate_input.setValue(0.0)
        self.rate_input.setDecimals(2)
        self.rate_input.setStyleSheet(input_style)
        self.rate_label = QLabel("Rate (per unit):")
        f_prate = make_field("Rate (₹)", self.rate_input, width=90)
        item_row.addWidget(f_prate)

        # 7. GST % (Container)
        self.gst_rate_label = QLabel("GST %:")
        self.gst_rate_combo = QComboBox()
        self.gst_rate_combo.addItems(["0%", "5%", "12%", "18%", "28%"])
        self.gst_rate_combo.setCurrentText("18%")
        self.gst_rate_combo.setStyleSheet(input_style)

        self.gst_item_container = make_field("GST %", self.gst_rate_combo, width=75)
        item_row.addWidget(self.gst_item_container)

        # 8. Add Item Button
        self.add_item_btn = QPushButton("Add Item")
        self.add_item_btn.setProperty("class", "btn-warning")
        self.add_item_btn.setStyleSheet("""
            QPushButton {
                background-color: #f59e0b;
                color: #ffffff;
                font-size: 12px;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                min-height: 36px;
                max-height: 36px;
                padding: 0px 14px;
            }
            QPushButton:hover {
                background-color: #d97706;
            }
        """)
        self.add_item_btn.setCursor(Qt.PointingHandCursor)
        self.add_item_btn.clicked.connect(self.add_item_to_list)

        add_btn_w = QWidget()
        add_btn_w.setFixedWidth(85)
        add_btn_vl = QVBoxLayout(add_btn_w)
        add_btn_vl.setContentsMargins(0, 0, 0, 0)
        add_btn_vl.setSpacing(3)
        add_btn_spacer = QLabel(" ")
        add_btn_spacer.setStyleSheet("font-size: 11.5px;")
        add_btn_vl.addWidget(add_btn_spacer)
        add_btn_vl.addWidget(self.add_item_btn)
        item_row.addWidget(add_btn_w)

        bottom_layout.addLayout(item_row)

        # Items Table
        self.table = QTableWidget()
        self.setup_table_columns(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)
        bottom_layout.addWidget(self.table, 1)

        # Summary Bar (Totals, Paid, Balance, and Bottom Save Button)
        summary_bar = QHBoxLayout()
        summary_bar.setContentsMargins(4, 4, 4, 4)
        summary_bar.setSpacing(16)

        self.total_lbl = QLabel("Total Amount: ₹0.00")
        self.total_lbl.setStyleSheet("font-size: 14.5px; font-weight: bold; color: #4338ca;")

        self.balance_lbl = QLabel("Balance Receivable: ₹0.00")
        self.balance_lbl.setStyleSheet("font-size: 14.5px; font-weight: bold; color: #d97706;")

        summary_bar.addWidget(self.total_lbl)
        summary_bar.addWidget(self.balance_lbl)
        summary_bar.addStretch()

        self.save_bottom_btn = QPushButton("Save && Print Invoice")
        self.save_bottom_btn.setProperty("class", "btn-success")
        self.save_bottom_btn.setStyleSheet("min-height: 34px; padding: 0px 16px; font-weight: bold; border-radius: 6px;")
        self.save_bottom_btn.setCursor(Qt.PointingHandCursor)
        self.save_bottom_btn.clicked.connect(self.save_sales_invoice)
        summary_bar.addWidget(self.save_bottom_btn)

        self.cancel_bottom_btn = QPushButton("Cancel Edit")
        self.cancel_bottom_btn.setProperty("class", "btn-secondary")
        self.cancel_bottom_btn.setStyleSheet("min-height: 34px; padding: 0px 14px; font-weight: bold; border-radius: 6px;")
        self.cancel_bottom_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_bottom_btn.setVisible(False)
        self.cancel_bottom_btn.clicked.connect(self.cancel_edit_mode)
        summary_bar.addWidget(self.cancel_bottom_btn)

        bottom_layout.addLayout(summary_bar)

        # Add Block 2 with vertical stretch 1 so it fills the rest of the tab
        main_layout.addWidget(bottom_panel, 1)

    def setup_history_tab(self):
        layout = QVBoxLayout(self.history_tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Search Filters Panel
        filters_frame = QFrame()
        filters_frame.setProperty("class", "CardFrame")
        filters_layout = QHBoxLayout(filters_frame)
        filters_layout.setContentsMargins(15, 12, 15, 12)
        filters_layout.setSpacing(15)

        # Search Query
        filters_layout.addWidget(QLabel("Search:"))
        self.history_search = QLineEdit()
        self.history_search.setPlaceholderText("Invoice # or Customer name...")
        self.history_search.textChanged.connect(self.load_history)
        filters_layout.addWidget(self.history_search, 2)

        # Date range
        filters_layout.addWidget(QLabel("From:"))
        self.history_from_date = QDateEdit()
        self.history_from_date.setCalendarPopup(True)
        self.history_from_date.setDate(QDate.currentDate().addMonths(-1))
        self.history_from_date.dateChanged.connect(self.load_history)
        filters_layout.addWidget(self.history_from_date)

        filters_layout.addWidget(QLabel("To:"))
        self.history_to_date = QDateEdit()
        self.history_to_date.setCalendarPopup(True)
        self.history_to_date.setDate(QDate.currentDate())
        self.history_to_date.dateChanged.connect(self.load_history)
        filters_layout.addWidget(self.history_to_date)

        # Reset button
        self.reset_filter_btn = QPushButton("Reset")
        self.reset_filter_btn.setProperty("class", "btn-secondary")
        self.reset_filter_btn.clicked.connect(self.reset_history_filters)
        filters_layout.addWidget(self.reset_filter_btn)

        layout.addWidget(filters_frame)

        # History Table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(7)
        self.history_table.setHorizontalHeaderLabels([
            "Invoice #", "Date", "Customer Name", "Total (₹)", "Paid (₹)", "Balance (₹)", "Actions"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Fixed)
        self.history_table.setColumnWidth(6, 270)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.verticalHeader().setDefaultSectionSize(54)
        layout.addWidget(self.history_table)

        # Lazy loading state
        self.history_offset = 0
        self.has_more_history = True
        self.history_table.verticalScrollBar().valueChanged.connect(self.handle_history_scroll)

    def filter_products_by_category(self):
        cat_name = self.category_combo.currentText().strip()
        filtered_products = []
        for prod_id, p in self.products_cache.items():
            if not cat_name or cat_name == "-- All Categories --" or p.category == cat_name:
                filtered_products.append(p)
        self.product_combo.set_products(filtered_products)
        self.update_rate_on_product_change()
        if hasattr(self, 'add_product_btn'):
            self.check_product_match()

    def load_customers(self, select_customer_id=None):
        curr_id = select_customer_id if select_customer_id is not None else self.customer_combo.currentData()
        self.customer_combo.blockSignals(True)
        self.customer_combo.clear()
        self.customer_combo.addItem("-- Select Customer / Cash --", None)
        session = Session()
        try:
            customers = session.query(Customer).all()
            for c in customers:
                self.customer_combo.addItem(c.name, c.id)
        except Exception as e:
            print(f"Error loading customers: {e}")
        finally:
            session.close()

        self.customer_combo.update_completer()
        self.customer_combo.blockSignals(False)

        if curr_id is not None:
            idx = self.customer_combo.findData(curr_id)
            if idx >= 0:
                self.customer_combo.setCurrentIndex(idx)
        else:
            self.customer_combo.setCurrentIndex(0)
        if hasattr(self, 'add_customer_btn'):
            self.check_customer_match()

    def check_customer_match(self):
        text = self.customer_combo.currentText().strip()
        if not text or text == "-- Select Customer / Cash --":
            self.add_customer_btn.hide()
            return
        
        matched = False
        for i in range(self.customer_combo.count()):
            item_text = self.customer_combo.itemText(i).strip()
            if item_text and item_text != "-- Select Customer / Cash --" and item_text.lower() == text.lower():
                matched = True
                if self.customer_combo.currentIndex() != i:
                    self.customer_combo.blockSignals(True)
                    self.customer_combo.setCurrentIndex(i)
                    self.customer_combo.blockSignals(False)
                break
        
        if not matched:
            self.add_customer_btn.show()
        else:
            self.add_customer_btn.hide()

    def handle_add_customer_click(self):
        from ui.masters.customers import CustomerDialog
        typed_text = self.customer_combo.currentText().strip()
        if typed_text == "-- Select Customer / Cash --":
            typed_text = ""
        dlg = CustomerDialog(initial_name=typed_text, parent=self)
        if dlg.exec() == QDialog.Accepted and hasattr(dlg, 'saved_customer_id'):
            self.load_customers(select_customer_id=dlg.saved_customer_id)

    def check_product_match(self):
        text = self.product_combo.currentText().strip()
        if not text or text == "Select Product" or text.startswith("--"):
            self.add_product_btn.hide()
            return
        
        matched = False
        for i in range(self.product_combo.count()):
            item_text = self.product_combo.itemText(i).strip()
            if item_text and item_text != "Select Product":
                name_part = item_text
                if " | " in item_text:
                    name_part = item_text.split(" | ")[1]
                if " (" in name_part:
                    name_part = name_part.split(" (")[0]
                
                if name_part.strip().lower() == text.lower() or item_text.lower() == text.lower():
                    matched = True
                    break
        
        if not matched:
            self.add_product_btn.show()
        else:
            self.add_product_btn.hide()

    def handle_add_product_click(self):
        from ui.masters.products import ProductDialog
        typed_text = self.product_combo.currentText().strip()
        if typed_text == "Select Product":
            typed_text = ""
        current_cat = self.category_combo.currentText().strip()
        def_cat = current_cat if (current_cat and current_cat != "-- All Categories --") else None
        dlg = ProductDialog(initial_name=typed_text, default_category=def_cat, parent=self)
        if dlg.exec() == QDialog.Accepted and hasattr(dlg, 'saved_product_id'):
            self.refresh_data()
            self.product_combo.select_product_id(dlg.saved_product_id)

    def refresh_data(self):
        session = Session()
        try:
            # 1. Load Products & Cache them first to prevent early signal errors
            self.products_cache = {}
            products = session.query(Product).all()
            for p in products:
                self.products_cache[p.id] = p

            # Update auto-completer
            codes = [f"{p.product_code} | {p.name}" for p in products if p.product_code]
            from PySide6.QtWidgets import QCompleter
            completer = QCompleter(codes, self)
            completer.setCaseSensitivity(Qt.CaseInsensitive)
            completer.setFilterMode(Qt.MatchContains)
            popup = completer.popup()
            popup.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            fm = popup.fontMetrics()
            max_width = 350
            for code_str in codes:
                w = fm.horizontalAdvance(code_str) + 50
                if w > max_width:
                    max_width = w
            popup.setMinimumWidth(max_width)
            completer.activated.connect(lambda text: self.handle_product_code_entry())
            self.product_code_input.setCompleter(completer)

            # 2. Block combo box signals during update
            self.customer_combo.blockSignals(True)
            self.category_combo.blockSignals(True)
            self.bank_combo.blockSignals(True)

            # Load Customers
            self.load_customers()

            # Load Categories
            self.category_combo.clear()
            self.category_combo.addItem("-- All Categories --")
            categories = session.query(Category).all()
            for c in categories:
                self.category_combo.addItem(c.name)
            self.category_combo.setCurrentIndex(-1)
            self.category_combo.update_completer()

            # Load Bank Accounts
            self.bank_combo.clear()
            banks = session.query(BankAccount).all()
            for b in banks:
                self.bank_combo.addItem(f"{b.bank_name} ({b.account_name})", b.id)

            # Suggest an invoice number (if not editing)
            if not self.editing_sales_id:
                last_s = session.query(SalesMaster).order_by(SalesMaster.id.desc()).first()
                if last_s:
                    self.invoice_input.setText(f"INV-{last_s.id + 1001}")
                else:
                    self.invoice_input.setText("INV-1001")

            # 3. Unblock signals and filter/load
            self.customer_combo.blockSignals(False)
            self.category_combo.blockSignals(False)
            self.bank_combo.blockSignals(False)

            # Load global GST setting
            self.gst_globally_enabled = False
            gst_setting = session.query(Setting).filter_by(key='enable_gst').first()
            if gst_setting and gst_setting.value == 'true':
                self.gst_globally_enabled = True
            self.apply_gst_visibility()

            self.filter_products_by_category()
            self.load_units()
            self.toggle_bank_account()
            
            # Load History
            self.load_history()

            if hasattr(self, 'return_entry_tab'):
                self.return_entry_tab.refresh_data()
            if hasattr(self, 'return_history_tab'):
                self.return_history_tab.load_history()

        except Exception as e:
            print(f"Error loading sales options: {e}")
        finally:
            session.close()

    def load_units(self):
        curr_text = self.unit_combo.currentText() if hasattr(self, 'unit_combo') else ""
        if hasattr(self, 'unit_combo'):
            self.unit_combo.blockSignals(True)
            self.unit_combo.clear()
            session = Session()
            try:
                from models import Unit
                units = session.query(Unit).order_by(Unit.name.asc()).all()
                for u in units:
                    self.unit_combo.addItem(u.name)
            except Exception:
                pass
            finally:
                session.close()

            if self.unit_combo.count() == 0:
                self.unit_combo.addItems(["Pcs", "Box", "Kg", "Grams", "Ltr", "Mtr", "Nos", "Pack", "Set"])

            if curr_text:
                idx = self.unit_combo.findText(curr_text)
                if idx >= 0:
                    self.unit_combo.setCurrentIndex(idx)
            self.unit_combo.blockSignals(False)

    def update_rate_on_product_change(self):
        prod_id = self.product_combo.currentData()
        if prod_id and hasattr(self, 'products_cache') and prod_id in self.products_cache:
            prod = self.products_cache[prod_id]
            self.rate_input.setValue(prod.selling_price)
            # Sync product code input for visual feedback
            if prod.product_code:
                self.product_code_input.setText(prod.product_code)
            # Sync unit
            unit_val = getattr(prod, 'unit', 'Pcs') or 'Pcs'
            u_idx = self.unit_combo.findText(unit_val)
            if u_idx >= 0:
                self.unit_combo.setCurrentIndex(u_idx)
        else:
            self.rate_input.setValue(0.0)
            self.product_code_input.clear()
            self.unit_combo.setCurrentIndex(0)

    def handle_product_code_entry(self):
        text = self.product_code_input.text().strip()
        if not text:
            return
        code = text
        if " | " in text:
            code = text.split(" | ")[0].strip()
        elif " - " in text:
            code = text.split(" - ")[0].strip()
            
        found_product = None
        for p in self.products_cache.values():
            if p.product_code == code:
                found_product = p
                break
        if found_product:
            self.product_code_input.setText(found_product.product_code)
            self.product_combo.select_product_id(found_product.id)
            self.update_rate_on_product_change()
            self.qty_input.setFocus()
            self.qty_input.selectAll()
        else:
            QMessageBox.warning(self, "Product Code Not Found", f"Product Code '{code}' Not Found.")
            self.product_code_input.selectAll()
            self.product_code_input.setFocus()

    def toggle_bank_account(self, mode=None):
        if mode is None:
            mode = self.pay_mode_combo.currentText()
        self.bank_combo.setEnabled(mode == "Bank")

    def on_gst_checkbox_changed(self):
        self.apply_gst_visibility()
        self.update_summary()

    def apply_gst_visibility(self):
        globally_enabled = getattr(self, 'gst_globally_enabled', False)
        
        self.gst_enabled_label.setVisible(globally_enabled)
        self.gst_enabled_checkbox.setVisible(globally_enabled)
        if hasattr(self, 'gst_top_container'):
            self.gst_top_container.setVisible(globally_enabled)
        
        gst_active = globally_enabled and self.gst_enabled_checkbox.isChecked()
        
        self.gst_rate_label.setVisible(gst_active)
        self.gst_rate_combo.setVisible(gst_active)
        if hasattr(self, 'gst_item_container'):
            self.gst_item_container.setVisible(gst_active)
        
        self.setup_table_columns(gst_active)

    def setup_table_columns(self, gst_active):
        if gst_active:
            self.table.setColumnCount(9)
            self.table.setHorizontalHeaderLabels([
                "Code", "Name", "Qty", "Unit", "Rate (₹)", "GST %", "Tax (₹)", "Total (₹)", "Action"
            ])
            header = self.table.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.Interactive)
            header.setSectionResizeMode(1, QHeaderView.Stretch)
            self.table.setColumnWidth(0, 62)   # Code
            self.table.setColumnWidth(2, 45)   # Qty
            self.table.setColumnWidth(3, 50)   # Unit
            self.table.setColumnWidth(4, 75)   # Rate (₹)
            self.table.setColumnWidth(5, 54)   # GST %
            self.table.setColumnWidth(6, 68)   # Tax (₹)
            self.table.setColumnWidth(7, 78)   # Total (₹)
            header.setSectionResizeMode(8, QHeaderView.Fixed)
            self.table.setColumnWidth(8, 68)   # Action
        else:
            self.table.setColumnCount(7)
            self.table.setHorizontalHeaderLabels([
                "Code", "Name", "Qty", "Unit", "Rate (₹)", "Total (₹)", "Action"
            ])
            header = self.table.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.Interactive)
            header.setSectionResizeMode(1, QHeaderView.Stretch)
            self.table.setColumnWidth(0, 65)   # Code
            self.table.setColumnWidth(2, 48)   # Qty
            self.table.setColumnWidth(3, 54)   # Unit
            self.table.setColumnWidth(4, 78)   # Rate (₹)
            self.table.setColumnWidth(5, 84)   # Total (₹)
            header.setSectionResizeMode(6, QHeaderView.Fixed)
            self.table.setColumnWidth(6, 68)   # Action

    def add_item_to_list(self):
        prod_idx = self.product_combo.currentIndex()
        if prod_idx < 0:
            return

        prod_id = self.product_combo.currentData()
        qty = self.qty_input.value()
        unit = self.unit_combo.currentText()
        rate = self.rate_input.value()
        disc = self.discount_input.value() if hasattr(self, 'discount_input') else 0.0

        gst_active = getattr(self, 'gst_globally_enabled', False) and self.gst_enabled_checkbox.isChecked()
        if gst_active:
            gst_rate_text = self.gst_rate_combo.currentText().replace("%", "")
            gst_rate = float(gst_rate_text)
        else:
            gst_rate = 0.0

        taxable_value = qty * rate
        tax_amount = taxable_value * (gst_rate / 100.0)

        # Retrieve cached stock limit
        p_cache = self.products_cache.get(prod_id)
        if not p_cache:
            return
            
        current_added_qty = 0
        for item in self.invoice_items:
            if item["product_id"] == prod_id:
                current_added_qty += item["qty"]

        # If editing, we should account for the stock quantity already allocated in this invoice!
        # Find how much was originally allocated in this invoice if it's an edit
        original_allocated = 0
        if self.editing_sales_id:
            session = Session()
            try:
                old_items = session.query(SalesItem).filter_by(sales_id=self.editing_sales_id, product_id=prod_id).all()
                for old_item in old_items:
                    original_allocated += old_item.qty
            finally:
                session.close()

        # Net stock limit check
        effective_stock = p_cache.stock_qty + original_allocated
        if (current_added_qty + qty) > effective_stock:
            QMessageBox.warning(
                self, 
                "Stock Alert", 
                f"Insufficient stock for {p_cache.name}!\nAvailable: {effective_stock}\nRequested: {current_added_qty + qty}"
            )
            return

        # Check if already added (match by product_id AND unit AND gst_rate)
        for item in self.invoice_items:
            if item["product_id"] == prod_id and item.get("unit") == unit and item.get("gst_rate", 0.0) == gst_rate:
                item["qty"] += qty
                item["rate"] = rate  
                item["discount"] = disc
                item["taxable_value"] = (item["qty"] * rate) - disc
                item["tax_amount"] = item["taxable_value"] * (gst_rate / 100.0)
                self.update_table()
                self.reset_item_inputs()
                return

        self.invoice_items.append({
            "product_id": prod_id,
            "product_code": p_cache.product_code if p_cache.product_code else "-",
            "name": p_cache.name,
            "qty": qty,
            "unit": unit,
            "rate": rate,
            "discount": disc,
            "gst_rate": gst_rate,
            "tax_amount": tax_amount,
            "taxable_value": taxable_value - disc
        })
        
        self.update_table()
        self.reset_item_inputs()

    def reset_item_inputs(self):
        self.product_code_input.clear()
        self.product_combo.blockSignals(True)
        self.product_combo.setCurrentIndex(-1)
        if self.product_combo.lineEdit():
            self.product_combo.lineEdit().clear()
        self.product_combo.blockSignals(False)
        self.qty_input.setValue(1)
        self.rate_input.setValue(0.0)
        if hasattr(self, 'discount_input'):
            self.discount_input.setValue(0.0)
        if hasattr(self, 'add_product_btn'):
            self.add_product_btn.hide()
        QTimer.singleShot(0, self._focus_product_code)

    def _focus_product_code(self):
        self.product_code_input.setFocus()
        self.product_code_input.selectAll()

    def delete_item(self, row_idx):
        self.invoice_items.pop(row_idx)
        self.update_table()

    def update_table(self):
        gst_active = getattr(self, 'gst_globally_enabled', False) and self.gst_enabled_checkbox.isChecked()
        self.table.setRowCount(len(self.invoice_items))
        for i, item in enumerate(self.invoice_items):
            self.table.setItem(i, 0, QTableWidgetItem(item.get("product_code", "-")))
            self.table.setItem(i, 1, QTableWidgetItem(item["name"]))
            self.table.setItem(i, 2, QTableWidgetItem(str(item["qty"])))
            self.table.setItem(i, 3, QTableWidgetItem(item.get("unit", "Pcs")))
            self.table.setItem(i, 4, QTableWidgetItem(f"{item['rate']:.2f}"))
            
            if gst_active:
                gst_rate = item.get("gst_rate", 0.0)
                tax_amt = item.get("tax_amount", 0.0)
                subtotal = ((item["qty"] * item["rate"]) - item.get("discount", 0.0)) + tax_amt
                if subtotal < 0:
                    subtotal = 0.0
                
                self.table.setItem(i, 5, QTableWidgetItem(f"{gst_rate:.0f}%"))
                self.table.setItem(i, 6, QTableWidgetItem(f"{tax_amt:.2f}"))
                self.table.setItem(i, 7, QTableWidgetItem(f"{subtotal:.2f}"))

                # Delete button (centered wrapper container) at index 8
                btn_container = QWidget()
                btn_layout = QHBoxLayout(btn_container)
                btn_layout.setContentsMargins(4, 4, 4, 4)
                btn_layout.setSpacing(0)
                btn_layout.setAlignment(Qt.AlignCenter)

                del_btn = QPushButton("Delete")
                del_btn.setProperty("class", "btn-action-delete")
                del_btn.clicked.connect(lambda checked, idx=i: self.delete_item(idx))
                btn_layout.addWidget(del_btn)
                self.table.setCellWidget(i, 8, btn_container)
            else:
                subtotal = (item["qty"] * item["rate"]) - item.get("discount", 0.0)
                if subtotal < 0:
                    subtotal = 0.0
                self.table.setItem(i, 5, QTableWidgetItem(f"{subtotal:.2f}"))

                # Delete button (centered wrapper container) at index 6
                btn_container = QWidget()
                btn_layout = QHBoxLayout(btn_container)
                btn_layout.setContentsMargins(4, 4, 4, 4)
                btn_layout.setSpacing(0)
                btn_layout.setAlignment(Qt.AlignCenter)

                del_btn = QPushButton("Delete")
                del_btn.setProperty("class", "btn-action-delete")
                del_btn.clicked.connect(lambda checked, idx=i: self.delete_item(idx))
                btn_layout.addWidget(del_btn)
                self.table.setCellWidget(i, 6, btn_container)

        self.update_summary()

    def update_summary(self):
        gst_active = getattr(self, 'gst_globally_enabled', False) and self.gst_enabled_checkbox.isChecked()
        
        if gst_active:
            taxable_sum = sum((item["qty"] * item["rate"]) - item.get("discount", 0.0) for item in self.invoice_items)
            if taxable_sum < 0:
                taxable_sum = 0.0
            tax_sum = sum(item.get("tax_amount", 0.0) for item in self.invoice_items)
            total = taxable_sum + tax_sum
            
            self.total_lbl.setText(f"Taxable: ₹{format_inr(taxable_sum)} | GST: ₹{format_inr(tax_sum)} | Total: ₹{format_inr(total)}")
        else:
            total = sum((item["qty"] * item["rate"]) - item.get("discount", 0.0) for item in self.invoice_items)
            if total < 0:
                total = 0.0
            self.total_lbl.setText(f"Total Amount: ₹{format_inr(total)}")

        paid = self.paid_input.value()
        balance = total - paid
        if balance < 0:
            balance = 0.0
        self.balance_lbl.setText(f"Balance Receivable: ₹{format_inr(balance)}")

    def save_sales_invoice(self):
        invoice_no = self.invoice_input.text().strip()
        cust_id = self.customer_combo.currentData()
        
        if not invoice_no:
            QMessageBox.warning(self, "Validation Error", "Please enter Invoice Number.")
            return
        if not self.invoice_items:
            QMessageBox.warning(self, "Validation Error", "Please add at least one product to the invoice.")
            return

        # Determine if GST is active for this invoice (defaults to Local CGST+SGST)
        gst_active = self.gst_globally_enabled and self.gst_enabled_checkbox.isChecked()
        gst_type = "CGST+SGST"
        
        taxable_amount = 0.0
        total_cgst = 0.0
        total_sgst = 0.0
        total_igst = 0.0
        total_gst = 0.0

        if gst_active:
            for item in self.invoice_items:
                taxable = (item["qty"] * item["rate"]) - item.get("discount", 0.0)
                if taxable < 0:
                    taxable = 0.0
                gst_rate = item.get("gst_rate", 0.0)
                tax_amt = taxable * (gst_rate / 100.0)
                
                taxable_amount += taxable
                total_gst += tax_amt
                total_cgst += tax_amt / 2.0
                total_sgst += tax_amt / 2.0
            total = taxable_amount + total_gst
        else:
            total = sum((item["qty"] * item["rate"]) - item.get("discount", 0.0) for item in self.invoice_items)
            if total < 0:
                total = 0.0
            taxable_amount = total

        paid = self.paid_input.value()
        balance = total - paid
        if balance < 0:
            balance = 0.0

        date_q = self.date_input.date()
        bill_date = datetime.date(date_q.year(), date_q.month(), date_q.day())

        pay_mode = self.pay_mode_combo.currentText()
        bank_id = self.bank_combo.currentData() if pay_mode == "Bank" else None

        session = Session()
        try:
            if not cust_id:
                # Find or create default customer "Mr/Mss customer"
                default_cust = session.query(Customer).filter_by(name="Mr/Mss customer").first()
                if not default_cust:
                    default_cust = Customer(name="Mr/Mss customer", mobile="N/A", address="N/A")
                    session.add(default_cust)
                    session.flush()
                cust_id = default_cust.id

            if self.editing_sales_id:
                # 1. Fetch existing invoice
                sale = session.query(SalesMaster).get(self.editing_sales_id)
                if not sale:
                    QMessageBox.warning(self, "Error", "Invoice to update was not found.")
                    session.close()
                    return

                # 2. Revert Old Stock
                for item in sale.items:
                    prod = session.query(Product).get(item.product_id)
                    if prod:
                        prod.stock_qty += item.qty

                # 3. Revert Old Customer Balance
                old_customer = session.query(Customer).get(sale.customer_id)
                if old_customer:
                    old_customer.outstanding_balance -= sale.balance_receivable

                # 4. Revert Old Ledger Payments
                cash_txs = session.query(CashTransaction).filter_by(source_type='sale', source_id=sale.id).all()
                for tx in cash_txs:
                    session.delete(tx)

                bank_txs = session.query(BankTransaction).filter_by(source_type='sale', source_id=sale.id).all()
                for tx in bank_txs:
                    bank = session.query(BankAccount).get(tx.account_id)
                    if bank:
                        bank.balance -= tx.amount
                    session.delete(tx)

                # 5. Clear old sales items (they will be recreated)
                sale.items.clear()

                # 6. Check stock level availability for new quantities
                for item in self.invoice_items:
                    prod = session.query(Product).get(item["product_id"])
                    if prod.stock_qty < item["qty"]:
                        QMessageBox.warning(self, "Stock Level Error", f"Product {prod.name} ran out of stock! Available: {prod.stock_qty}")
                        session.rollback()
                        session.close()
                        return

                # 7. Update SalesMaster Details
                sale.date = bill_date
                sale.customer_id = cust_id
                sale.total_amount = total
                sale.paid_amount = paid
                sale.balance_receivable = balance
                sale.gst_enabled = gst_active
                sale.gst_type = "CGST+SGST"
                sale.taxable_amount = taxable_amount
                sale.total_cgst = total_cgst
                sale.total_sgst = total_sgst
                sale.total_igst = 0.0
                sale.total_gst = total_gst

            else:
                # Check duplicate invoice number
                existing = session.query(SalesMaster).filter_by(invoice_number=invoice_no).first()
                if existing:
                    QMessageBox.warning(self, "Duplicate Invoice", f"Invoice number {invoice_no} already exists.")
                    session.close()
                    return

                # Check stock quantities for final validation
                for item in self.invoice_items:
                    prod = session.query(Product).get(item["product_id"])
                    if prod.stock_qty < item["qty"]:
                        QMessageBox.warning(self, "Stock Level Error", f"Product {prod.name} ran out of stock! Available: {prod.stock_qty}")
                        session.close()
                        return

                # Save Sales Master
                sale = SalesMaster(
                    invoice_number=invoice_no,
                    date=bill_date,
                    customer_id=cust_id,
                    total_amount=total,
                    paid_amount=paid,
                    balance_receivable=balance,
                    gst_enabled=gst_active,
                    gst_type="CGST+SGST",
                    taxable_amount=taxable_amount,
                    total_cgst=total_cgst,
                    total_sgst=total_sgst,
                    total_igst=0.0,
                    total_gst=total_gst
                )
                session.add(sale)
                session.flush()  # Populates sale.id safely within the transaction

            # Save Sales Items & deduct stock
            pdf_items = []
            for item in self.invoice_items:
                g_rate = item.get("gst_rate", 0.0) if gst_active else 0.0
                taxable_val = (item["qty"] * item["rate"]) - item.get("discount", 0.0)
                if taxable_val < 0:
                    taxable_val = 0.0
                tax_amt = taxable_val * (g_rate / 100.0)
                
                cgst_amt = 0.0
                sgst_amt = 0.0
                igst_amt = 0.0
                if gst_active:
                    cgst_amt = tax_amt / 2.0
                    sgst_amt = tax_amt / 2.0

                s_item = SalesItem(
                    sales_id=sale.id,
                    product_id=item["product_id"],
                    qty=item["qty"],
                    rate=item["rate"],
                    discount=item["discount"],
                    unit=item.get("unit", "Pcs"),
                    gst_rate=g_rate,
                    cgst_amount=cgst_amt,
                    sgst_amount=sgst_amt,
                    igst_amount=igst_amt,
                    tax_amount=tax_amt,
                    taxable_value=taxable_val
                )
                session.add(s_item)

                prod = session.query(Product).get(item["product_id"])
                if prod:
                    prod.stock_qty -= item["qty"]
                    bm = getattr(prod, 'brand_model', None) or getattr(prod, 'brand', '') or ''
                    p_name = f"{prod.name} ({bm})" if bm else prod.name
                else:
                    p_name = f"Unknown Product (ID: {item['product_id']})"

                pdf_items.append({
                    "name": p_name,
                    "qty": f"{item['qty']} {item.get('unit', 'Pcs')}",
                    "rate": item["rate"],
                    "discount": item["discount"],
                    "gst_rate": g_rate,
                    "tax_amount": tax_amt,
                    "taxable_value": taxable_val,
                    "total": taxable_val + tax_amt
                })

            # Update Customer Outstanding Balance
            customer = session.query(Customer).get(cust_id)
            customer.outstanding_balance += balance

            # Ledger Book logging
            if paid > 0:
                desc = f"Payment for sales invoice {invoice_no}"
                if pay_mode == "Cash":
                    tx_cash = CashTransaction(
                        date=bill_date,
                        transaction_type='in',
                        amount=paid,
                        source_type='sale',
                        source_id=sale.id,
                        description=desc
                    )
                    session.add(tx_cash)
                else:
                    tx_bank = BankTransaction(
                        date=bill_date,
                        transaction_type='deposit',
                        account_id=bank_id,
                        amount=paid,
                        source_type='sale',
                        source_id=sale.id,
                        description=desc
                    )
                    session.add(tx_bank)
                    
                    # Add to bank account balance
                    bank = session.query(BankAccount).get(bank_id)
                    bank.balance += paid

            session.commit()

            # Retrieve Settings details for PDF Header
            s_name = session.query(Setting).filter_by(key='shop_name').first().value
            s_contact = session.query(Setting).filter_by(key='shop_contact').first().value
            s_address = session.query(Setting).filter_by(key='shop_address').first().value
            s_gst = session.query(Setting).filter_by(key='shop_gst').first().value
            s_logo_setting = session.query(Setting).filter_by(key='shop_logo').first()
            s_logo_val = s_logo_setting.value if s_logo_setting and s_logo_setting.value and os.path.exists(s_logo_setting.value) else None

            # Prepare Invoice PDF data
            pdf_data = {
                "shop_logo": s_logo_val,
                "shop_name": s_name,
                "shop_contact": s_contact,
                "shop_address": s_address,
                "shop_gst": s_gst,
                "invoice_number": invoice_no,
                "date": bill_date.strftime("%Y-%m-%d"),
                "customer_name": customer.name,
                "customer_mobile": customer.mobile,
                "customer_address": customer.address,
                "customer_gst": customer.gst,
                "items": pdf_items,
                "total_amount": total,
                "paid_amount": paid,
                "balance": balance,
                "gst_enabled": gst_active,
                "gst_type": "CGST+SGST",
                "taxable_amount": taxable_amount,
                "total_cgst": total_cgst,
                "total_sgst": total_sgst,
                "total_igst": total_igst,
                "total_gst": total_gst
            }

            # Prompt user to save PDF
            os.makedirs("invoices", exist_ok=True)
            default_path = os.path.abspath(f"invoices/{invoice_no}.pdf")
            
            # Generate PDF
            generate_sales_pdf(pdf_data, default_path)
            
            # Inform user
            QMessageBox.information(
                self, 
                "Success", 
                f"Sales invoice saved successfully!\nPDF Invoice generated at:\n{default_path}"
            )

            # Auto-open PDF on Windows
            try:
                os.startfile(default_path)
            except Exception as e:
                print(f"Could not auto-open PDF: {e}")

            # Reset page states
            self.editing_sales_id = None
            self.save_btn.setText("Save && Print Invoice")
            self.save_btn.setProperty("class", "btn-success")
            self.save_btn.style().unpolish(self.save_btn)
            self.save_btn.style().polish(self.save_btn)
            self.cancel_edit_btn.setVisible(False)
            if hasattr(self, 'save_bottom_btn'):
                self.save_bottom_btn.setText("Save && Print Invoice")
                self.save_bottom_btn.setProperty("class", "btn-success")
                self.save_bottom_btn.style().unpolish(self.save_bottom_btn)
                self.save_bottom_btn.style().polish(self.save_bottom_btn)
            if hasattr(self, 'cancel_bottom_btn'):
                self.cancel_bottom_btn.setVisible(False)
            self.invoice_input.setEnabled(True)

            self.invoice_items.clear()
            self.update_table()
            self.invoice_input.clear()
            self.pay_mode_combo.setCurrentText("Cash")
            self.toggle_bank_account("Cash")
            self.paid_input.setValue(0.0)
            self.qty_input.setValue(1)
            self.discount_input.setValue(0.0)
            self.refresh_data()

        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save invoice: {e}")
        finally:
            session.close()

    def reset_history_filters(self):
        self.history_search.clear()
        self.history_from_date.setDate(QDate.currentDate().addMonths(-1))
        self.history_to_date.setDate(QDate.currentDate())
        self.load_history()

    def handle_history_scroll(self, value):
        scrollbar = self.history_table.verticalScrollBar()
        if value == scrollbar.maximum() and scrollbar.maximum() > 0:
            if self.has_more_history:
                self.history_offset += 25
                self.load_history(reset=False)

    def load_history(self, reset=True):
        if not isinstance(reset, bool):
            reset = True
            
        if reset:
            self.history_offset = 0
            self.has_more_history = True
            self.history_table.setRowCount(0)

        session = Session()
        try:
            query = session.query(SalesMaster)
            
            # Apply date filters
            from_d = self.history_from_date.date()
            to_d = self.history_to_date.date()
            from_date = datetime.date(from_d.year(), from_d.month(), from_d.day())
            to_date = datetime.date(to_d.year(), to_d.month(), to_d.day())
            query = query.filter(SalesMaster.date >= from_date, SalesMaster.date <= to_date)
            
            # Apply search text filter
            search_text = self.history_search.text().strip()
            if search_text:
                # Join with Customer table to search by customer name
                query = query.join(Customer).filter(
                    (SalesMaster.invoice_number.ilike(f"%{search_text}%")) |
                    (Customer.name.ilike(f"%{search_text}%"))
                )
                
            invoices = query.order_by(SalesMaster.date.desc(), SalesMaster.id.desc()).offset(self.history_offset).limit(25).all()
            
            if len(invoices) < 25:
                self.has_more_history = False
                
            start_row = self.history_table.rowCount()
            self.history_table.setRowCount(start_row + len(invoices))
            for offset_idx, p in enumerate(invoices):
                i = start_row + offset_idx
                self.history_table.setItem(i, 0, QTableWidgetItem(p.invoice_number))
                self.history_table.setItem(i, 1, QTableWidgetItem(p.date.strftime("%Y-%m-%d")))
                self.history_table.setItem(i, 2, QTableWidgetItem(p.customer.name))
                self.history_table.setItem(i, 3, QTableWidgetItem(f"₹{format_inr(p.total_amount)}"))
                self.history_table.setItem(i, 4, QTableWidgetItem(f"₹{format_inr(p.paid_amount)}"))
                self.history_table.setItem(i, 5, QTableWidgetItem(f"₹{format_inr(p.balance_receivable)}"))
                
                # Action Buttons
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(6, 4, 6, 4)
                actions_layout.setSpacing(8)
                actions_layout.setAlignment(Qt.AlignCenter)
                
                view_btn = QPushButton("View")
                view_btn.setProperty("class", "btn-action-view")
                view_btn.clicked.connect(lambda checked, sid=p.id: self.view_invoice_details(sid))
                actions_layout.addWidget(view_btn)
                
                edit_btn = QPushButton("Edit")
                edit_btn.setProperty("class", "btn-action-edit")
                edit_btn.clicked.connect(lambda checked, sid=p.id: self.edit_sales_invoice(sid))
                actions_layout.addWidget(edit_btn)
                
                del_btn = QPushButton("Delete")
                del_btn.setProperty("class", "btn-action-delete")
                del_btn.clicked.connect(lambda checked, sid=p.id: self.delete_sales_invoice(sid))
                actions_layout.addWidget(del_btn)
                
                self.history_table.setCellWidget(i, 6, actions_widget)
                
        except Exception as e:
            print(f"Error loading sales history: {e}")
        finally:
            session.close()

    def view_invoice_details(self, sale_id):
        session = Session()
        try:
            sale = session.query(SalesMaster).get(sale_id)
            if not sale:
                QMessageBox.warning(self, "Error", "Invoice not found.")
                return

            dialog = QDialog(self)
            dialog.setWindowTitle(f"Invoice Details - {sale.invoice_number}")
            dialog.setMinimumSize(600, 450)
            
            dlg_layout = QVBoxLayout(dialog)
            
            # Header info
            info_frame = QFrame()
            info_frame.setProperty("class", "CardFrame")
            info_layout = QFormLayout(info_frame)
            info_layout.addRow("Invoice Number:", QLabel(sale.invoice_number))
            info_layout.addRow("Date:", QLabel(sale.date.strftime("%Y-%m-%d")))
            cust_name = sale.customer.name if sale.customer else "Unknown Customer (Deleted)"
            cust_mobile = sale.customer.mobile if sale.customer else "N/A"
            info_layout.addRow("Customer Name:", QLabel(cust_name))
            info_layout.addRow("Customer Contact:", QLabel(cust_mobile))
            dlg_layout.addWidget(info_frame)
            
            # Items table
            items_table = QTableWidget()
            items_table.setColumnCount(7)
            items_table.setHorizontalHeaderLabels(["Code", "Name", "Qty", "Unit", "Rate (₹)", "Discount (₹)", "Total (₹)"])
            header = items_table.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.Interactive)
            header.setSectionResizeMode(1, QHeaderView.Stretch)
            items_table.setColumnWidth(0, 70)
            items_table.setColumnWidth(2, 50)
            items_table.setColumnWidth(3, 55)
            items_table.setColumnWidth(4, 80)
            items_table.setColumnWidth(5, 80)
            items_table.setColumnWidth(6, 85)
            items_table.verticalHeader().setVisible(False)
            
            items = session.query(SalesItem).filter_by(sales_id=sale_id).all()
            items_table.setRowCount(len(items))
            for i, item in enumerate(items):
                p_code = item.product.product_code if item.product else "-"
                if item.product:
                    bm = getattr(item.product, 'brand_model', None) or getattr(item.product, 'brand', '') or ''
                    display_name = f"{item.product.name} ({bm})" if bm else item.product.name
                else:
                    display_name = f"Unknown Product (ID: {item.product_id})"
                items_table.setItem(i, 0, QTableWidgetItem(p_code))
                items_table.setItem(i, 1, QTableWidgetItem(display_name))
                items_table.setItem(i, 2, QTableWidgetItem(str(item.qty)))
                items_table.setItem(i, 3, QTableWidgetItem(getattr(item, 'unit', 'Pcs') or 'Pcs'))
                items_table.setItem(i, 4, QTableWidgetItem(f"{item.rate:.2f}"))
                items_table.setItem(i, 5, QTableWidgetItem(f"{item.discount:.2f}"))
                subtotal = (item.qty * item.rate) - item.discount
                items_table.setItem(i, 6, QTableWidgetItem(f"{subtotal:.2f}"))
                
            dlg_layout.addWidget(items_table)
            
            # Totals
            totals_frame = QFrame()
            totals_layout = QFormLayout(totals_frame)
            totals_layout.addRow("Total Amount:", QLabel(f"₹{format_inr(sale.total_amount)}"))
            totals_layout.addRow("Paid Amount:", QLabel(f"₹{format_inr(sale.paid_amount)}"))
            totals_layout.addRow("Balance Receivable:", QLabel(f"₹{format_inr(sale.balance_receivable)}"))
            dlg_layout.addWidget(totals_frame)
            
            # Bottom Buttons (Print Invoice & Close)
            btn_layout = QHBoxLayout()
            btn_layout.addStretch()
            
            print_btn = QPushButton("Print Invoice")
            print_btn.clicked.connect(lambda: self.print_sales_invoice(sale_id))
            btn_layout.addWidget(print_btn)
            
            close_btn = QPushButton("Close")
            close_btn.setProperty("class", "btn-secondary")
            close_btn.clicked.connect(dialog.accept)
            btn_layout.addWidget(close_btn)
            
            dlg_layout.addLayout(btn_layout)
            
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load invoice details: {e}")
        finally:
            session.close()

    def print_sales_invoice(self, sale_id):
        session = Session()
        try:
            sale = session.query(SalesMaster).get(sale_id)
            if not sale:
                QMessageBox.warning(self, "Error", "Invoice not found.")
                return
                
            # Retrieve Settings details
            s_name = session.query(Setting).filter_by(key='shop_name').first().value
            s_contact = session.query(Setting).filter_by(key='shop_contact').first().value
            s_address = session.query(Setting).filter_by(key='shop_address').first().value
            s_gst = session.query(Setting).filter_by(key='shop_gst').first().value

            # Prepare items list
            pdf_items = []
            gst_active = getattr(sale, 'gst_enabled', False) or False
            for item in sale.items:
                if item.product:
                    bm = getattr(item.product, 'brand_model', None) or getattr(item.product, 'brand', '') or ''
                    p_name = f"{item.product.name} ({bm})" if bm else item.product.name
                else:
                    p_name = f"Unknown Product (ID: {item.product_id})"

                g_rate = getattr(item, 'gst_rate', 0.0) or 0.0
                tax_amt = getattr(item, 'tax_amount', 0.0) or 0.0
                taxable_val = getattr(item, 'taxable_value', (item.qty * item.rate) - item.discount) or ((item.qty * item.rate) - item.discount)

                pdf_items.append({
                    "name": p_name,
                    "qty": f"{item.qty} {getattr(item, 'unit', 'Pcs') or 'Pcs'}",
                    "rate": item.rate,
                    "discount": item.discount,
                    "gst_rate": g_rate,
                    "tax_amount": tax_amt,
                    "taxable_value": taxable_val,
                    "total": (taxable_val + tax_amt) if gst_active else ((item.qty * item.rate) - item.discount)
                })

            s_logo_setting = session.query(Setting).filter_by(key='shop_logo').first()
            s_logo_val = s_logo_setting.value if s_logo_setting and s_logo_setting.value and os.path.exists(s_logo_setting.value) else None

            # Prepare Invoice PDF data
            pdf_data = {
                "shop_logo": s_logo_val,
                "shop_name": s_name,
                "shop_contact": s_contact,
                "shop_address": s_address,
                "shop_gst": s_gst,
                "invoice_number": sale.invoice_number,
                "date": sale.date.strftime("%Y-%m-%d"),
                "customer_name": sale.customer.name,
                "customer_mobile": sale.customer.mobile,
                "customer_address": sale.customer.address,
                "customer_gst": sale.customer.gst,
                "items": pdf_items,
                "total_amount": sale.total_amount,
                "paid_amount": sale.paid_amount,
                "balance": sale.balance_receivable,
                "gst_enabled": gst_active,
                "gst_type": getattr(sale, 'gst_type', 'CGST+SGST') or 'CGST+SGST',
                "taxable_amount": getattr(sale, 'taxable_amount', sale.total_amount) or sale.total_amount,
                "total_cgst": getattr(sale, 'total_cgst', 0.0) or 0.0,
                "total_sgst": getattr(sale, 'total_sgst', 0.0) or 0.0,
                "total_igst": getattr(sale, 'total_igst', 0.0) or 0.0,
                "total_gst": getattr(sale, 'total_gst', 0.0) or 0.0
            }

            os.makedirs("invoices", exist_ok=True)
            path = os.path.abspath(f"invoices/{sale.invoice_number}.pdf")
            generate_sales_pdf(pdf_data, path)
            
            QMessageBox.information(self, "Success", f"Invoice PDF generated at:\n{path}")
            
            # Auto-open
            try:
                os.startfile(path)
            except Exception as e:
                print(f"Could not auto-open PDF: {e}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to print/generate PDF: {e}")
        finally:
            session.close()

    def delete_sales_invoice(self, sale_id):
        confirm = QMessageBox.question(
            self, "Confirm Delete", 
            "Are you sure you want to delete this invoice?\nAll inventory stock and customer outstanding adjustments will be reverted.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return
            
        session = Session()
        try:
            sale = session.query(SalesMaster).get(sale_id)
            if not sale:
                QMessageBox.warning(self, "Error", "Invoice not found.")
                session.close()
                return
                
            # Revert inventory stock
            for item in sale.items:
                prod = session.query(Product).get(item.product_id)
                if prod:
                    prod.stock_qty += item.qty
                    
            # Revert customer outstanding balance
            customer = session.query(Customer).get(sale.customer_id)
            if customer:
                customer.outstanding_balance -= sale.balance_receivable
                
            # Revert/delete ledger entries (CashTransaction/BankTransaction)
            cash_txs = session.query(CashTransaction).filter_by(source_type='sale', source_id=sale.id).all()
            for tx in cash_txs:
                session.delete(tx)
                
            bank_txs = session.query(BankTransaction).filter_by(source_type='sale', source_id=sale.id).all()
            for tx in bank_txs:
                # Revert bank account balance
                bank = session.query(BankAccount).get(tx.account_id)
                if bank:
                    bank.balance -= tx.amount
                session.delete(tx)
                
            # Delete payments logged against this sales invoice
            from models import Payment
            payments = session.query(Payment).filter_by(sales_id=sale.id).all()
            for p_rec in payments:
                # Revert CashTransaction and BankTransaction of the payment
                p_cash_txs = session.query(CashTransaction).filter_by(source_type='payment', source_id=p_rec.id).all()
                for tx in p_cash_txs:
                    session.delete(tx)
                p_bank_txs = session.query(BankTransaction).filter_by(source_type='payment', source_id=p_rec.id).all()
                for tx in p_bank_txs:
                    bank = session.query(BankAccount).get(tx.account_id)
                    if bank:
                        bank.balance -= tx.amount
                    session.delete(tx)
                session.delete(p_rec)

            # Delete SalesMaster (which cascades to delete SalesItems)
            session.delete(sale)
            
            session.commit()
            QMessageBox.information(self, "Success", "Invoice deleted and related records reverted successfully.")
            self.load_history()
            self.refresh_data()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to delete invoice: {e}")
        finally:
            session.close()

    def edit_sales_invoice(self, sale_id):
        session = Session()
        try:
            sale = session.query(SalesMaster).get(sale_id)
            if not sale:
                QMessageBox.warning(self, "Error", "Invoice not found.")
                return
                
            # Switch to entry tab
            self.tabs.setCurrentIndex(0)
            
            # Set editing states
            self.editing_sales_id = sale.id
            self.save_btn.setText("Update & Print Invoice")
            self.save_btn.setProperty("class", "btn-warning")
            self.save_btn.style().unpolish(self.save_btn)
            self.save_btn.style().polish(self.save_btn)
            
            self.cancel_edit_btn.setVisible(True)
            
            # Load invoice parameters
            self.invoice_input.setText(sale.invoice_number)
            self.invoice_input.setEnabled(False)  # Disabled to preserve identifier integrity
            
            self.date_input.setDate(QDate(sale.date.year, sale.date.month, sale.date.day))
            
            # Set customer
            idx = self.customer_combo.findData(sale.customer_id)
            if idx >= 0:
                self.customer_combo.setCurrentIndex(idx)
                
            # Set payment mode
            cash_tx = session.query(CashTransaction).filter_by(source_type='sale', source_id=sale.id).first()
            bank_tx = session.query(BankTransaction).filter_by(source_type='sale', source_id=sale.id).first()
            
            if bank_tx:
                self.pay_mode_combo.setCurrentText("Bank")
                self.bank_combo.setEnabled(True)
                b_idx = self.bank_combo.findData(bank_tx.account_id)
                if b_idx >= 0:
                    self.bank_combo.setCurrentIndex(b_idx)
            else:
                self.pay_mode_combo.setCurrentText("Cash")
                self.bank_combo.setEnabled(False)
                
            self.paid_input.setValue(sale.paid_amount)
            
            # Load GST settings
            is_gst = getattr(sale, 'gst_enabled', False) or False
            self.gst_enabled_checkbox.setChecked(is_gst)

            # Load items
            self.invoice_items = []
            for item in sale.items:
                self.invoice_items.append({
                    "product_id": item.product_id,
                    "product_code": item.product.product_code if item.product else "-",
                    "name": item.product.name if item.product else f"Unknown Product (ID: {item.product_id})",
                    "qty": item.qty,
                    "unit": getattr(item, 'unit', 'Pcs') or 'Pcs',
                    "rate": item.rate,
                    "discount": item.discount,
                    "gst_rate": getattr(item, 'gst_rate', 0.0) or 0.0,
                    "tax_amount": getattr(item, 'tax_amount', 0.0) or 0.0,
                    "taxable_value": getattr(item, 'taxable_value', (item.qty * item.rate) - item.discount) or ((item.qty * item.rate) - item.discount)
                })
                
            self.apply_gst_visibility()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load invoice for editing: {e}")
        finally:
            session.close()

    def cancel_edit_mode(self):
        self.editing_sales_id = None
        self.save_btn.setText("Save && Print Invoice")
        self.save_btn.setProperty("class", "btn-success")
        self.save_btn.style().unpolish(self.save_btn)
        self.save_btn.style().polish(self.save_btn)
        self.cancel_edit_btn.setVisible(False)
        if hasattr(self, 'save_bottom_btn'):
            self.save_bottom_btn.setText("Save && Print Invoice")
            self.save_bottom_btn.setProperty("class", "btn-success")
            self.save_bottom_btn.style().unpolish(self.save_bottom_btn)
            self.save_bottom_btn.style().polish(self.save_bottom_btn)
        if hasattr(self, 'cancel_bottom_btn'):
            self.cancel_bottom_btn.setVisible(False)
        self.invoice_input.setEnabled(True)
        
        # Clear fields
        self.invoice_items.clear()
        self.update_table()
        self.invoice_input.clear()
        self.pay_mode_combo.setCurrentText("Cash")
        self.toggle_bank_account("Cash")
        self.paid_input.setValue(0.0)
        self.qty_input.setValue(1)
        self.discount_input.setValue(0.0)
        self.refresh_data()
