import datetime
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QComboBox, 
                             QDateEdit, QSpinBox, QDoubleSpinBox, QPushButton, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QMessageBox, QFrame, QFormLayout, 
                             QDialog, QDialogButtonBox)
from PySide6.QtCore import Qt, QDate, QTimer
from utils.formatters import format_inr
from database import Session, Setting, generate_next_sales_return_number
from models import Customer, Product, BankAccount, SalesMaster, SalesItem, CashTransaction, BankTransaction, Category, SalesReturnMaster, SalesReturnItem
from utils.ui_helpers import enable_quick_add_auto_select, AutoClearSearchableComboBox

class SalesReturnEntryWidget(QWidget):
    def __init__(self, parent=None, history_widget=None):
        super().__init__(parent)
        self.history_widget = history_widget
        self.return_items = []  # list of dicts: {"product_id": int, "name": str, "qty": int, "rate": float}
        self.products_cache = {}
        self.init_ui()
        self.refresh_data()

    def init_ui(self):
        # Vertical stacked layout: Top = Block 1 (Sales Return Parameters), Bottom = Block 2 (Items Entry & Table)
        main_layout = QVBoxLayout(self)
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
        # BLOCK 1 (Top Block): Sales Return Details Card
        # =========================================================================
        top_panel = QFrame()
        top_panel.setProperty("class", "CardFrame")
        top_layout = QVBoxLayout(top_panel)
        top_layout.setContentsMargins(16, 12, 16, 12)
        top_layout.setSpacing(10)

        # Header Row: Title & Outstanding Adj Badge
        top_title_row = QHBoxLayout()
        top_title_row.setContentsMargins(0, 0, 0, 0)
        title_lbl = QLabel("Sales Return Details")
        title_lbl.setStyleSheet("font-size: 14.5px; font-weight: bold; color: #0f172a;")
        top_title_row.addWidget(title_lbl)
        top_title_row.addStretch()

        self.adj_badge = QLabel("Outstanding Adj: ₹0.00")
        self.adj_badge.setStyleSheet("""
            font-size: 12.5px;
            font-weight: bold;
            color: #ef4444;
            background-color: #fef2f2;
            border: 1px solid #fecaca;
            border-radius: 6px;
            padding: 4px 12px;
        """)
        top_title_row.addWidget(self.adj_badge)
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

        # 1. Return Number
        self.return_no_input = QLineEdit()
        self.return_no_input.setPlaceholderText("e.g. SR-1001")
        self.return_no_input.setStyleSheet(input_style)
        f_ret_no = make_field("Return Number *", self.return_no_input)

        # 2. Return Date
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setStyleSheet(input_style)
        f_date = make_field("Return Date", self.date_input)

        # 3. Customer (combo + add button)
        self.customer_combo = AutoClearSearchableComboBox()
        self.customer_combo.currentTextChanged.connect(self.check_customer_match)
        if self.customer_combo.lineEdit():
            self.customer_combo.lineEdit().setPlaceholderText("Select or type customer name")
        self.customer_combo.currentIndexChanged.connect(self.load_customer_invoices)

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
        f_cust = make_field("Customer *", cust_widget)

        # 4. Ref Sales Invoice
        self.invoice_combo = QComboBox()
        self.invoice_combo.setStyleSheet(input_style)
        self.invoice_combo.currentIndexChanged.connect(self.on_invoice_selected)
        f_inv = make_field("Ref Sales Invoice", self.invoice_combo)

        # 5. Refund Mode
        self.pay_mode_combo = QComboBox()
        self.pay_mode_combo.addItems(["Cash", "Bank"])
        self.pay_mode_combo.setStyleSheet(input_style)
        self.pay_mode_combo.currentTextChanged.connect(self.toggle_bank_account)
        self.pay_mode_combo.currentIndexChanged.connect(lambda: self.toggle_bank_account())
        f_mode = make_field("Refund Mode", self.pay_mode_combo)

        # 6. Select Bank A/c
        self.bank_combo = QComboBox()
        self.bank_combo.setStyleSheet(input_style)
        self.bank_combo.setEnabled(False)
        f_bank = make_field("Select Bank A/c", self.bank_combo)

        # 7. Refund Paid (₹)
        self.refund_input = QDoubleSpinBox()
        self.refund_input.setRange(0, 9999999)
        self.refund_input.setValue(0.0)
        self.refund_input.setDecimals(2)
        self.refund_input.setStyleSheet(input_style)
        self.refund_input.valueChanged.connect(self.update_summary)
        f_refund = make_field("Refund Paid (₹)", self.refund_input)

        # Auto-calculated outstanding adjustment spinbox (hidden from form, displayed in badge & summary bar)
        self.bal_deducted_input = QDoubleSpinBox()
        self.bal_deducted_input.setRange(0, 9999999)
        self.bal_deducted_input.setValue(0.0)
        self.bal_deducted_input.setDecimals(2)
        self.bal_deducted_input.setEnabled(False)
        self.bal_deducted_input.hide()

        # 8. Save Button in Top Block
        self.save_btn = QPushButton("Save && Print Return Note")
        self.save_btn.setProperty("class", "btn-success")
        self.save_btn.setStyleSheet("min-height: 36px; max-height: 36px; padding: 0px 14px; font-weight: bold; border-radius: 6px;")
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.clicked.connect(self.save_sales_return)

        top_btn_container = QWidget()
        top_btn_vl = QVBoxLayout(top_btn_container)
        top_btn_vl.setContentsMargins(0, 0, 0, 0)
        top_btn_vl.setSpacing(3)
        top_btn_spacer = QLabel(" ")
        top_btn_spacer.setStyleSheet("font-size: 11.5px;")
        top_btn_vl.addWidget(top_btn_spacer)
        top_btn_vl.addWidget(self.save_btn)

        # Row 0: Return Number, Return Date, Customer, Ref Sales Invoice
        top_grid.addWidget(f_ret_no, 0, 0)
        top_grid.addWidget(f_date, 0, 1)
        top_grid.addWidget(f_cust, 0, 2)
        top_grid.addWidget(f_inv, 0, 3)

        # Row 1: Refund Mode, Select Bank, Refund Paid, Save Button
        top_grid.addWidget(f_mode, 1, 0)
        top_grid.addWidget(f_bank, 1, 1)
        top_grid.addWidget(f_refund, 1, 2)
        top_grid.addWidget(top_btn_container, 1, 3)

        top_layout.addLayout(top_grid)
        main_layout.addWidget(top_panel)

        # =========================================================================
        # BLOCK 2 (Bottom Block): Product Line Items & Table Card
        # =========================================================================
        bottom_panel = QFrame()
        bottom_panel.setProperty("class", "CardFrame")
        bottom_layout = QVBoxLayout(bottom_panel)
        bottom_layout.setContentsMargins(16, 12, 16, 14)
        bottom_layout.setSpacing(10)

        entry_title = QLabel("Add Returned Products")
        entry_title.setStyleSheet("font-size: 13.5px; font-weight: bold; color: #0f172a;")
        bottom_layout.addWidget(entry_title)

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
        self.category_combo = QComboBox()
        self.category_combo.setStyleSheet(input_style)
        self.category_combo.currentIndexChanged.connect(self.filter_products_by_category)
        f_pcat = make_field("Category", self.category_combo, width=160)
        item_row.addWidget(f_pcat)

        # 3. Product Combo
        self.product_combo = QComboBox()
        self.product_combo.setPlaceholderText("Select Product")
        self.product_combo.setStyleSheet(input_style)
        self.product_combo.currentIndexChanged.connect(self.update_rate_on_product_change)
        f_pprod = make_field("Product Name *", self.product_combo)
        item_row.addWidget(f_pprod, 1)

        # 4. Quantity
        self.qty_input = QSpinBox()
        self.qty_input.setRange(1, 100000)
        self.qty_input.setValue(1)
        self.qty_input.setStyleSheet(input_style)
        f_pqty = make_field("Quantity", self.qty_input, width=70)
        item_row.addWidget(f_pqty)

        # 5. Rate (₹)
        self.rate_input = QDoubleSpinBox()
        self.rate_input.setRange(0.0, 9999999.0)
        self.rate_input.setValue(0.0)
        self.rate_input.setDecimals(2)
        self.rate_input.setStyleSheet(input_style)
        f_prate = make_field("Rate (₹)", self.rate_input, width=90)
        item_row.addWidget(f_prate)

        # 6. Add Item Button
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

        # Table
        self.table = QTableWidget()
        header_labels = ["Code", "Name", "Qty", "Rate (₹)", "Total (₹)", "Action"]
        self.table.setColumnCount(len(header_labels))
        for col, label in enumerate(header_labels):
            h_item = QTableWidgetItem(label)
            if col in [0, 2, 5]:  # Code, Qty, Action
                h_item.setTextAlignment(Qt.AlignCenter)
            elif col in [3, 4]:  # Rate, Total
                h_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            else:
                h_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.table.setHorizontalHeaderItem(col, h_item)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 90)   # Code
        self.table.setColumnWidth(2, 110)  # Qty (wide enough for centered spinbox)
        self.table.setColumnWidth(3, 120)  # Rate (₹)
        self.table.setColumnWidth(4, 130)  # Total (₹)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        self.table.setColumnWidth(5, 95)   # Action
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)
        self.table.setStyleSheet("QTableWidget::item { padding: 2px 6px; }")
        bottom_layout.addWidget(self.table, 1)

        # Totals Summary Bar
        summary_bar = QHBoxLayout()
        summary_bar.setContentsMargins(4, 4, 4, 4)
        summary_bar.setSpacing(16)

        self.total_lbl = QLabel("Total Return Value: ₹0.00")
        self.total_lbl.setStyleSheet("font-size: 14.5px; font-weight: bold; color: #4338ca;")

        self.adj_lbl = QLabel("Outstanding Adj: ₹0.00")
        self.adj_lbl.setStyleSheet("font-size: 14.5px; font-weight: bold; color: #dc2626;")

        summary_bar.addWidget(self.total_lbl)
        summary_bar.addWidget(self.adj_lbl)
        summary_bar.addStretch()

        self.save_bottom_btn = QPushButton("Save && Print Return Note")
        self.save_bottom_btn.setProperty("class", "btn-success")
        self.save_bottom_btn.setStyleSheet("min-height: 34px; padding: 0px 16px; font-weight: bold; border-radius: 6px;")
        self.save_bottom_btn.setCursor(Qt.PointingHandCursor)
        self.save_bottom_btn.clicked.connect(self.save_sales_return)
        summary_bar.addWidget(self.save_bottom_btn)

        bottom_layout.addLayout(summary_bar)

        # Add Block 2 with vertical stretch 1
        main_layout.addWidget(bottom_panel, 1)

    def toggle_bank_account(self, mode=None):
        if mode is None:
            mode = self.pay_mode_combo.currentText()
        self.bank_combo.setEnabled(mode == "Bank")

    def check_customer_match(self):
        text = self.customer_combo.currentText().strip()
        if not text or text == "-- Select Customer --":
            self.add_customer_btn.hide()
            return
        
        matched = False
        for i in range(self.customer_combo.count()):
            item_text = self.customer_combo.itemText(i).strip()
            if item_text and item_text != "-- Select Customer --" and item_text.lower() == text.lower():
                matched = True
                if self.customer_combo.currentIndex() != i:
                    self.customer_combo.setCurrentIndex(i)
                break
        
        if not matched:
            self.add_customer_btn.show()
        else:
            self.add_customer_btn.hide()

    def handle_add_customer_click(self):
        from ui.masters.customers import CustomerDialog
        typed_text = self.customer_combo.currentText().strip()
        if typed_text == "-- Select Customer --":
            typed_text = ""
        dlg = CustomerDialog(initial_name=typed_text, parent=self)
        if dlg.exec() == QDialog.Accepted and hasattr(dlg, 'saved_customer_id'):
            self.refresh_data()
            for idx in range(self.customer_combo.count()):
                if self.customer_combo.itemData(idx) == dlg.saved_customer_id:
                    self.customer_combo.setCurrentIndex(idx)
                    break

    def load_customer_invoices(self):
        cust_id = self.customer_combo.currentData()
        self.invoice_combo.blockSignals(True)
        self.invoice_combo.clear()
        self.invoice_combo.addItem("-- Select Invoice (Optional) --", None)
        if cust_id:
            session = Session()
            try:
                invoices = session.query(SalesMaster).filter_by(customer_id=cust_id).order_by(SalesMaster.date.desc()).all()
                for inv in invoices:
                    self.invoice_combo.addItem(f"{inv.invoice_number} (₹{inv.total_amount:.2f})", inv.id)
            except Exception as e:
                print(f"Error loading customer invoices: {e}")
            finally:
                session.close()
        self.invoice_combo.blockSignals(False)
        if any(item.get("from_invoice") for item in self.return_items):
            self.return_items.clear()
            self.update_table()

    def on_invoice_selected(self):
        inv_id = self.invoice_combo.currentData()
        if not inv_id:
            if any(item.get("from_invoice") for item in self.return_items):
                self.return_items.clear()
                self.update_table()
            return

        session = Session()
        try:
            sale = session.query(SalesMaster).get(inv_id)
            if not sale:
                return

            self.return_items.clear()
            for item in sale.items:
                if item.product:
                    p_id = item.product.id
                    p_code = item.product.product_code or "-"
                    bm = getattr(item.product, 'brand_model', None) or getattr(item.product, 'brand', '') or ''
                    p_name = f"{item.product.name} ({bm})" if bm else item.product.name
                else:
                    p_id = item.product_id
                    p_code = "-"
                    p_name = f"Product #{item.product_id}"

                # Calculate effective charged rate per item (accounting for discounts and tax)
                item_discount = getattr(item, 'discount', 0.0) or 0.0
                item_tax = getattr(item, 'tax_amount', 0.0) or 0.0
                charged_subtotal = (item.qty * item.rate) - item_discount + item_tax
                effective_rate = round(charged_subtotal / item.qty, 2) if item.qty > 0 else item.rate

                self.return_items.append({
                    "product_id": p_id,
                    "product_code": p_code,
                    "name": p_name,
                    "qty": item.qty,
                    "max_qty": item.qty,
                    "rate": effective_rate,
                    "unit": getattr(item, 'unit', 'Pcs') or 'Pcs',
                    "from_invoice": True
                })

            self.update_table()

            # Suggest refund amount vs balance deduction
            total_return = sum(it["qty"] * it["rate"] for it in self.return_items)
            paid_amount = getattr(sale, 'paid_amount', 0.0) or 0.0
            suggested_refund = min(paid_amount, total_return)
            self.refund_input.setValue(suggested_refund)
            self.update_summary()

        except Exception as e:
            print(f"Error loading invoice items for return: {e}")
        finally:
            session.close()

    def on_item_qty_changed(self, row_idx, val):
        if 0 <= row_idx < len(self.return_items):
            self.return_items[row_idx]["qty"] = val
            subtotal = val * self.return_items[row_idx]["rate"]
            tot_item = self.table.item(row_idx, 4)
            if tot_item:
                tot_item.setText(f"{subtotal:,.2f}")
            self.update_summary()

    def filter_products_by_category(self):
        self.product_combo.blockSignals(True)
        self.product_combo.clear()
        
        cat_name = self.category_combo.currentText()
        for prod_id, p in self.products_cache.items():
            if cat_name == "-- All Categories --" or p.category == cat_name:
                bm = getattr(p, 'brand_model', None) or getattr(p, 'brand', '') or ''
                display_txt = f"{p.name} ({bm})" if bm else p.name
                self.product_combo.addItem(display_txt, p.id)
                
        self.product_combo.blockSignals(False)
        self.update_rate_on_product_change()

    def update_rate_on_product_change(self):
        prod_id = self.product_combo.currentData()
        if prod_id and prod_id in self.products_cache:
            prod = self.products_cache[prod_id]
            self.rate_input.setValue(prod.selling_price)
            if hasattr(self, 'product_code_input'):
                if prod.product_code:
                    self.product_code_input.setText(prod.product_code)
                else:
                    self.product_code_input.clear()
        else:
            self.rate_input.setValue(0.0)
            if hasattr(self, 'product_code_input'):
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

    def refresh_data(self):
        session = Session()
        try:
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

            self.customer_combo.blockSignals(True)
            self.category_combo.blockSignals(True)
            self.bank_combo.blockSignals(True)

            # Load Customers (excluding Cash default if needed, or including all)
            self.customer_combo.clear()
            self.customer_combo.addItem("-- Select Customer --", None)
            customers = session.query(Customer).all()
            for c in customers:
                self.customer_combo.addItem(c.name, c.id)
            self.customer_combo.update_completer()

            # Load Categories
            self.category_combo.clear()
            self.category_combo.addItem("-- All Categories --")
            categories = session.query(Category).all()
            for c in categories:
                self.category_combo.addItem(c.name)

            # Load Banks
            self.bank_combo.clear()
            banks = session.query(BankAccount).all()
            for b in banks:
                self.bank_combo.addItem(f"{b.bank_name} ({b.account_name})", b.id)

            # Clear Ref Sales Invoice combo
            self.invoice_combo.blockSignals(True)
            self.invoice_combo.clear()
            self.invoice_combo.addItem("-- Select Invoice (Optional) --", None)
            self.invoice_combo.blockSignals(False)

            # Auto-suggest Return Number
            self.return_no_input.setText(generate_next_sales_return_number(session))

            self.customer_combo.blockSignals(False)
            self.category_combo.blockSignals(False)
            self.bank_combo.blockSignals(False)

            self.check_customer_match()
            self.filter_products_by_category()
        except Exception as e:
            print(f"Error loading sales return fields: {e}")
        finally:
            session.close()

    def add_item_to_list(self):
        prod_idx = self.product_combo.currentIndex()
        if prod_idx < 0:
            return

        prod_id = self.product_combo.currentData()
        qty = self.qty_input.value()
        rate = self.rate_input.value()

        p_cache = self.products_cache.get(prod_id)
        if not p_cache:
            return

        # Check if already added
        for item in self.return_items:
            if item["product_id"] == prod_id:
                item["qty"] += qty
                item["rate"] = rate
                self.update_table()
                self.reset_item_inputs()
                return

        self.return_items.append({
            "product_id": prod_id,
            "product_code": p_cache.product_code if p_cache.product_code else "-",
            "name": p_cache.name,
            "qty": qty,
            "rate": rate
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
        QTimer.singleShot(0, self._focus_product_code)

    def _focus_product_code(self):
        self.product_code_input.setFocus()
        self.product_code_input.selectAll()

    def delete_item(self, row_idx):
        self.return_items.pop(row_idx)
        self.update_table()

    def update_table(self):
        self.table.setRowCount(len(self.return_items))
        for i, item in enumerate(self.return_items):
            # Code
            c_item = QTableWidgetItem(item.get("product_code", "-"))
            c_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 0, c_item)

            # Name
            n_item = QTableWidgetItem(item["name"])
            n_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.table.setItem(i, 1, n_item)

            # Qty: Editable QSpinBox with max allowable return qty
            qty_container = QWidget()
            qty_container.setStyleSheet("background: transparent; margin: 0px; padding: 0px;")
            qty_layout = QHBoxLayout(qty_container)
            qty_layout.setContentsMargins(0, 0, 0, 0)
            qty_layout.setSpacing(0)
            qty_layout.setAlignment(Qt.AlignCenter)
            qty_spin = QSpinBox()
            max_q = item.get("max_qty", 99999) or 99999
            qty_spin.setRange(1, max_q)
            qty_spin.setValue(item["qty"])
            qty_spin.setFixedSize(76, 28)
            qty_spin.setAlignment(Qt.AlignCenter)
            qty_spin.setStyleSheet(
                "QSpinBox { background: #ffffff; border: 1.5px solid #cbd5e1; border-radius: 6px; "
                "padding: 0px 4px !important; min-height: 28px !important; max-height: 28px !important; height: 28px !important; "
                "font-size: 13px; font-weight: bold; color: #0f172a; margin: 0px !important; } "
                "QSpinBox:focus { border: 1.5px solid #f59e0b; background-color: #fffbeb; }"
            )
            qty_spin.valueChanged.connect(lambda val, idx=i: self.on_item_qty_changed(idx, val))
            qty_layout.addWidget(qty_spin)
            self.table.setCellWidget(i, 2, qty_container)

            # Rate
            r_item = QTableWidgetItem(f"{item['rate']:,.2f}")
            r_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(i, 3, r_item)
            
            # Total
            subtotal = item["qty"] * item["rate"]
            tot_item = QTableWidgetItem(f"{subtotal:,.2f}")
            tot_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            tot_item.setForeground(Qt.darkGreen)
            self.table.setItem(i, 4, tot_item)

            # Delete Action
            btn_container = QWidget()
            btn_container.setStyleSheet("background: transparent; margin: 0px; padding: 0px;")
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(0, 0, 0, 0)
            btn_layout.setSpacing(0)
            btn_layout.setAlignment(Qt.AlignCenter)

            del_btn = QPushButton("Delete")
            del_btn.setProperty("class", "btn-action-delete")
            del_btn.setFixedSize(68, 26)
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.clicked.connect(lambda checked, idx=i: self.delete_item(idx))
            btn_layout.addWidget(del_btn)
            self.table.setCellWidget(i, 5, btn_container)

        self.update_summary()

    def update_summary(self):
        total = sum(item["qty"] * item["rate"] for item in self.return_items)
        refund = self.refund_input.value()
        
        if refund > total:
            refund = total
            self.refund_input.setValue(refund)
            
        adj = total - refund
        self.bal_deducted_input.setValue(adj)

        self.total_lbl.setText(f"Total Return Value: ₹{format_inr(total)}")
        self.adj_lbl.setText(f"Outstanding Adj: ₹{format_inr(adj)}")
        if hasattr(self, 'adj_badge'):
            self.adj_badge.setText(f"Outstanding Adj: ₹{format_inr(adj)}")

    def save_sales_return(self):
        if hasattr(self, 'save_btn'):
            self.save_btn.setEnabled(False)
        if hasattr(self, 'save_bottom_btn'):
            self.save_bottom_btn.setEnabled(False)
        return_no = self.return_no_input.text().strip()
        cust_id = self.customer_combo.currentData()
        
        if not return_no:
            QMessageBox.warning(self, "Validation Error", "Please enter Return Number.")
            if hasattr(self, 'save_btn'): self.save_btn.setEnabled(True)
            if hasattr(self, 'save_bottom_btn'): self.save_bottom_btn.setEnabled(True)
            return
        if not cust_id:
            QMessageBox.warning(self, "Validation Error", "Please select a Customer.")
            if hasattr(self, 'save_btn'): self.save_btn.setEnabled(True)
            if hasattr(self, 'save_bottom_btn'): self.save_bottom_btn.setEnabled(True)
            return
        if not self.return_items:
            QMessageBox.warning(self, "Validation Error", "Please add at least one item to the return.")
            if hasattr(self, 'save_btn'): self.save_btn.setEnabled(True)
            if hasattr(self, 'save_bottom_btn'): self.save_bottom_btn.setEnabled(True)
            return

        total = sum(item["qty"] * item["rate"] for item in self.return_items)
        refund = self.refund_input.value()
        if refund > total + 0.001:
            QMessageBox.warning(
                self, "Invalid Refund",
                f"Refund amount (₹{format_inr(refund)}) cannot exceed total return value (₹{format_inr(total)})!"
            )
            if hasattr(self, 'save_btn'): self.save_btn.setEnabled(True)
            if hasattr(self, 'save_bottom_btn'): self.save_bottom_btn.setEnabled(True)
            return
        adj = total - refund

        date_q = self.date_input.date()
        ret_date = datetime.date(date_q.year(), date_q.month(), date_q.day())

        pay_mode = self.pay_mode_combo.currentText()
        bank_id = self.bank_combo.currentData() if pay_mode == "Bank" else None
        sales_master_id = self.invoice_combo.currentData()

        session = Session()
        try:
            # Check duplicate return number
            existing = session.query(SalesReturnMaster).filter_by(return_number=return_no).first()
            if existing:
                next_no = generate_next_sales_return_number(session)
                QMessageBox.warning(
                    self,
                    "Duplicate Return Number",
                    f"Return number '{return_no}' already exists in the database.\n\n"
                    f"Next available return number '{next_no}' has been assigned automatically.\n"
                    f"If you wish to save a new return, please review and click Save again."
                )
                self.return_no_input.setText(next_no)
                return

            # If bank transaction, check bank balance for paying refund
            if pay_mode == "Bank" and refund > 0:
                bank = session.query(BankAccount).get(bank_id)
                if bank.balance < refund:
                    QMessageBox.warning(self, "Insufficient Funds", f"Insufficient bank balance to refund. Current: ₹{bank.balance:.2f}")
                    return

            # Save Sales Return Master
            sales_return = SalesReturnMaster(
                return_number=return_no,
                date=ret_date,
                sales_id=sales_master_id,
                customer_id=cust_id,
                total_amount=total,
                refund_amount=refund,
                balance_deducted=adj
            )
            session.add(sales_return)
            session.flush()

            # Save Items, update stock
            pdf_items = []
            for item in self.return_items:
                ret_item = SalesReturnItem(
                    sales_return_id=sales_return.id,
                    product_id=item["product_id"],
                    qty=item["qty"],
                    rate=item["rate"]
                )
                session.add(ret_item)

                prod = session.query(Product).get(item["product_id"])
                if prod:
                    prod.stock_qty += item["qty"]
                    bm = getattr(prod, 'brand_model', None) or getattr(prod, 'brand', '') or ''
                    p_name = f"{prod.name} ({bm})" if bm else prod.name
                else:
                    p_name = f"Unknown Product (ID: {item['product_id']})"

                pdf_items.append({
                    "name": p_name,
                    "qty": item["qty"],
                    "rate": item["rate"],
                    "total": item["qty"] * item["rate"]
                })

            # Update customer balance (reduces debt)
            customer = session.query(Customer).get(cust_id)
            customer.outstanding_balance -= adj

            # Record ledger details if refund paid
            if refund > 0:
                desc = f"Refund paid for sales return {return_no}"
                if pay_mode == "Cash":
                    tx_cash = CashTransaction(
                        date=ret_date,
                        transaction_type='out',
                        amount=refund,
                        source_type='sales_return',
                        source_id=sales_return.id,
                        description=desc
                    )
                    session.add(tx_cash)
                else:
                    tx_bank = BankTransaction(
                        date=ret_date,
                        transaction_type='withdrawal',
                        account_id=bank_id,
                        amount=refund,
                        source_type='sales_return',
                        source_id=sales_return.id,
                        description=desc
                    )
                    session.add(tx_bank)
                    
                    bank = session.query(BankAccount).get(bank_id)
                    bank.balance -= refund

            session.commit()

            # Generate PDF Credit Note
            s_name = session.query(Setting).filter_by(key='shop_name').first().value
            s_contact = session.query(Setting).filter_by(key='shop_contact').first().value
            s_address = session.query(Setting).filter_by(key='shop_address').first().value
            s_gst = session.query(Setting).filter_by(key='shop_gst').first().value

            ref_invoice_num = None
            if sales_master_id:
                ref_invoice_obj = session.query(SalesMaster).get(sales_master_id)
                if ref_invoice_obj:
                    ref_invoice_num = ref_invoice_obj.invoice_number

            pdf_data = {
                "shop_name": s_name,
                "shop_contact": s_contact,
                "shop_address": s_address,
                "shop_gst": s_gst,
                "return_number": return_no,
                "date": ret_date.strftime("%Y-%m-%d"),
                "invoice_number": ref_invoice_num,
                "customer_name": customer.name,
                "customer_mobile": customer.mobile,
                "customer_address": customer.address,
                "items": pdf_items,
                "total_amount": total,
                "refund_amount": refund,
                "balance_deducted": adj
            }

            os.makedirs("invoices", exist_ok=True)
            path = os.path.abspath(f"invoices/{return_no}.pdf")
            generate_sales_return_pdf(pdf_data, path)

            QMessageBox.information(self, "Success", f"Sales return saved successfully!\nPDF generated at:\n{path}")
            
            try:
                os.startfile(path)
            except Exception as e:
                print(f"Could not auto-open PDF: {e}")

            # Reset fields
            self.return_items.clear()
            self.update_table()
            self.refund_input.setValue(0.0)
            self.qty_input.setValue(1)
            self.refresh_data()

            if self.history_widget:
                self.history_widget.load_history()

        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save return: {e}")
        finally:
            if hasattr(self, 'save_btn'):
                self.save_btn.setEnabled(True)
            if hasattr(self, 'save_bottom_btn'):
                self.save_bottom_btn.setEnabled(True)
            session.close()


class SalesReturnHistoryWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.offset = 0
        self.has_more = True
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Filters
        filters_frame = QFrame()
        filters_frame.setProperty("class", "CardFrame")
        filters_layout = QHBoxLayout(filters_frame)
        filters_layout.setContentsMargins(15, 12, 15, 12)
        filters_layout.setSpacing(15)

        filters_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Return # or Customer Name...")
        self.search_input.textChanged.connect(self.load_history)
        filters_layout.addWidget(self.search_input, 2)

        filters_layout.addWidget(QLabel("From:"))
        self.from_date = QDateEdit()
        self.from_date.setCalendarPopup(True)
        self.from_date.setDate(QDate.currentDate().addMonths(-1))
        self.from_date.dateChanged.connect(self.load_history)
        filters_layout.addWidget(self.from_date)

        filters_layout.addWidget(QLabel("To:"))
        self.to_date = QDateEdit()
        self.to_date.setCalendarPopup(True)
        self.to_date.setDate(QDate.currentDate())
        self.to_date.dateChanged.connect(self.load_history)
        filters_layout.addWidget(self.to_date)

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setProperty("class", "btn-secondary")
        self.reset_btn.clicked.connect(self.reset_filters)
        filters_layout.addWidget(self.reset_btn)

        layout.addWidget(filters_frame)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Return #", "Date", "Customer Name", "Total (₹)", "Refunded (₹)", "Adj Balance (₹)", "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Fixed)
        self.table.setColumnWidth(6, 270)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)
        layout.addWidget(self.table)

        self.table.verticalScrollBar().valueChanged.connect(self.handle_scroll)

    def reset_filters(self):
        self.search_input.clear()
        self.from_date.setDate(QDate.currentDate().addMonths(-1))
        self.to_date.setDate(QDate.currentDate())
        self.load_history()

    def handle_scroll(self, value):
        scrollbar = self.table.verticalScrollBar()
        if value == scrollbar.maximum() and scrollbar.maximum() > 0:
            if self.has_more:
                self.offset += 25
                self.load_history(reset=False)

    def load_history(self, reset=True):
        if not isinstance(reset, bool):
            reset = True
        if reset:
            self.offset = 0
            self.has_more = True
            self.table.setRowCount(0)

        session = Session()
        try:
            query = session.query(SalesReturnMaster)
            
            # Date filter
            f_date = self.from_date.date()
            t_date = self.to_date.date()
            from_d = datetime.date(f_date.year(), f_date.month(), f_date.day())
            to_d = datetime.date(t_date.year(), t_date.month(), t_date.day())
            query = query.filter(SalesReturnMaster.date >= from_d, SalesReturnMaster.date <= to_d)

            # Search text filter
            search = self.search_input.text().strip()
            if search:
                query = query.join(Customer).filter(
                    (SalesReturnMaster.return_number.ilike(f"%{search}%")) |
                    (Customer.name.ilike(f"%{search}%"))
                )

            returns = query.order_by(SalesReturnMaster.date.desc(), SalesReturnMaster.id.desc()).offset(self.offset).limit(25).all()

            if len(returns) < 25:
                self.has_more = False

            start_row = self.table.rowCount()
            self.table.setRowCount(start_row + len(returns))
            for idx, r in enumerate(returns):
                i = start_row + idx
                self.table.setItem(i, 0, QTableWidgetItem(r.return_number))
                self.table.setItem(i, 1, QTableWidgetItem(r.date.strftime("%Y-%m-%d")))
                self.table.setItem(i, 2, QTableWidgetItem(r.customer.name))
                self.table.setItem(i, 3, QTableWidgetItem(f"₹{format_inr(r.total_amount)}"))
                self.table.setItem(i, 4, QTableWidgetItem(f"₹{format_inr(r.refund_amount)}"))
                self.table.setItem(i, 5, QTableWidgetItem(f"₹{format_inr(r.balance_deducted)}"))

                # Action Buttons
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(6, 4, 6, 4)
                actions_layout.setSpacing(8)
                actions_layout.setAlignment(Qt.AlignCenter)

                view_btn = QPushButton("View")
                view_btn.setProperty("class", "btn-action-view")
                view_btn.clicked.connect(lambda checked, rid=r.id: self.view_details(rid))
                actions_layout.addWidget(view_btn)

                print_btn = QPushButton("Print")
                print_btn.setProperty("class", "btn-action-print")
                print_btn.clicked.connect(lambda checked, rid=r.id: self.print_return(rid))
                actions_layout.addWidget(print_btn)

                del_btn = QPushButton("Delete")
                del_btn.setProperty("class", "btn-action-delete")
                del_btn.clicked.connect(lambda checked, rid=r.id: self.delete_return(rid))
                actions_layout.addWidget(del_btn)

                self.table.setCellWidget(i, 6, actions_widget)

        except Exception as e:
            print(f"Error loading returns history: {e}")
        finally:
            session.close()

    def view_details(self, return_id):
        session = Session()
        try:
            ret = session.query(SalesReturnMaster).get(return_id)
            if not ret:
                QMessageBox.warning(self, "Error", "Return record not found.")
                return

            dialog = QDialog(self)
            dialog.setWindowTitle(f"Sales Return Details - {ret.return_number}")
            dialog.setMinimumSize(550, 400)
            dlg_layout = QVBoxLayout(dialog)

            info_frame = QFrame()
            info_frame.setProperty("class", "CardFrame")
            info_layout = QFormLayout(info_frame)
            info_layout.addRow("Return Number:", QLabel(ret.return_number))
            info_layout.addRow("Date:", QLabel(ret.date.strftime("%Y-%m-%d")))
            info_layout.addRow("Customer Name:", QLabel(ret.customer.name))
            if ret.sales:
                info_layout.addRow("Ref Sales Invoice:", QLabel(ret.sales.invoice_number))
            dlg_layout.addWidget(info_frame)

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
            
            items = session.query(SalesReturnItem).filter_by(sales_return_id=return_id).all()
            items_table.setRowCount(len(items))
            for i, item in enumerate(items):
                if item.product:
                    bm = getattr(item.product, 'brand_model', None) or getattr(item.product, 'brand', '') or ''
                    disp_name = f"{item.product.name} ({bm})" if bm else item.product.name
                else:
                    disp_name = f"Product ID: {item.product_id}"
                items_table.setItem(i, 0, QTableWidgetItem(p_code))
                items_table.setItem(i, 1, QTableWidgetItem(disp_name))
                items_table.setItem(i, 2, QTableWidgetItem(str(item.qty)))
                items_table.setItem(i, 3, QTableWidgetItem(f"{item.rate:.2f}"))
                items_table.setItem(i, 4, QTableWidgetItem(f"{(item.qty * item.rate):.2f}"))
            dlg_layout.addWidget(items_table)

            totals_frame = QFrame()
            totals_layout = QFormLayout(totals_frame)
            totals_layout.addRow("Total Return Amount:", QLabel(f"₹{format_inr(ret.total_amount)}"))
            totals_layout.addRow("Refund Paid:", QLabel(f"₹{format_inr(ret.refund_amount)}"))
            totals_layout.addRow("Outstanding Adjusted:", QLabel(f"₹{format_inr(ret.balance_deducted)}"))
            dlg_layout.addWidget(totals_frame)

            btn_box = QHBoxLayout()
            btn_box.addStretch()
            close_btn = QPushButton("Close")
            close_btn.setProperty("class", "btn-secondary")
            close_btn.clicked.connect(dialog.accept)
            btn_box.addWidget(close_btn)
            dlg_layout.addLayout(btn_box)

            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load details: {e}")
        finally:
            session.close()

    def print_return(self, return_id):
        session = Session()
        try:
            ret = session.query(SalesReturnMaster).get(return_id)
            if not ret:
                QMessageBox.warning(self, "Error", "Return record not found.")
                return

            s_name = session.query(Setting).filter_by(key='shop_name').first().value
            s_contact = session.query(Setting).filter_by(key='shop_contact').first().value
            s_address = session.query(Setting).filter_by(key='shop_address').first().value
            s_gst = session.query(Setting).filter_by(key='shop_gst').first().value

            pdf_items = []
            for item in ret.items:
                if item.product:
                    bm = getattr(item.product, 'brand_model', None) or getattr(item.product, 'brand', '') or ''
                    p_name = f"{item.product.name} ({bm})" if bm else item.product.name
                else:
                    p_name = f"Unknown Product (ID: {item.product_id})"

                pdf_items.append({
                    "name": p_name,
                    "qty": item.qty,
                    "rate": item.rate,
                    "total": item.qty * item.rate
                })

            pdf_data = {
                "shop_name": s_name,
                "shop_contact": s_contact,
                "shop_address": s_address,
                "shop_gst": s_gst,
                "return_number": ret.return_number,
                "date": ret.date.strftime("%Y-%m-%d"),
                "invoice_number": ret.sales.invoice_number if ret.sales else None,
                "customer_name": ret.customer.name,
                "customer_mobile": ret.customer.mobile,
                "customer_address": ret.customer.address,
                "items": pdf_items,
                "total_amount": ret.total_amount,
                "refund_amount": ret.refund_amount,
                "balance_deducted": ret.balance_deducted
            }

            os.makedirs("invoices", exist_ok=True)
            path = os.path.abspath(f"invoices/{ret.return_number}.pdf")
            generate_sales_return_pdf(pdf_data, path)

            QMessageBox.information(self, "Success", f"Sales return PDF generated at:\n{path}")
            try:
                os.startfile(path)
            except Exception as e:
                print(f"Could not auto-open PDF: {e}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate PDF: {e}")
        finally:
            session.close()

    def delete_return(self, return_id):
        confirm = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this return record?\nAll stock additions and outstanding adjustments will be reverted.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        session = Session()
        try:
            ret = session.query(SalesReturnMaster).get(return_id)
            if not ret:
                QMessageBox.warning(self, "Error", "Return record not found.")
                return

            # Check if reverting any item would cause negative stock
            required_revert = {}
            for item in ret.items:
                required_revert[item.product_id] = required_revert.get(item.product_id, 0) + item.qty

            for prod_id, req_qty in required_revert.items():
                prod = session.query(Product).get(prod_id)
                if prod and prod.stock_qty < req_qty:
                    QMessageBox.warning(
                        self, "Cannot Delete Return",
                        f"Cannot delete this return record because product '{prod.name}' currently has only "
                        f"{prod.stock_qty} in stock, but cancelling requires deducting {req_qty}. "
                        f"Some returned items have already been sold or used. Deleting would cause negative stock."
                    )
                    session.close()
                    return

            # Revert stock additions
            for item in ret.items:
                prod = session.query(Product).get(item.product_id)
                if prod:
                    prod.stock_qty -= item.qty # deduct stock since return is cancelled

            # Revert customer outstanding balance deduction
            customer = session.query(Customer).get(ret.customer_id)
            if customer:
                customer.outstanding_balance += ret.balance_deducted

            # Delete refund transactions
            cash_txs = session.query(CashTransaction).filter_by(source_type='sales_return', source_id=ret.id).all()
            for tx in cash_txs:
                session.delete(tx)

            bank_txs = session.query(BankTransaction).filter_by(source_type='sales_return', source_id=ret.id).all()
            for tx in bank_txs:
                bank = session.query(BankAccount).get(tx.account_id)
                if bank:
                    bank.balance += tx.amount # Revert bank deduction
                session.delete(tx)

            session.delete(ret)
            session.commit()

            QMessageBox.information(self, "Success", "Return record deleted and stock/ledger reverted successfully.")
            self.load_history()
            
            # Notify parent window / main view to refresh stock labels if any
            main_window = self.window()
            if hasattr(main_window, 'sales_view') and hasattr(main_window.sales_view, 'refresh_data'):
                main_window.sales_view.refresh_data()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to delete return record: {e}")
        finally:
            session.close()
