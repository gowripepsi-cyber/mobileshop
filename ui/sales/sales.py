import datetime
import os
import subprocess
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, 
                             QDateEdit, QSpinBox, QDoubleSpinBox, QPushButton, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QMessageBox, QFrame, QFormLayout, 
                             QFileDialog, QTabWidget, QDialog, QDialogButtonBox, QCompleter)
from PySide6.QtCore import Qt, QDate
from database import Session, Setting
from models import Customer, Product, BankAccount, SalesMaster, SalesItem, CashTransaction, BankTransaction, Category
from utils.pdf_generator import generate_sales_pdf

class SalesView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.invoice_items = []  # list of dicts: {"product_id": int, "name": str, "qty": int, "rate": float, "discount": float}
        self.editing_sales_id = None  # Tracks if we are editing an invoice
        self.products_cache = {}      # Cache of products to prevent early signal errors during reload
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
        main_layout = QHBoxLayout(self.entry_tab)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(20)

        # Left Column: Invoice Parameters
        left_panel = QFrame()
        left_panel.setProperty("class", "CardFrame")
        left_panel.setFixedWidth(350)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(15, 15, 15, 15)
        left_layout.setSpacing(15)

        title_lbl = QLabel("Sales Invoice Details")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff;")
        left_layout.addWidget(title_lbl)

        form_layout = QFormLayout()
        
        self.invoice_input = QLineEdit()
        self.invoice_input.setPlaceholderText("e.g. INV-1004")
        
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())
        
        self.customer_combo = QComboBox()
        self.customer_combo.setEditable(True)
        self.customer_combo.setInsertPolicy(QComboBox.NoInsert)
        self.customer_combo.currentTextChanged.connect(self.check_customer_match)
        if self.customer_combo.lineEdit():
            self.customer_combo.lineEdit().textChanged.connect(self.check_customer_match)

        cust_layout = QHBoxLayout()
        cust_layout.setContentsMargins(0, 0, 0, 0)
        cust_layout.setSpacing(6)
        cust_layout.addWidget(self.customer_combo, 1)

        self.add_customer_btn = QPushButton("+")
        self.add_customer_btn.setToolTip("Add new customer")
        self.add_customer_btn.setProperty("class", "btn-quick-add")
        self.add_customer_btn.setFixedWidth(40)
        self.add_customer_btn.setStyleSheet("padding: 0px; font-size: 18px; font-weight: bold; text-align: center;")
        self.add_customer_btn.setCursor(Qt.PointingHandCursor)
        self.add_customer_btn.clicked.connect(self.handle_add_customer_click)
        self.add_customer_btn.hide()
        cust_layout.addWidget(self.add_customer_btn)
        
        self.pay_mode_combo = QComboBox()
        self.pay_mode_combo.addItems(["Cash", "Bank"])
        self.pay_mode_combo.currentTextChanged.connect(self.toggle_bank_account)
        
        self.bank_combo = QComboBox()
        self.bank_combo.setEnabled(False)
        
        self.paid_input = QDoubleSpinBox()
        self.paid_input.setRange(0, 9999999)
        self.paid_input.setValue(0.0)
        self.paid_input.setDecimals(2)
        self.paid_input.valueChanged.connect(self.update_summary)

        form_layout.addRow("Invoice Number *:", self.invoice_input)
        form_layout.addRow("Invoice Date:", self.date_input)
        form_layout.addRow("Customer:", cust_layout)
        form_layout.addRow("Payment Mode:", self.pay_mode_combo)
        form_layout.addRow("Select Bank A/c:", self.bank_combo)
        form_layout.addRow("Paid Amount (₹):", self.paid_input)

        left_layout.addLayout(form_layout)
        left_layout.addStretch()

        # Action Buttons Layout (Save/Update and Cancel Edit)
        btn_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Save & Print Invoice")
        self.save_btn.setProperty("class", "btn-success")
        self.save_btn.setFixedHeight(40)
        self.save_btn.clicked.connect(self.save_sales_invoice)
        btn_layout.addWidget(self.save_btn)

        self.cancel_edit_btn = QPushButton("Cancel Edit")
        self.cancel_edit_btn.setProperty("class", "btn-secondary")
        self.cancel_edit_btn.setFixedHeight(40)
        self.cancel_edit_btn.setVisible(False)
        self.cancel_edit_btn.clicked.connect(self.cancel_edit_mode)
        btn_layout.addWidget(self.cancel_edit_btn)

        left_layout.addLayout(btn_layout)

        main_layout.addWidget(left_panel)

        # Right Column: Product Line Items & Table
        right_panel = QFrame()
        right_panel.setProperty("class", "CardFrame")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(15, 15, 15, 15)
        right_layout.setSpacing(15)

        # Product Entry Section
        entry_title = QLabel("Add Items to Invoice")
        entry_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        right_layout.addWidget(entry_title)

        row1_layout = QHBoxLayout()
        
        self.product_code_input = QLineEdit()
        self.product_code_input.setPlaceholderText("Code")
        self.product_code_input.setFixedWidth(120)
        self.product_code_input.returnPressed.connect(self.handle_product_code_entry)
        row1_layout.addWidget(QLabel("Code:"), 0)
        row1_layout.addWidget(self.product_code_input, 1)
        
        self.category_combo = QComboBox()
        self.category_combo.currentIndexChanged.connect(self.filter_products_by_category)
        row1_layout.addWidget(QLabel("Category:"), 0)
        row1_layout.addWidget(self.category_combo, 2)
        
        self.product_combo = QComboBox()
        self.product_combo.setPlaceholderText("Select Product")
        self.product_combo.currentIndexChanged.connect(self.update_rate_on_product_change)
        row1_layout.addWidget(QLabel("Product:"), 0)
        row1_layout.addWidget(self.product_combo, 5)

        right_layout.addLayout(row1_layout)

        row2_layout = QHBoxLayout()

        self.qty_input = QSpinBox()
        self.qty_input.setRange(1, 1000)
        self.qty_input.setValue(1)
        row2_layout.addWidget(QLabel("Qty:"), 0)
        row2_layout.addWidget(self.qty_input, 1)

        self.rate_input = QDoubleSpinBox()
        self.rate_input.setRange(0.0, 9999999.0)
        self.rate_input.setValue(0.0)
        self.rate_input.setDecimals(2)
        row2_layout.addWidget(QLabel("Rate (₹):"), 0)
        row2_layout.addWidget(self.rate_input, 2)

        self.discount_input = QDoubleSpinBox()
        self.discount_input.setRange(0.0, 999999.0)
        self.discount_input.setValue(0.0)
        self.discount_input.setDecimals(2)
        row2_layout.addWidget(QLabel("Disc (₹):"), 0)
        row2_layout.addWidget(self.discount_input, 1.5)

        self.add_item_btn = QPushButton("Add Item")
        self.add_item_btn.clicked.connect(self.add_item_to_list)
        row2_layout.addWidget(self.add_item_btn, 2)

        right_layout.addLayout(row2_layout)

        # Items Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["Product Code", "Product Name", "Qty", "Rate (₹)", "Discount (₹)", "Total (₹)", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Fixed)
        self.table.setColumnWidth(6, 110)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(54)
        right_layout.addWidget(self.table)

        # Summary Bar (Totals, Paid, Balance)
        summary_bar = QHBoxLayout()
        
        self.total_lbl = QLabel("Total Amount: ₹0.00")
        self.total_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #6366f1;")
        
        self.balance_lbl = QLabel("Balance Receivable: ₹0.00")
        self.balance_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #f59e0b;")
        
        summary_bar.addWidget(self.total_lbl)
        summary_bar.addWidget(self.balance_lbl)
        right_layout.addLayout(summary_bar)

        main_layout.addWidget(right_panel, 2)

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
        self.product_combo.blockSignals(True)
        self.product_combo.clear()
        
        cat_name = self.category_combo.currentText()
        for prod_id, p in self.products_cache.items():
            if cat_name == "-- All Categories --" or p.category == cat_name:
                display_txt = f"{p.name} ({p.brand} - {p.model}) [Stock: {p.stock_qty}]"
                if p.imei:
                    display_txt += f" [IMEI: {p.imei}]"
                self.product_combo.addItem(display_txt, p.id)
                
        self.product_combo.blockSignals(False)
        self.update_rate_on_product_change()

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

        # Re-attach completer model
        completer = QCompleter(self.customer_combo.model(), self.customer_combo)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.customer_combo.setCompleter(completer)
        self.customer_combo.blockSignals(False)

        if curr_id is not None:
            idx = self.customer_combo.findData(curr_id)
            if idx >= 0:
                self.customer_combo.setCurrentIndex(idx)
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

            self.filter_products_by_category()
            
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

    def update_rate_on_product_change(self):
        prod_id = self.product_combo.currentData()
        if prod_id and hasattr(self, 'products_cache') and prod_id in self.products_cache:
            prod = self.products_cache[prod_id]
            self.rate_input.setValue(prod.selling_price)
            # Sync product code input for visual feedback
            if prod.product_code:
                self.product_code_input.setText(prod.product_code)
        else:
            self.rate_input.setValue(0.0)
            self.product_code_input.clear()

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
            cat_idx = self.category_combo.findText(found_product.category)
            if cat_idx >= 0:
                self.category_combo.blockSignals(True)
                self.category_combo.setCurrentIndex(cat_idx)
                self.category_combo.blockSignals(False)
            self.filter_products_by_category()
            prod_idx = self.product_combo.findData(found_product.id)
            if prod_idx >= 0:
                self.product_combo.setCurrentIndex(prod_idx)
            self.qty_input.setFocus()
            self.qty_input.selectAll()
        else:
            QMessageBox.warning(self, "Product Code Not Found", f"Product Code '{code}' Not Found.")
            self.product_code_input.selectAll()
            self.product_code_input.setFocus()

    def toggle_bank_account(self, mode):
        self.bank_combo.setEnabled(mode == "Bank")

    def add_item_to_list(self):
        prod_idx = self.product_combo.currentIndex()
        if prod_idx < 0:
            return

        prod_id = self.product_combo.currentData()
        qty = self.qty_input.value()
        rate = self.rate_input.value()
        disc = self.discount_input.value()

        # Retrieve cached stock limit
        p_cache = self.products_cache.get(prod_id)
        if not p_cache:
            return
            
        current_added_qty = 0
        for item in self.invoice_items:
            if item["product_id"] == prod_id:
                current_added_qty = item["qty"]

        # If editing, we should account for the stock quantity already allocated in this invoice!
        # Find how much was originally allocated in this invoice if it's an edit
        original_allocated = 0
        if self.editing_sales_id:
            session = Session()
            try:
                old_item = session.query(SalesItem).filter_by(sales_id=self.editing_sales_id, product_id=prod_id).first()
                if old_item:
                    original_allocated = old_item.qty
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

        # Check if already added
        for item in self.invoice_items:
            if item["product_id"] == prod_id:
                item["qty"] += qty
                item["rate"] = rate  
                item["discount"] = disc
                self.update_table()
                return

        self.invoice_items.append({
            "product_id": prod_id,
            "product_code": p_cache.product_code if p_cache.product_code else "-",
            "name": p_cache.name,
            "qty": qty,
            "rate": rate,
            "discount": disc
        })
        
        self.update_table()

    def delete_item(self, row_idx):
        self.invoice_items.pop(row_idx)
        self.update_table()

    def update_table(self):
        self.table.setRowCount(len(self.invoice_items))
        for i, item in enumerate(self.invoice_items):
            self.table.setItem(i, 0, QTableWidgetItem(item.get("product_code", "-")))
            self.table.setItem(i, 1, QTableWidgetItem(item["name"]))
            self.table.setItem(i, 2, QTableWidgetItem(str(item["qty"])))
            self.table.setItem(i, 3, QTableWidgetItem(f"{item['rate']:.2f}"))
            self.table.setItem(i, 4, QTableWidgetItem(f"{item['discount']:.2f}"))
            
            subtotal = (item["qty"] * item["rate"]) - item["discount"]
            if subtotal < 0:
                subtotal = 0.0
            self.table.setItem(i, 5, QTableWidgetItem(f"{subtotal:.2f}"))

            # Delete button (centered wrapper container)
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
        total = sum((item["qty"] * item["rate"]) - item["discount"] for item in self.invoice_items)
        if total < 0:
            total = 0.0
        paid = self.paid_input.value()
        balance = total - paid
        if balance < 0:
            balance = 0.0

        self.total_lbl.setText(f"Total Amount: ₹{total:,.2f}")
        self.balance_lbl.setText(f"Balance Receivable: ₹{balance:,.2f}")

    def save_sales_invoice(self):
        invoice_no = self.invoice_input.text().strip()
        cust_id = self.customer_combo.currentData()
        
        if not invoice_no:
            QMessageBox.warning(self, "Validation Error", "Please enter Invoice Number.")
            return
        if not self.invoice_items:
            QMessageBox.warning(self, "Validation Error", "Please add at least one product to the invoice.")
            return

        total = sum((item["qty"] * item["rate"]) - item["discount"] for item in self.invoice_items)
        if total < 0:
            total = 0.0
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
                session.query(SalesItem).filter_by(sales_id=sale.id).delete()

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
                    balance_receivable=balance
                )
                session.add(sale)
                session.flush()  # Populates sale.id safely within the transaction

            # Save Sales Items & deduct stock
            pdf_items = []
            for item in self.invoice_items:
                s_item = SalesItem(
                    sales_id=sale.id,
                    product_id=item["product_id"],
                    qty=item["qty"],
                    rate=item["rate"],
                    discount=item["discount"]
                )
                session.add(s_item)

                prod = session.query(Product).get(item["product_id"])
                prod.stock_qty -= item["qty"]
                
                p_code = f"[{prod.product_code}] " if prod.product_code else ""
                pdf_items.append({
                    "name": f"{p_code}{prod.name} ({prod.brand} {prod.model})",
                    "qty": item["qty"],
                    "rate": item["rate"],
                    "discount": item["discount"],
                    "total": (item["qty"] * item["rate"]) - item["discount"]
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

            # Prepare Invoice PDF data
            pdf_data = {
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
                "balance": balance
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
            self.save_btn.setText("Save & Print Invoice")
            self.save_btn.setProperty("class", "btn-success")
            self.save_btn.style().unpolish(self.save_btn)
            self.save_btn.style().polish(self.save_btn)
            self.cancel_edit_btn.setVisible(False)
            self.invoice_input.setEnabled(True)

            self.invoice_items.clear()
            self.update_table()
            self.invoice_input.clear()
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
                self.history_table.setItem(i, 3, QTableWidgetItem(f"₹{p.total_amount:,.2f}"))
                self.history_table.setItem(i, 4, QTableWidgetItem(f"₹{p.paid_amount:,.2f}"))
                self.history_table.setItem(i, 5, QTableWidgetItem(f"₹{p.balance_receivable:,.2f}"))
                
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
            items_table.setColumnCount(6)
            items_table.setHorizontalHeaderLabels(["Product Code", "Product Name", "Qty", "Rate (₹)", "Discount (₹)", "Total (₹)"])
            items_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            items_table.verticalHeader().setVisible(False)
            
            items = session.query(SalesItem).filter_by(sales_id=sale_id).all()
            items_table.setRowCount(len(items))
            for i, item in enumerate(items):
                p_code = item.product.product_code if item.product else "-"
                if item.product:
                    display_name = f"{item.product.name} ({item.product.brand} {item.product.model})"
                else:
                    display_name = f"Unknown Product (ID: {item.product_id})"
                items_table.setItem(i, 0, QTableWidgetItem(p_code))
                items_table.setItem(i, 1, QTableWidgetItem(display_name))
                items_table.setItem(i, 2, QTableWidgetItem(str(item.qty)))
                items_table.setItem(i, 3, QTableWidgetItem(f"{item.rate:.2f}"))
                items_table.setItem(i, 4, QTableWidgetItem(f"{item.discount:.2f}"))
                subtotal = (item.qty * item.rate) - item.discount
                items_table.setItem(i, 5, QTableWidgetItem(f"{subtotal:.2f}"))
                
            dlg_layout.addWidget(items_table)
            
            # Totals
            totals_frame = QFrame()
            totals_layout = QFormLayout(totals_frame)
            totals_layout.addRow("Total Amount:", QLabel(f"₹{sale.total_amount:,.2f}"))
            totals_layout.addRow("Paid Amount:", QLabel(f"₹{sale.paid_amount:,.2f}"))
            totals_layout.addRow("Balance Receivable:", QLabel(f"₹{sale.balance_receivable:,.2f}"))
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
            for item in sale.items:
                p_code = f"[{item.product.product_code}] " if item.product and item.product.product_code else ""
                pdf_items.append({
                    "name": f"{p_code}{item.product.name} ({item.product.brand} {item.product.model})",
                    "qty": item.qty,
                    "rate": item.rate,
                    "discount": item.discount,
                    "total": (item.qty * item.rate) - item.discount
                })

            # Prepare Invoice PDF data
            pdf_data = {
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
                "balance": sale.balance_receivable
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
            
            # Load items
            self.invoice_items = []
            for item in sale.items:
                self.invoice_items.append({
                    "product_id": item.product_id,
                    "product_code": item.product.product_code if item.product else "-",
                    "name": item.product.name,
                    "qty": item.qty,
                    "rate": item.rate,
                    "discount": item.discount
                })
                
            self.update_table()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load invoice for editing: {e}")
        finally:
            session.close()

    def cancel_edit_mode(self):
        self.editing_sales_id = None
        self.save_btn.setText("Save & Print Invoice")
        self.save_btn.setProperty("class", "btn-success")
        self.save_btn.style().unpolish(self.save_btn)
        self.save_btn.style().polish(self.save_btn)
        
        self.cancel_edit_btn.setVisible(False)
        self.invoice_input.setEnabled(True)
        
        # Clear fields
        self.invoice_items.clear()
        self.update_table()
        self.invoice_input.clear()
        self.paid_input.setValue(0.0)
        self.qty_input.setValue(1)
        self.discount_input.setValue(0.0)
        self.refresh_data()
