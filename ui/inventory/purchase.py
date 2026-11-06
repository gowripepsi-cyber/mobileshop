import datetime
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QComboBox, 
                             QDateEdit, QSpinBox, QDoubleSpinBox, QPushButton, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QMessageBox, QFrame, QFormLayout,
                             QTabWidget, QDialog, QDialogButtonBox, QCompleter, QCheckBox)
from PySide6.QtCore import Qt, QDate, QTimer
from utils.formatters import format_inr
from database import Session, Setting
from models import Supplier, Product, BankAccount, PurchaseMaster, PurchaseItem, CashTransaction, BankTransaction, Category
from utils.pdf_generator import generate_purchase_pdf
from utils.ui_helpers import enable_quick_add_auto_select, enable_auto_clear_and_expand, SearchableProductComboBox, SearchableComboBox, AutoClearSearchableComboBox

class PurchaseView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bill_items = []  # list of dicts: {"product_id": int, "name": str, "qty": int, "rate": float}
        self.editing_purchase_id = None  # Tracks if we are editing a purchase bill
        self.products_cache = {}
        self.gst_globally_enabled = False
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Tabs for operations
        self.tabs = QTabWidget()

        # Tab 1: New Purchase Entry
        self.entry_tab = QWidget()
        self.setup_entry_tab()
        self.tabs.addTab(self.entry_tab, "New Purchase Entry")

        # Tab 2: Purchase Invoice History
        self.history_tab = QWidget()
        self.setup_history_tab()
        self.tabs.addTab(self.history_tab, "Purchase Invoice History")

        # Tab 3 & 4: Purchase Return Entry & History
        from ui.inventory.purchase_return import PurchaseReturnEntryWidget, PurchaseReturnHistoryWidget
        self.return_history_tab = PurchaseReturnHistoryWidget(self)
        self.return_entry_tab = PurchaseReturnEntryWidget(self, self.return_history_tab)
        self.tabs.addTab(self.return_entry_tab, "New Purchase Return")
        self.tabs.addTab(self.return_history_tab, "Purchase Return History")

        layout.addWidget(self.tabs)

    def setup_entry_tab(self):
        # Vertical stacked layout: Top = Block 1 (Purchase Invoice Parameters), Bottom = Block 2 (Items Entry & Table)
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
        # BLOCK 1 (Top Block): Purchase Invoice Parameters Card
        # =========================================================================
        top_panel = QFrame()
        top_panel.setProperty("class", "CardFrame")
        top_layout = QVBoxLayout(top_panel)
        top_layout.setContentsMargins(16, 12, 16, 12)
        top_layout.setSpacing(10)

        # Header Row: Title & Upload Existing Stock shortcut button
        top_title_row = QHBoxLayout()
        top_title_row.setContentsMargins(0, 0, 0, 0)
        title_lbl = QLabel("Purchase Invoice Details")
        title_lbl.setStyleSheet("font-size: 14.5px; font-weight: bold; color: #0f172a;")
        top_title_row.addWidget(title_lbl)
        top_title_row.addStretch()

        self.goto_stock_btn = QPushButton("📦 Upload Existing Stock")
        self.goto_stock_btn.setToolTip("Switch to Upload Existing Stock / Opening Inventory")
        self.goto_stock_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: #ffffff;
                font-size: 11.5px;
                font-weight: 600;
                border: none;
                border-radius: 6px;
                padding: 5px 12px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        self.goto_stock_btn.setCursor(Qt.PointingHandCursor)
        self.goto_stock_btn.clicked.connect(self.switch_to_existing_stock)
        top_title_row.addWidget(self.goto_stock_btn)
        top_layout.addLayout(top_title_row)

        # Grid for Block 1 (4 Columns x 2 Rows)
        top_grid = QGridLayout()
        top_grid.setContentsMargins(0, 0, 0, 0)
        top_grid.setHorizontalSpacing(14)
        top_grid.setVerticalSpacing(8)

        top_grid.setColumnStretch(0, 1)
        top_grid.setColumnStretch(1, 1)
        top_grid.setColumnStretch(2, 2)
        top_grid.setColumnStretch(3, 1)

        # 1. Invoice Number (Supplier Invoice / Bill No.)
        self.invoice_input = QLineEdit()
        self.invoice_input.setPlaceholderText("Enter Supplier Invoice No.")
        self.invoice_input.setStyleSheet(input_style)
        f_invoice = make_field("Supplier Invoice No. *", self.invoice_input)

        # 2. Invoice Date
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setStyleSheet(input_style)
        f_date = make_field("Invoice Date", self.date_input)

        # 3. Supplier (combo + add button)
        self.supplier_combo = AutoClearSearchableComboBox()
        self.supplier_combo.currentTextChanged.connect(self.check_supplier_match)
        if self.supplier_combo.lineEdit():
            self.supplier_combo.lineEdit().textChanged.connect(self.check_supplier_match)

        self.add_supplier_btn = QPushButton("+")
        self.add_supplier_btn.setToolTip("Add new supplier")
        self.add_supplier_btn.setProperty("class", "btn-quick-add")
        self.add_supplier_btn.setStyleSheet("min-height: 36px; max-height: 36px; margin: 0px; padding: 0px; font-size: 18px; font-weight: bold; border-radius: 6px;")
        self.add_supplier_btn.setFixedWidth(34)
        self.add_supplier_btn.setCursor(Qt.PointingHandCursor)
        self.add_supplier_btn.clicked.connect(self.handle_add_supplier_click)
        self.add_supplier_btn.hide()

        supp_widget = QWidget()
        supp_layout = QHBoxLayout(supp_widget)
        supp_layout.setContentsMargins(0, 0, 0, 0)
        supp_layout.setSpacing(4)
        supp_layout.addWidget(self.supplier_combo, 1)
        supp_layout.addWidget(self.add_supplier_btn)
        f_supp = make_field("Supplier *", supp_widget)

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
        self.save_btn = QPushButton("Save Purchase Bill")
        self.save_btn.setProperty("class", "btn-success")
        self.save_btn.setStyleSheet("min-height: 36px; max-height: 36px; padding: 0px 14px; font-weight: bold; border-radius: 6px;")
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.clicked.connect(self.save_purchase)

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

        # Row 0: Invoice Number, Date, Supplier, Tax Invoice
        top_grid.addWidget(f_invoice, 0, 0)
        top_grid.addWidget(f_date, 0, 1)
        top_grid.addWidget(f_supp, 0, 2)
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

        # Section Header
        entry_title = QLabel("Add Items to Bill")
        entry_title.setStyleSheet("font-size: 13.5px; font-weight: bold; color: #0f172a;")
        bottom_layout.addWidget(entry_title)

        # Hidden brand/model inputs
        self.brand_input = QLineEdit()
        self.brand_input.hide()
        self.model_input = QLineEdit()
        self.model_input.hide()

        # Item Entry Row (Clean single horizontal row matching Existing Stock design)
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
        self.category_combo = AutoClearSearchableComboBox()
        self.category_combo.setPlaceholderText("Select Category")
        self.category_combo.currentIndexChanged.connect(self.filter_products_by_category)
        self.category_combo.currentTextChanged.connect(self.filter_products_by_category)
        self.category_combo.activated.connect(self.filter_products_by_category)
        if self.category_combo.lineEdit():
            self.category_combo.lineEdit().textChanged.connect(self.filter_products_by_category)
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
        f_prate = make_field("Rate (₹)", self.rate_input, width=85)
        item_row.addWidget(f_prate)

        # 7. Selling Price
        self.selling_price_input = QDoubleSpinBox()
        self.selling_price_input.setRange(0.0, 9999999.0)
        self.selling_price_input.setValue(0.0)
        self.selling_price_input.setDecimals(2)
        self.selling_price_input.setStyleSheet(input_style)
        self.selling_price_label = QLabel("Selling Price:")
        f_psell = make_field("Selling Price (₹)", self.selling_price_input, width=90)
        item_row.addWidget(f_psell)

        # 8. GST % (Container)
        self.gst_rate_label = QLabel("GST %:")
        self.gst_rate_combo = QComboBox()
        self.gst_rate_combo.addItems(["0%", "5%", "12%", "18%", "28%"])
        self.gst_rate_combo.setCurrentText("18%")
        self.gst_rate_combo.setStyleSheet(input_style)

        self.gst_item_container = make_field("GST %", self.gst_rate_combo, width=75)
        item_row.addWidget(self.gst_item_container)

        # 9. Add Item Button
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

        self.balance_lbl = QLabel("Balance Payable: ₹0.00")
        self.balance_lbl.setStyleSheet("font-size: 14.5px; font-weight: bold; color: #dc2626;")

        summary_bar.addWidget(self.total_lbl)
        summary_bar.addWidget(self.balance_lbl)
        summary_bar.addStretch()

        self.save_bottom_btn = QPushButton("Save Purchase Bill")
        self.save_bottom_btn.setProperty("class", "btn-success")
        self.save_bottom_btn.setStyleSheet("min-height: 34px; padding: 0px 16px; font-weight: bold; border-radius: 6px;")
        self.save_bottom_btn.setCursor(Qt.PointingHandCursor)
        self.save_bottom_btn.clicked.connect(self.save_purchase)
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
        self.history_search.setPlaceholderText("Invoice # or Supplier name...")
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
            "Invoice #", "Date", "Supplier Name", "Total (₹)", "Paid (₹)", "Balance (₹)", "Actions"
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
    def load_suppliers(self, select_supplier_id=None):
        curr_id = select_supplier_id if select_supplier_id is not None else self.supplier_combo.currentData()
        self.supplier_combo.blockSignals(True)
        self.supplier_combo.clear()
        self.supplier_combo.addItem("-- Select Supplier / Cash --", None)
        session = Session()
        try:
            suppliers = session.query(Supplier).all()
            for s in suppliers:
                self.supplier_combo.addItem(s.name, s.id)
        except Exception as e:
            print(f"Error loading suppliers: {e}")
        finally:
            session.close()

        self.supplier_combo.update_completer()
        self.supplier_combo.blockSignals(False)

        if curr_id is not None:
            idx = self.supplier_combo.findData(curr_id)
            if idx >= 0:
                self.supplier_combo.setCurrentIndex(idx)
        else:
            self.supplier_combo.setCurrentIndex(0)
        if hasattr(self, 'add_supplier_btn'):
            self.check_supplier_match()

    def check_supplier_match(self):
        text = self.supplier_combo.currentText().strip()
        if not text or text == "-- Select Supplier / Cash --":
            self.add_supplier_btn.hide()
            return
        
        matched = False
        for i in range(self.supplier_combo.count()):
            item_text = self.supplier_combo.itemText(i).strip()
            if item_text and item_text != "-- Select Supplier / Cash --" and item_text.lower() == text.lower():
                matched = True
                if self.supplier_combo.currentIndex() != i:
                    self.supplier_combo.blockSignals(True)
                    self.supplier_combo.setCurrentIndex(i)
                    self.supplier_combo.blockSignals(False)
                break
        
        if not matched:
            self.add_supplier_btn.show()
        else:
            self.add_supplier_btn.hide()

    def handle_add_supplier_click(self):
        from ui.masters.suppliers import SupplierDialog
        typed_text = self.supplier_combo.currentText().strip()
        if typed_text == "-- Select Supplier / Cash --":
            typed_text = ""
        dlg = SupplierDialog(initial_name=typed_text, parent=self)
        if dlg.exec() == QDialog.Accepted and hasattr(dlg, 'saved_supplier_id'):
            self.load_suppliers(select_supplier_id=dlg.saved_supplier_id)

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

    def filter_products_by_category(self, *args):
        if not hasattr(self, 'products_cache') or not self.products_cache:
            return
            
        cat_name = self.category_combo.currentText().strip()
        cat_lower = cat_name.lower()
        
        is_all = not cat_lower or cat_lower in ("-- all categories --", "select category", "all")
        
        filtered_products = []
        if is_all:
            filtered_products = list(self.products_cache.values())
            placeholder = "Select Product"
        else:
            for prod_id, p in self.products_cache.items():
                p_cat = (p.category or "").strip().lower()
                if p_cat == cat_lower:
                    filtered_products.append(p)
                elif "spare" in cat_lower and "spare" in p_cat:
                    filtered_products.append(p)
                elif cat_lower and (cat_lower in p_cat or p_cat in cat_lower):
                    filtered_products.append(p)
            
            placeholder = f"Select {cat_name} Item..."

        self.product_combo.set_products(filtered_products)
        self.product_combo.setPlaceholderText(placeholder)
        if self.product_combo.lineEdit():
            self.product_combo.lineEdit().setPlaceholderText(placeholder)
            
        self.update_rate_on_product_change()
        if hasattr(self, 'add_product_btn'):
            self.check_product_match()

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

            # Save previous category selection if any
            prev_cat = self.category_combo.currentText().strip()

            # 2. Block combo box signals during update
            self.supplier_combo.blockSignals(True)
            self.category_combo.blockSignals(True)
            if self.category_combo.lineEdit():
                self.category_combo.lineEdit().blockSignals(True)
            self.bank_combo.blockSignals(True)

            # Load Suppliers
            self.load_suppliers()

            # Load Categories
            self.category_combo.clear()
            self.category_combo.addItem("-- All Categories --")
            categories = session.query(Category).all()
            for c in categories:
                self.category_combo.addItem(c.name)
            
            if prev_cat and prev_cat != "-- All Categories --":
                cat_idx = -1
                for i in range(self.category_combo.count()):
                    if self.category_combo.itemText(i).strip().lower() == prev_cat.lower():
                        cat_idx = i
                        break
                if cat_idx >= 0:
                    self.category_combo.setCurrentIndex(cat_idx)
                else:
                    self.category_combo.setCurrentIndex(-1)
            else:
                self.category_combo.setCurrentIndex(-1)
                
            self.category_combo.update_completer()

            # Load Bank Accounts
            self.bank_combo.clear()
            banks = session.query(BankAccount).all()
            for b in banks:
                self.bank_combo.addItem(f"{b.bank_name} ({b.account_name})", b.id)

            # Supplier invoice number is provided by supplier on the bill; left as an empty text box

            # 3. Unblock signals and filter/load
            self.supplier_combo.blockSignals(False)
            self.category_combo.blockSignals(False)
            if self.category_combo.lineEdit():
                self.category_combo.lineEdit().blockSignals(False)
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
            print(f"Error loading purchase options: {e}")
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
            query = session.query(PurchaseMaster)
            
            # Apply date filters
            from_d = self.history_from_date.date()
            to_d = self.history_to_date.date()
            from_date = datetime.date(from_d.year(), from_d.month(), from_d.day())
            to_date = datetime.date(to_d.year(), to_d.month(), to_d.day())
            query = query.filter(PurchaseMaster.date >= from_date, PurchaseMaster.date <= to_date)
            
            # Apply search text filter
            search_text = self.history_search.text().strip()
            if search_text:
                # Join with Supplier table to search by supplier name
                query = query.join(Supplier).filter(
                    (PurchaseMaster.invoice_number.ilike(f"%{search_text}%")) |
                    (Supplier.name.ilike(f"%{search_text}%"))
                )
                
            purchases = query.order_by(PurchaseMaster.date.desc(), PurchaseMaster.id.desc()).offset(self.history_offset).limit(25).all()
            
            if len(purchases) < 25:
                self.has_more_history = False
                
            start_row = self.history_table.rowCount()
            self.history_table.setRowCount(start_row + len(purchases))
            for offset_idx, p in enumerate(purchases):
                i = start_row + offset_idx
                self.history_table.setItem(i, 0, QTableWidgetItem(p.invoice_number))
                self.history_table.setItem(i, 1, QTableWidgetItem(p.date.strftime("%Y-%m-%d")))
                self.history_table.setItem(i, 2, QTableWidgetItem(p.supplier.name))
                self.history_table.setItem(i, 3, QTableWidgetItem(f"₹{format_inr(p.total_amount)}"))
                self.history_table.setItem(i, 4, QTableWidgetItem(f"₹{format_inr(p.paid_amount)}"))
                self.history_table.setItem(i, 5, QTableWidgetItem(f"₹{format_inr(p.balance_payable)}"))
                
                # Action Buttons
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(6, 4, 6, 4)
                actions_layout.setSpacing(8)
                actions_layout.setAlignment(Qt.AlignCenter)
                
                view_btn = QPushButton("View")
                view_btn.setProperty("class", "btn-action-view")
                view_btn.clicked.connect(lambda checked, pid=p.id: self.view_purchase_details(pid))
                actions_layout.addWidget(view_btn)
                
                edit_btn = QPushButton("Edit")
                edit_btn.setProperty("class", "btn-action-edit")
                edit_btn.clicked.connect(lambda checked, pid=p.id: self.edit_purchase_invoice(pid))
                actions_layout.addWidget(edit_btn)
                
                del_btn = QPushButton("Delete")
                del_btn.setProperty("class", "btn-action-delete")
                del_btn.clicked.connect(lambda checked, pid=p.id: self.delete_purchase_invoice(pid))
                actions_layout.addWidget(del_btn)
                
                self.history_table.setCellWidget(i, 6, actions_widget)
                
        except Exception as e:
            print(f"Error loading purchase history: {e}")
        finally:
            session.close()

    def toggle_bank_account(self, mode=None):
        if mode is None:
            mode = self.pay_mode_combo.currentText()
        self.bank_combo.setEnabled(mode == "Bank")

    def update_rate_on_product_change(self):
        prod_id = self.product_combo.currentData()
        if prod_id and prod_id in self.products_cache:
            prod = self.products_cache[prod_id]
            self.rate_input.setValue(prod.purchase_price)
            if hasattr(self, 'selling_price_input'):
                self.selling_price_input.setValue(prod.selling_price)
            if hasattr(self, 'brand_input'):
                self.brand_input.setText(prod.brand if prod.brand else "")
            if hasattr(self, 'model_input'):
                self.model_input.setText(prod.model if prod.model else "")
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
            if hasattr(self, 'selling_price_input'):
                self.selling_price_input.setValue(0.0)
            if hasattr(self, 'brand_input'):
                self.brand_input.clear()
            if hasattr(self, 'model_input'):
                self.model_input.clear()
            self.product_code_input.clear()
            self.unit_combo.setCurrentIndex(0)

    def switch_to_existing_stock(self):
        parent_win = self.window()
        if hasattr(parent_win, 'switch_view'):
            parent_win.switch_view(12)

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
            if found_product.category:
                p_cat_lower = found_product.category.strip().lower()
                for c_i in range(self.category_combo.count()):
                    if self.category_combo.itemText(c_i).strip().lower() == p_cat_lower:
                        self.category_combo.blockSignals(True)
                        if self.category_combo.lineEdit():
                            self.category_combo.lineEdit().blockSignals(True)
                        self.category_combo.setCurrentIndex(c_i)
                        self.category_combo.blockSignals(False)
                        if self.category_combo.lineEdit():
                            self.category_combo.lineEdit().blockSignals(False)
                        break
            self.filter_products_by_category()
            self.product_combo.select_product_id(found_product.id)
            self.qty_input.setFocus()
            self.qty_input.selectAll()
        else:
            QMessageBox.warning(self, "Product Code Not Found", f"Product Code '{code}' Not Found.")
            self.product_code_input.selectAll()
            self.product_code_input.setFocus()

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
            self.table.setColumnCount(10)
            self.table.setHorizontalHeaderLabels([
                "Code", "Name", "Category", 
                "Qty", "Unit", "Rate (₹)", "GST %", "Tax (₹)", "Total (₹)", "Action"
            ])
            header = self.table.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.Interactive)
            header.setSectionResizeMode(1, QHeaderView.Stretch)
            self.table.setColumnWidth(0, 62)   # Code
            self.table.setColumnWidth(2, 76)   # Category
            self.table.setColumnWidth(3, 44)   # Qty
            self.table.setColumnWidth(4, 48)   # Unit
            self.table.setColumnWidth(5, 74)   # Rate (₹)
            self.table.setColumnWidth(6, 54)   # GST %
            self.table.setColumnWidth(7, 68)   # Tax (₹)
            self.table.setColumnWidth(8, 78)   # Total (₹)
            header.setSectionResizeMode(9, QHeaderView.Fixed)
            self.table.setColumnWidth(9, 68)   # Action
        else:
            self.table.setColumnCount(8)
            self.table.setHorizontalHeaderLabels([
                "Code", "Name", "Category", 
                "Qty", "Unit", "Rate (₹)", "Total (₹)", "Action"
            ])
            header = self.table.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.Interactive)
            header.setSectionResizeMode(1, QHeaderView.Stretch)
            self.table.setColumnWidth(0, 65)   # Code
            self.table.setColumnWidth(2, 82)   # Category
            self.table.setColumnWidth(3, 46)   # Qty
            self.table.setColumnWidth(4, 52)   # Unit
            self.table.setColumnWidth(5, 76)   # Rate (₹)
            self.table.setColumnWidth(6, 82)   # Total (₹)
            header.setSectionResizeMode(7, QHeaderView.Fixed)
            self.table.setColumnWidth(7, 68)   # Action

    def add_item_to_list(self):
        prod_idx = self.product_combo.currentIndex()
        if prod_idx < 0:
            return

        prod_id = self.product_combo.currentData()
        qty = self.qty_input.value()
        unit = self.unit_combo.currentText()
        rate = self.rate_input.value()
        
        gst_active = getattr(self, 'gst_globally_enabled', False) and self.gst_enabled_checkbox.isChecked()
        if gst_active:
            gst_rate_text = self.gst_rate_combo.currentText().replace("%", "")
            gst_rate = float(gst_rate_text)
        else:
            gst_rate = 0.0

        taxable_value = qty * rate
        tax_amount = taxable_value * (gst_rate / 100.0)

        selling_price = self.selling_price_input.value() if hasattr(self, 'selling_price_input') else 0.0
        brand = self.brand_input.text().strip() if hasattr(self, 'brand_input') else ""
        model = self.model_input.text().strip() if hasattr(self, 'model_input') else ""

        p_cache = self.products_cache.get(prod_id)
        prod_text = p_cache.name if p_cache else self.product_combo.currentText()
        prod_code = p_cache.product_code if p_cache else "-"
        category = p_cache.category if p_cache else "-"

        # Check if already added (match by product_id AND unit AND gst_rate)
        for item in self.bill_items:
            if item["product_id"] == prod_id and item.get("unit") == unit and item.get("gst_rate", 0.0) == gst_rate:
                item["qty"] += qty
                item["rate"] = rate  # update with latest rate
                item["taxable_value"] = item["qty"] * rate
                item["tax_amount"] = item["taxable_value"] * (gst_rate / 100.0)
                item["selling_price"] = selling_price
                item["brand"] = brand
                item["model"] = model
                item["category"] = category
                self.update_table()
                self.reset_item_inputs()
                return

        self.bill_items.append({
            "product_id": prod_id,
            "product_code": prod_code,
            "name": prod_text,
            "category": category,
            "brand": brand,
            "model": model,
            "qty": qty,
            "unit": unit,
            "rate": rate,
            "gst_rate": gst_rate,
            "tax_amount": tax_amount,
            "taxable_value": taxable_value,
            "selling_price": selling_price
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
        if hasattr(self, 'selling_price_input'):
            self.selling_price_input.setValue(0.0)
        if hasattr(self, 'brand_input'):
            self.brand_input.clear()
        if hasattr(self, 'model_input'):
            self.model_input.clear()
        if hasattr(self, 'add_product_btn'):
            self.add_product_btn.hide()
        QTimer.singleShot(0, self._focus_product_code)

    def _focus_product_code(self):
        self.product_code_input.setFocus()
        self.product_code_input.selectAll()

    def delete_item(self, row_idx):
        self.bill_items.pop(row_idx)
        self.update_table()

    def update_table(self):
        gst_active = getattr(self, 'gst_globally_enabled', False) and self.gst_enabled_checkbox.isChecked()
        self.table.setRowCount(len(self.bill_items))
        for i, item in enumerate(self.bill_items):
            self.table.setItem(i, 0, QTableWidgetItem(item.get("product_code", "-")))
            self.table.setItem(i, 1, QTableWidgetItem(item.get("name", "-")))
            self.table.setItem(i, 2, QTableWidgetItem(item.get("category", "-")))
            self.table.setItem(i, 3, QTableWidgetItem(str(item.get("qty", 0))))
            self.table.setItem(i, 4, QTableWidgetItem(item.get("unit", "Pcs")))
            self.table.setItem(i, 5, QTableWidgetItem(f"{item.get('rate', 0.0):.2f}"))
            
            if gst_active:
                gst_rate = item.get("gst_rate", 0.0)
                tax_amt = item.get("tax_amount", 0.0)
                subtotal = (item.get("qty", 0) * item.get("rate", 0.0)) + tax_amt
                
                self.table.setItem(i, 6, QTableWidgetItem(f"{gst_rate:.0f}%"))
                self.table.setItem(i, 7, QTableWidgetItem(f"{tax_amt:.2f}"))
                self.table.setItem(i, 8, QTableWidgetItem(f"{subtotal:.2f}"))
                
                # Delete button at column index 9
                btn_container = QWidget()
                btn_layout = QHBoxLayout(btn_container)
                btn_layout.setContentsMargins(4, 4, 4, 4)
                btn_layout.setSpacing(0)
                btn_layout.setAlignment(Qt.AlignCenter)

                del_btn = QPushButton("Delete")
                del_btn.setProperty("class", "btn-action-delete")
                del_btn.clicked.connect(lambda checked, idx=i: self.delete_item(idx))
                btn_layout.addWidget(del_btn)
                self.table.setCellWidget(i, 9, btn_container)
            else:
                subtotal = item.get("qty", 0) * item.get("rate", 0.0)
                self.table.setItem(i, 6, QTableWidgetItem(f"{subtotal:.2f}"))

                # Delete button at column index 7
                btn_container = QWidget()
                btn_layout = QHBoxLayout(btn_container)
                btn_layout.setContentsMargins(4, 4, 4, 4)
                btn_layout.setSpacing(0)
                btn_layout.setAlignment(Qt.AlignCenter)

                del_btn = QPushButton("Delete")
                del_btn.setProperty("class", "btn-action-delete")
                del_btn.clicked.connect(lambda checked, idx=i: self.delete_item(idx))
                btn_layout.addWidget(del_btn)
                self.table.setCellWidget(i, 7, btn_container)

        self.update_summary()

    def update_summary(self):
        gst_active = getattr(self, 'gst_globally_enabled', False) and self.gst_enabled_checkbox.isChecked()
        
        if gst_active:
            taxable_sum = sum(item.get("qty", 0) * item.get("rate", 0.0) for item in self.bill_items)
            tax_sum = sum(item.get("tax_amount", 0.0) for item in self.bill_items)
            total = taxable_sum + tax_sum
            
            self.total_lbl.setText(f"Taxable: ₹{format_inr(taxable_sum)} | GST: ₹{format_inr(tax_sum)} | Total: ₹{format_inr(total)}")
        else:
            total = sum(item.get("qty", 0) * item.get("rate", 0.0) for item in self.bill_items)
            self.total_lbl.setText(f"Total Amount: ₹{format_inr(total)}")

        paid = self.paid_input.value()
        balance = total - paid
        if balance < 0:
            balance = 0.0
        self.balance_lbl.setText(f"Balance Payable: ₹{format_inr(balance)}")

    def save_purchase(self):
        invoice_no = self.invoice_input.text().strip()
        supp_id = self.supplier_combo.currentData()
        
        if not invoice_no:
            QMessageBox.warning(self, "Validation Error", "Please enter Supplier Invoice Number.")
            return
        if not self.bill_items:
            QMessageBox.warning(self, "Validation Error", "Please add at least one item to the bill.")
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
            for item in self.bill_items:
                taxable = item["qty"] * item["rate"]
                gst_rate = item.get("gst_rate", 0.0)
                tax_amt = taxable * (gst_rate / 100.0)
                
                taxable_amount += taxable
                total_gst += tax_amt
                total_cgst += tax_amt / 2.0
                total_sgst += tax_amt / 2.0
            total = taxable_amount + total_gst
        else:
            total = sum(item["qty"] * item["rate"] for item in self.bill_items)
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
            if not supp_id:
                # Find or create default supplier "Mr/Mss supplier"
                default_supp = session.query(Supplier).filter_by(name="Mr/Mss supplier").first()
                if not default_supp:
                    default_supp = Supplier(name="Mr/Mss supplier", mobile="N/A", address="N/A")
                    session.add(default_supp)
                    session.flush()
                supp_id = default_supp.id

            if self.editing_purchase_id:
                # 1. Fetch existing purchase
                purchase = session.query(PurchaseMaster).get(self.editing_purchase_id)
                if not purchase:
                    QMessageBox.warning(self, "Error", "Purchase bill to update was not found.")
                    session.close()
                    return

                # 2. Revert Old Stock (subtracting stock received)
                for item in purchase.items:
                    prod = session.query(Product).get(item.product_id)
                    if prod:
                        prod.stock_qty -= item.qty

                # 3. Revert Old Supplier Outstanding Balance
                old_supplier = session.query(Supplier).get(purchase.supplier_id)
                if old_supplier:
                    old_supplier.outstanding_balance -= purchase.balance_payable

                # 4. Revert Old Ledger Payments
                cash_txs = session.query(CashTransaction).filter_by(source_type='purchase', source_id=purchase.id).all()
                for tx in cash_txs:
                    session.delete(tx)

                bank_txs = session.query(BankTransaction).filter_by(source_type='purchase', source_id=purchase.id).all()
                for tx in bank_txs:
                    bank = session.query(BankAccount).get(tx.account_id)
                    if bank:
                        bank.balance += tx.amount
                    session.delete(tx)

                # 5. Clear old purchase items (they will be recreated)
                purchase.items.clear()

                # If bank transaction, check bank balance
                if pay_mode == "Bank" and paid > 0:
                    bank = session.query(BankAccount).get(bank_id)
                    if bank.balance < paid:
                        QMessageBox.warning(self, "Insufficient Funds", f"Insufficient balance in bank account {bank.bank_name}. Current: ₹{bank.balance:.2f}")
                        session.rollback()
                        session.close()
                        return

                # 6. Update PurchaseMaster Details
                purchase.date = bill_date
                purchase.supplier_id = supp_id
                purchase.total_amount = total
                purchase.paid_amount = paid
                purchase.balance_payable = balance
                purchase.gst_enabled = gst_active
                purchase.gst_type = "CGST+SGST"
                purchase.taxable_amount = taxable_amount
                purchase.total_cgst = total_cgst
                purchase.total_sgst = total_sgst
                purchase.total_igst = 0.0
                purchase.total_gst = total_gst

            else:
                # Check duplicate invoice number
                existing = session.query(PurchaseMaster).filter_by(invoice_number=invoice_no).first()
                if existing:
                    QMessageBox.warning(self, "Duplicate Invoice", f"Invoice number {invoice_no} already exists.")
                    session.close()
                    return

                # If bank transaction, check bank balance
                if pay_mode == "Bank" and paid > 0:
                    bank = session.query(BankAccount).get(bank_id)
                    if bank.balance < paid:
                        QMessageBox.warning(self, "Insufficient Funds", f"Insufficient balance in bank account {bank.bank_name}. Current: ₹{bank.balance:.2f}")
                        session.close()
                        return

                # Save Purchase Master
                purchase = PurchaseMaster(
                    invoice_number=invoice_no,
                    date=bill_date,
                    supplier_id=supp_id,
                    total_amount=total,
                    paid_amount=paid,
                    balance_payable=balance,
                    gst_enabled=gst_active,
                    gst_type="CGST+SGST",
                    taxable_amount=taxable_amount,
                    total_cgst=total_cgst,
                    total_sgst=total_sgst,
                    total_igst=0.0,
                    total_gst=total_gst
                )
                session.add(purchase)
                session.flush() # Get purchase ID safely within the transaction

            # Save Purchase Items & update stocks
            for item in self.bill_items:
                g_rate = item.get("gst_rate", 0.0) if gst_active else 0.0
                taxable_val = item["qty"] * item["rate"]
                tax_amt = taxable_val * (g_rate / 100.0)
                
                cgst_amt = 0.0
                sgst_amt = 0.0
                igst_amt = 0.0
                if gst_active:
                    cgst_amt = tax_amt / 2.0
                    sgst_amt = tax_amt / 2.0

                p_item = PurchaseItem(
                    purchase_id=purchase.id,
                    product_id=item["product_id"],
                    qty=item["qty"],
                    rate=item["rate"],
                    unit=item.get("unit", "Pcs"),
                    gst_rate=g_rate,
                    cgst_amount=cgst_amt,
                    sgst_amount=sgst_amt,
                    igst_amount=igst_amt,
                    tax_amount=tax_amt,
                    taxable_value=taxable_val
                )
                session.add(p_item)

                # Update product stock and rate
                prod = session.query(Product).get(item["product_id"])
                if prod:
                    prod.stock_qty += item["qty"]
                    # Optionally update purchase price to the latest price
                    prod.purchase_price = item["rate"]
                    if item.get("selling_price", 0.0) > 0:
                        prod.selling_price = item["selling_price"]
                    if item.get("brand"):
                        prod.brand = item["brand"]
                    if item.get("model"):
                        prod.model = item["model"]

            # Update Supplier Outstanding Balance
            supplier = session.query(Supplier).get(supp_id)
            supplier.outstanding_balance += balance

            # Ledger Book logging
            if paid > 0:
                desc = f"Payment for purchase invoice {invoice_no}"
                if pay_mode == "Cash":
                    tx_cash = CashTransaction(
                        date=bill_date,
                        transaction_type='out',
                        amount=paid,
                        source_type='purchase',
                        source_id=purchase.id,
                        description=desc
                    )
                    session.add(tx_cash)
                else:
                    tx_bank = BankTransaction(
                        date=bill_date,
                        transaction_type='withdrawal',
                        account_id=bank_id,
                        amount=paid,
                        source_type='purchase',
                        source_id=purchase.id,
                        description=desc
                    )
                    session.add(tx_bank)
                    # Deduct from bank account balance
                    bank = session.query(BankAccount).get(bank_id)
                    bank.balance -= paid

            session.commit()
            QMessageBox.information(self, "Success", "Purchase entry saved and stock updated successfully.")
            
            # Reset page
            self.editing_purchase_id = None
            self.save_btn.setText("Save Purchase Bill")
            self.save_btn.setProperty("class", "btn-success")
            self.save_btn.style().unpolish(self.save_btn)
            self.save_btn.style().polish(self.save_btn)
            self.cancel_edit_btn.setVisible(False)
            if hasattr(self, 'save_bottom_btn'):
                self.save_bottom_btn.setText("Save Purchase Bill")
                self.save_bottom_btn.setProperty("class", "btn-success")
                self.save_bottom_btn.style().unpolish(self.save_bottom_btn)
                self.save_bottom_btn.style().polish(self.save_bottom_btn)
            if hasattr(self, 'cancel_bottom_btn'):
                self.cancel_bottom_btn.setVisible(False)
            self.invoice_input.setEnabled(True)

            self.bill_items.clear()
            self.update_table()
            self.invoice_input.clear()
            self.pay_mode_combo.setCurrentText("Cash")
            self.toggle_bank_account("Cash")
            self.paid_input.setValue(0.0)
            self.qty_input.setValue(1)
            self.rate_input.setValue(0.0)
            if hasattr(self, 'selling_price_input'):
                self.selling_price_input.setValue(0.0)
            if hasattr(self, 'brand_input'):
                self.brand_input.clear()
            if hasattr(self, 'model_input'):
                self.model_input.clear()
            self.refresh_data()

        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save purchase bill: {e}")
        finally:
            session.close()

    def view_purchase_details(self, purchase_id):
        session = Session()
        try:
            purchase = session.query(PurchaseMaster).get(purchase_id)
            if not purchase:
                QMessageBox.warning(self, "Error", "Purchase bill not found.")
                return

            dialog = QDialog(self)
            dialog.setWindowTitle(f"Purchase Bill Details - {purchase.invoice_number}")
            dialog.setMinimumSize(600, 450)
            
            dlg_layout = QVBoxLayout(dialog)
            
            # Header info
            info_frame = QFrame()
            info_frame.setProperty("class", "CardFrame")
            info_layout = QFormLayout(info_frame)
            info_layout.addRow("Invoice Number:", QLabel(purchase.invoice_number))
            info_layout.addRow("Date:", QLabel(purchase.date.strftime("%Y-%m-%d")))
            supp_name = purchase.supplier.name if purchase.supplier else "Unknown Supplier (Deleted)"
            supp_mobile = purchase.supplier.mobile if purchase.supplier else "N/A"
            info_layout.addRow("Supplier Name:", QLabel(supp_name))
            info_layout.addRow("Supplier Contact:", QLabel(supp_mobile))
            dlg_layout.addWidget(info_frame)
            
            # Items table
            items_table = QTableWidget()
            items_table.setColumnCount(5)
            items_table.setHorizontalHeaderLabels(["Code", "Name", "Qty", "Rate (₹)", "Total (₹)"])
            header = items_table.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.Interactive)
            header.setSectionResizeMode(1, QHeaderView.Stretch)
            items_table.setColumnWidth(0, 75)
            items_table.setColumnWidth(2, 60)
            items_table.setColumnWidth(3, 85)
            items_table.setColumnWidth(4, 90)
            items_table.verticalHeader().setVisible(False)
            
            items = session.query(PurchaseItem).filter_by(purchase_id=purchase_id).all()
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
                items_table.setItem(i, 2, QTableWidgetItem(f"{item.qty} {getattr(item, 'unit', 'Pcs') or 'Pcs'}"))
                items_table.setItem(i, 3, QTableWidgetItem(f"{item.rate:.2f}"))
                subtotal = item.qty * item.rate
                items_table.setItem(i, 4, QTableWidgetItem(f"{subtotal:.2f}"))
                
            dlg_layout.addWidget(items_table)
            
            # Totals
            totals_frame = QFrame()
            totals_layout = QFormLayout(totals_frame)
            totals_layout.addRow("Total Amount:", QLabel(f"₹{format_inr(purchase.total_amount)}"))
            totals_layout.addRow("Paid Amount:", QLabel(f"₹{format_inr(purchase.paid_amount)}"))
            totals_layout.addRow("Balance Payable:", QLabel(f"₹{format_inr(purchase.balance_payable)}"))
            dlg_layout.addWidget(totals_frame)
            
            # Bottom Buttons (Print Invoice & Close)
            btn_layout = QHBoxLayout()
            btn_layout.addStretch()
            
            print_btn = QPushButton("Print Invoice")
            print_btn.clicked.connect(lambda: self.print_purchase_invoice(purchase_id))
            btn_layout.addWidget(print_btn)
            
            close_btn = QPushButton("Close")
            close_btn.setProperty("class", "btn-secondary")
            close_btn.clicked.connect(dialog.accept)
            btn_layout.addWidget(close_btn)
            
            dlg_layout.addLayout(btn_layout)
            
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load purchase details: {e}")
        finally:
            session.close()

    def print_purchase_invoice(self, purchase_id):
        session = Session()
        try:
            purchase = session.query(PurchaseMaster).get(purchase_id)
            if not purchase:
                QMessageBox.warning(self, "Error", "Purchase bill not found.")
                return
                
            # Retrieve Settings details
            s_name = session.query(Setting).filter_by(key='shop_name').first().value
            s_contact = session.query(Setting).filter_by(key='shop_contact').first().value
            s_address = session.query(Setting).filter_by(key='shop_address').first().value
            s_gst = session.query(Setting).filter_by(key='shop_gst').first().value

            # Prepare items list
            pdf_items = []
            gst_active = getattr(purchase, 'gst_enabled', False) or False
            for item in purchase.items:
                if item.product:
                    bm = getattr(item.product, 'brand_model', None) or getattr(item.product, 'brand', '') or ''
                    p_name = f"{item.product.name} ({bm})" if bm else item.product.name
                else:
                    p_name = f"Unknown Product (ID: {item.product_id})"

                g_rate = getattr(item, 'gst_rate', 0.0) or 0.0
                tax_amt = getattr(item, 'tax_amount', 0.0) or 0.0
                taxable_val = getattr(item, 'taxable_value', item.qty * item.rate) or (item.qty * item.rate)

                pdf_items.append({
                    "name": p_name,
                    "qty": f"{item.qty} {getattr(item, 'unit', 'Pcs') or 'Pcs'}",
                    "rate": item.rate,
                    "gst_rate": g_rate,
                    "tax_amount": tax_amt,
                    "taxable_value": taxable_val,
                    "total": (taxable_val + tax_amt) if gst_active else (item.qty * item.rate)
                })

            # Prepare Purchase PDF data
            pdf_data = {
                "shop_name": s_name,
                "shop_contact": s_contact,
                "shop_address": s_address,
                "shop_gst": s_gst,
                "invoice_number": purchase.invoice_number,
                "date": purchase.date.strftime("%Y-%m-%d"),
                "supplier_name": purchase.supplier.name,
                "supplier_mobile": purchase.supplier.mobile,
                "supplier_address": purchase.supplier.address,
                "supplier_gst": getattr(purchase.supplier, 'gst', '') or '',
                "items": pdf_items,
                "total_amount": purchase.total_amount,
                "paid_amount": purchase.paid_amount,
                "balance": purchase.balance_payable,
                "gst_enabled": gst_active,
                "gst_type": getattr(purchase, 'gst_type', 'CGST+SGST') or 'CGST+SGST',
                "taxable_amount": getattr(purchase, 'taxable_amount', purchase.total_amount) or purchase.total_amount,
                "total_cgst": getattr(purchase, 'total_cgst', 0.0) or 0.0,
                "total_sgst": getattr(purchase, 'total_sgst', 0.0) or 0.0,
                "total_igst": getattr(purchase, 'total_igst', 0.0) or 0.0,
                "total_gst": getattr(purchase, 'total_gst', 0.0) or 0.0
            }

            os.makedirs("invoices", exist_ok=True)
            path = os.path.abspath(f"invoices/{purchase.invoice_number}.pdf")
            generate_purchase_pdf(pdf_data, path)
            
            QMessageBox.information(self, "Success", f"Purchase Bill PDF generated at:\n{path}")
            
            # Auto-open
            try:
                os.startfile(path)
            except Exception as e:
                print(f"Could not auto-open PDF: {e}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to print/generate PDF: {e}")
        finally:
            session.close()

    def edit_purchase_invoice(self, purchase_id):
        session = Session()
        try:
            purchase = session.query(PurchaseMaster).get(purchase_id)
            if not purchase:
                QMessageBox.warning(self, "Error", "Purchase bill not found.")
                return
                
            # Switch to entry tab
            self.tabs.setCurrentIndex(0)
            
            # Set editing states
            self.editing_purchase_id = purchase.id
            self.save_btn.setText("Update Purchase Bill")
            self.save_btn.setProperty("class", "btn-warning")
            self.save_btn.style().unpolish(self.save_btn)
            self.save_btn.style().polish(self.save_btn)
            self.cancel_edit_btn.setVisible(True)
            if hasattr(self, 'save_bottom_btn'):
                self.save_bottom_btn.setText("Update Purchase Bill")
                self.save_bottom_btn.setProperty("class", "btn-warning")
                self.save_bottom_btn.style().unpolish(self.save_bottom_btn)
                self.save_bottom_btn.style().polish(self.save_bottom_btn)
            if hasattr(self, 'cancel_bottom_btn'):
                self.cancel_bottom_btn.setVisible(True)
            
            # Load purchase parameters
            self.invoice_input.setText(purchase.invoice_number)
            self.invoice_input.setEnabled(False)  # Disabled to preserve identifier integrity
            
            self.date_input.setDate(QDate(purchase.date.year, purchase.date.month, purchase.date.day))
            
            # Set supplier
            idx = self.supplier_combo.findData(purchase.supplier_id)
            if idx >= 0:
                self.supplier_combo.setCurrentIndex(idx)
                
            # Set payment mode
            cash_tx = session.query(CashTransaction).filter_by(source_type='purchase', source_id=purchase.id).first()
            bank_tx = session.query(BankTransaction).filter_by(source_type='purchase', source_id=purchase.id).first()
            
            if bank_tx:
                self.pay_mode_combo.setCurrentText("Bank")
                self.bank_combo.setEnabled(True)
                b_idx = self.bank_combo.findData(bank_tx.account_id)
                if b_idx >= 0:
                    self.bank_combo.setCurrentIndex(b_idx)
            else:
                self.pay_mode_combo.setCurrentText("Cash")
                self.bank_combo.setEnabled(False)
                
            self.paid_input.setValue(purchase.paid_amount)
            
            # Load GST settings
            is_gst = getattr(purchase, 'gst_enabled', False) or False
            self.gst_enabled_checkbox.setChecked(is_gst)
            
            # Load items
            self.bill_items = []
            for item in purchase.items:
                self.bill_items.append({
                    "product_id": item.product_id,
                    "product_code": item.product.product_code if item.product else "-",
                    "name": item.product.name if item.product else "Unknown",
                    "category": item.product.category if item.product else "-",
                    "brand": item.product.brand if item.product else "-",
                    "model": item.product.model if item.product else "-",
                    "qty": item.qty,
                    "unit": getattr(item, 'unit', 'Pcs') or 'Pcs',
                    "rate": item.rate,
                    "gst_rate": getattr(item, 'gst_rate', 0.0) or 0.0,
                    "tax_amount": getattr(item, 'tax_amount', 0.0) or 0.0,
                    "taxable_value": getattr(item, 'taxable_value', item.qty * item.rate) or (item.qty * item.rate),
                    "selling_price": item.product.selling_price if item.product else 0.0
                })
                
            self.apply_gst_visibility()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load purchase for editing: {e}")
        finally:
            session.close()

    def delete_purchase_invoice(self, purchase_id):
        confirm = QMessageBox.question(
            self, "Confirm Delete", 
            "Are you sure you want to delete this purchase bill?\nAll inventory stock and supplier outstanding adjustments will be reverted.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return
            
        session = Session()
        try:
            purchase = session.query(PurchaseMaster).get(purchase_id)
            if not purchase:
                QMessageBox.warning(self, "Error", "Purchase bill not found.")
                session.close()
                return
                
            # Revert inventory stock (deduct stock since we received it in purchase)
            for item in purchase.items:
                prod = session.query(Product).get(item.product_id)
                if prod:
                    prod.stock_qty -= item.qty
                    
            # Revert supplier outstanding balance
            supplier = session.query(Supplier).get(purchase.supplier_id)
            if supplier:
                supplier.outstanding_balance -= purchase.balance_payable
                
            # Revert/delete ledger entries (CashTransaction/BankTransaction)
            cash_txs = session.query(CashTransaction).filter_by(source_type='purchase', source_id=purchase.id).all()
            for tx in cash_txs:
                session.delete(tx)
                
            bank_txs = session.query(BankTransaction).filter_by(source_type='purchase', source_id=purchase.id).all()
            for tx in bank_txs:
                # Revert bank account balance (add back funds withdrawn for purchase)
                bank = session.query(BankAccount).get(tx.account_id)
                if bank:
                    bank.balance += tx.amount
                session.delete(tx)
                
            # Delete payments logged against this purchase
            from models import Payment
            payments = session.query(Payment).filter_by(purchase_id=purchase.id).all()
            for p_rec in payments:
                # Revert CashTransaction and BankTransaction of the payment
                p_cash_txs = session.query(CashTransaction).filter_by(source_type='payment', source_id=p_rec.id).all()
                for tx in p_cash_txs:
                    session.delete(tx)
                p_bank_txs = session.query(BankTransaction).filter_by(source_type='payment', source_id=p_rec.id).all()
                for tx in p_bank_txs:
                    bank = session.query(BankAccount).get(tx.account_id)
                    if bank:
                        bank.balance += tx.amount
                    session.delete(tx)
                session.delete(p_rec)
                
            # Delete PurchaseMaster (which cascades to delete PurchaseItems)
            session.delete(purchase)
            
            session.commit()
            QMessageBox.information(self, "Success", "Purchase bill deleted and related records reverted successfully.")
            self.load_history()
            self.refresh_data()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to delete purchase bill: {e}")
        finally:
            session.close()

    def cancel_edit_mode(self):
        self.editing_purchase_id = None
        self.save_btn.setText("Save Purchase Bill")
        self.save_btn.setProperty("class", "btn-success")
        self.save_btn.style().unpolish(self.save_btn)
        self.save_btn.style().polish(self.save_btn)
        self.cancel_edit_btn.setVisible(False)
        if hasattr(self, 'save_bottom_btn'):
            self.save_bottom_btn.setText("Save Purchase Bill")
            self.save_bottom_btn.setProperty("class", "btn-success")
            self.save_bottom_btn.style().unpolish(self.save_bottom_btn)
            self.save_bottom_btn.style().polish(self.save_bottom_btn)
        if hasattr(self, 'cancel_bottom_btn'):
            self.cancel_bottom_btn.setVisible(False)
        self.invoice_input.setEnabled(True)
        
        # Clear fields
        self.bill_items.clear()
        self.update_table()
        self.invoice_input.clear()
        self.pay_mode_combo.setCurrentText("Cash")
        self.toggle_bank_account("Cash")
        self.paid_input.setValue(0.0)
        self.qty_input.setValue(1)
        self.rate_input.setValue(0.0)
        if hasattr(self, 'selling_price_input'):
            self.selling_price_input.setValue(0.0)
        if hasattr(self, 'brand_input'):
            self.brand_input.clear()
        if hasattr(self, 'model_input'):
            self.model_input.clear()
        self.refresh_data()
