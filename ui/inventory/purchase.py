import datetime
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, 
                             QDateEdit, QSpinBox, QDoubleSpinBox, QPushButton, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QMessageBox, QFrame, QFormLayout,
                             QTabWidget, QDialog, QDialogButtonBox, QCompleter)
from PySide6.QtCore import Qt, QDate
from database import Session, Setting
from models import Supplier, Product, BankAccount, PurchaseMaster, PurchaseItem, CashTransaction, BankTransaction, Category
from utils.pdf_generator import generate_purchase_pdf

class PurchaseView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bill_items = []  # list of dicts: {"product_id": int, "name": str, "qty": int, "rate": float}
        self.editing_purchase_id = None  # Tracks if we are editing a purchase bill
        self.products_cache = {}
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

        title_lbl = QLabel("Purchase Invoice Details")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff;")
        left_layout.addWidget(title_lbl)

        form_layout = QFormLayout()
        
        self.invoice_input = QLineEdit()
        self.invoice_input.setPlaceholderText("e.g. PUR-1004")
        
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())
        
        self.supplier_combo = QComboBox()
        self.supplier_combo.setEditable(True)
        self.supplier_combo.setInsertPolicy(QComboBox.NoInsert)
        self.supplier_combo.currentTextChanged.connect(self.check_supplier_match)
        if self.supplier_combo.lineEdit():
            self.supplier_combo.lineEdit().textChanged.connect(self.check_supplier_match)

        supp_layout = QHBoxLayout()
        supp_layout.setContentsMargins(0, 0, 0, 0)
        supp_layout.setSpacing(6)
        supp_layout.addWidget(self.supplier_combo, 1)

        self.add_supplier_btn = QPushButton("+")
        self.add_supplier_btn.setToolTip("Add new supplier")
        self.add_supplier_btn.setProperty("class", "btn-quick-add")
        self.add_supplier_btn.setFixedWidth(40)
        self.add_supplier_btn.setStyleSheet("padding: 0px; font-size: 18px; font-weight: bold; text-align: center;")
        self.add_supplier_btn.setCursor(Qt.PointingHandCursor)
        self.add_supplier_btn.clicked.connect(self.handle_add_supplier_click)
        self.add_supplier_btn.hide()
        supp_layout.addWidget(self.add_supplier_btn)
        
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
        form_layout.addRow("Supplier:", supp_layout)
        form_layout.addRow("Payment Mode:", self.pay_mode_combo)
        form_layout.addRow("Select Bank A/c:", self.bank_combo)
        form_layout.addRow("Paid Amount (₹):", self.paid_input)

        left_layout.addLayout(form_layout)
        left_layout.addStretch()

        # Action Buttons Layout (Save/Update and Cancel Edit)
        btn_layout = QHBoxLayout()

        self.save_btn = QPushButton("Save Purchase Bill")
        self.save_btn.setProperty("class", "btn-success")
        self.save_btn.setFixedHeight(40)
        self.save_btn.clicked.connect(self.save_purchase)
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
        entry_title = QLabel("Add Items to Bill")
        entry_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        right_layout.addWidget(entry_title)

        row1_layout = QHBoxLayout()
        
        self.product_code_input = QLineEdit()
        self.product_code_input.setPlaceholderText("Code")
        self.product_code_input.setFixedWidth(120)
        self.product_code_input.returnPressed.connect(self.handle_product_code_entry)
        row1_layout.addWidget(QLabel("Product Code:"), 0)
        row1_layout.addWidget(self.product_code_input, 1)
        
        self.category_combo = QComboBox()
        self.category_combo.currentIndexChanged.connect(self.filter_products_by_category)
        row1_layout.addWidget(QLabel("Category:"), 0)
        row1_layout.addWidget(self.category_combo, 2)
        
        self.product_combo = QComboBox()
        self.product_combo.setPlaceholderText("Select Product")
        self.product_combo.currentIndexChanged.connect(self.update_rate_on_product_change)
        row1_layout.addWidget(QLabel("Product Name:"), 0)
        row1_layout.addWidget(self.product_combo, 4)

        right_layout.addLayout(row1_layout)

        row2_layout = QHBoxLayout()

        self.brand_input = QLineEdit()
        self.brand_input.setPlaceholderText("Brand")
        row2_layout.addWidget(QLabel("Brand:"), 0)
        row2_layout.addWidget(self.brand_input, 1)

        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("Model")
        row2_layout.addWidget(QLabel("Model:"), 0)
        row2_layout.addWidget(self.model_input, 1)

        right_layout.addLayout(row2_layout)

        row3_layout = QHBoxLayout()

        self.rate_input = QDoubleSpinBox()
        self.rate_input.setRange(0.0, 9999999.0)
        self.rate_input.setValue(0.0)
        self.rate_input.setDecimals(2)
        row3_layout.addWidget(QLabel("Purchase Price (₹):"), 0)
        row3_layout.addWidget(self.rate_input, 2)

        self.selling_price_input = QDoubleSpinBox()
        self.selling_price_input.setRange(0.0, 9999999.0)
        self.selling_price_input.setValue(0.0)
        self.selling_price_input.setDecimals(2)
        row3_layout.addWidget(QLabel("Selling Price (₹):"), 0)
        row3_layout.addWidget(self.selling_price_input, 2)

        self.qty_input = QSpinBox()
        self.qty_input.setRange(1, 1000)
        self.qty_input.setValue(1)
        row3_layout.addWidget(QLabel("Qty:"), 0)
        row3_layout.addWidget(self.qty_input, 1)

        self.add_item_btn = QPushButton("Add Item")
        self.add_item_btn.clicked.connect(self.add_item_to_list)
        row3_layout.addWidget(self.add_item_btn, 2)

        right_layout.addLayout(row3_layout)

        # Items Table
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels(["Product Code", "Product Name", "Category", "Brand", "Model", "Qty", "Purchase Price (₹)", "Selling Price (₹)", "Total (₹)", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(9, QHeaderView.Fixed)
        self.table.setColumnWidth(9, 100)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(54)
        right_layout.addWidget(self.table)

        # Summary Bar (Totals, Paid, Balance)
        summary_bar = QHBoxLayout()
        
        self.total_lbl = QLabel("Total Amount: ₹0.00")
        self.total_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #6366f1;")
        
        self.balance_lbl = QLabel("Balance Payable: ₹0.00")
        self.balance_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #ef4444;")
        
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

        # Re-attach completer model
        completer = QCompleter(self.supplier_combo.model(), self.supplier_combo)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.supplier_combo.setCompleter(completer)
        self.supplier_combo.blockSignals(False)

        if curr_id is not None:
            idx = self.supplier_combo.findData(curr_id)
            if idx >= 0:
                self.supplier_combo.setCurrentIndex(idx)
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

    def filter_products_by_category(self):
        self.product_combo.blockSignals(True)
        self.product_combo.clear()
        
        cat_name = self.category_combo.currentText()
        for prod_id, p in self.products_cache.items():
            if cat_name == "-- All Categories --" or p.category == cat_name:
                display_txt = f"{p.name} ({p.brand} - {p.model})"
                if p.imei:
                    display_txt += f" [IMEI: {p.imei}]"
                self.product_combo.addItem(display_txt, p.id)
                
        self.product_combo.blockSignals(False)
        self.update_rate_on_product_change()

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
            self.supplier_combo.blockSignals(True)
            self.category_combo.blockSignals(True)
            self.bank_combo.blockSignals(True)

            # Load Suppliers
            self.load_suppliers()

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
            if not self.editing_purchase_id:
                last_p = session.query(PurchaseMaster).order_by(PurchaseMaster.id.desc()).first()
                if last_p:
                    self.invoice_input.setText(f"PUR-{last_p.id + 1001}")
                else:
                    self.invoice_input.setText("PUR-1001")

            # 3. Unblock signals and filter/load
            self.supplier_combo.blockSignals(False)
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
            print(f"Error loading purchase options: {e}")
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
                self.history_table.setItem(i, 3, QTableWidgetItem(f"₹{p.total_amount:,.2f}"))
                self.history_table.setItem(i, 4, QTableWidgetItem(f"₹{p.paid_amount:,.2f}"))
                self.history_table.setItem(i, 5, QTableWidgetItem(f"₹{p.balance_payable:,.2f}"))
                
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

    def toggle_bank_account(self, mode):
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
        else:
            self.rate_input.setValue(0.0)
            if hasattr(self, 'selling_price_input'):
                self.selling_price_input.setValue(0.0)
            if hasattr(self, 'brand_input'):
                self.brand_input.clear()
            if hasattr(self, 'model_input'):
                self.model_input.clear()
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

    def add_item_to_list(self):
        prod_idx = self.product_combo.currentIndex()
        if prod_idx < 0:
            return

        prod_id = self.product_combo.currentData()
        qty = self.qty_input.value()
        rate = self.rate_input.value()
        selling_price = self.selling_price_input.value() if hasattr(self, 'selling_price_input') else 0.0
        brand = self.brand_input.text().strip() if hasattr(self, 'brand_input') else ""
        model = self.model_input.text().strip() if hasattr(self, 'model_input') else ""

        p_cache = self.products_cache.get(prod_id)
        prod_text = p_cache.name if p_cache else self.product_combo.currentText()
        prod_code = p_cache.product_code if p_cache else "-"
        category = p_cache.category if p_cache else "-"

        # Check if already added
        for item in self.bill_items:
            if item["product_id"] == prod_id:
                item["qty"] += qty
                item["rate"] = rate  # update with latest rate
                item["selling_price"] = selling_price
                item["brand"] = brand
                item["model"] = model
                item["category"] = category
                self.update_table()
                return

        self.bill_items.append({
            "product_id": prod_id,
            "product_code": prod_code,
            "name": prod_text,
            "category": category,
            "brand": brand,
            "model": model,
            "qty": qty,
            "rate": rate,
            "selling_price": selling_price
        })
        
        self.update_table()

    def delete_item(self, row_idx):
        self.bill_items.pop(row_idx)
        self.update_table()

    def update_table(self):
        self.table.setRowCount(len(self.bill_items))
        for i, item in enumerate(self.bill_items):
            self.table.setItem(i, 0, QTableWidgetItem(item.get("product_code", "-")))
            self.table.setItem(i, 1, QTableWidgetItem(item.get("name", "-")))
            self.table.setItem(i, 2, QTableWidgetItem(item.get("category", "-")))
            self.table.setItem(i, 3, QTableWidgetItem(item.get("brand", "-")))
            self.table.setItem(i, 4, QTableWidgetItem(item.get("model", "-")))
            self.table.setItem(i, 5, QTableWidgetItem(str(item.get("qty", 0))))
            self.table.setItem(i, 6, QTableWidgetItem(f"{item.get('rate', 0.0):.2f}"))
            self.table.setItem(i, 7, QTableWidgetItem(f"{item.get('selling_price', 0.0):.2f}"))
            
            subtotal = item.get("qty", 0) * item.get("rate", 0.0)
            self.table.setItem(i, 8, QTableWidgetItem(f"{subtotal:.2f}"))

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
            self.table.setCellWidget(i, 9, btn_container)

        self.update_summary()

    def update_summary(self):
        total = sum(item["qty"] * item["rate"] for item in self.bill_items)
        paid = self.paid_input.value()
        balance = total - paid
        if balance < 0:
            balance = 0.0

        self.total_lbl.setText(f"Total Amount: ₹{total:,.2f}")
        self.balance_lbl.setText(f"Balance Payable: ₹{balance:,.2f}")

    def save_purchase(self):
        invoice_no = self.invoice_input.text().strip()
        supp_id = self.supplier_combo.currentData()
        
        if not invoice_no:
            QMessageBox.warning(self, "Validation Error", "Please enter Invoice Number.")
            return
        if not self.bill_items:
            QMessageBox.warning(self, "Validation Error", "Please add at least one item to the bill.")
            return

        total = sum(item["qty"] * item["rate"] for item in self.bill_items)
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
                session.query(PurchaseItem).filter_by(purchase_id=purchase.id).delete()

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
                    balance_payable=balance
                )
                session.add(purchase)
                session.flush() # Get purchase ID safely within the transaction

            # Save Purchase Items & update stocks
            for item in self.bill_items:
                p_item = PurchaseItem(
                    purchase_id=purchase.id,
                    product_id=item["product_id"],
                    qty=item["qty"],
                    rate=item["rate"]
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
            self.invoice_input.setEnabled(True)

            self.bill_items.clear()
            self.update_table()
            self.invoice_input.clear()
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
            items_table.setHorizontalHeaderLabels(["Product Code", "Product Name", "Qty", "Rate (₹)", "Total (₹)"])
            items_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            items_table.verticalHeader().setVisible(False)
            
            items = session.query(PurchaseItem).filter_by(purchase_id=purchase_id).all()
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
                subtotal = item.qty * item.rate
                items_table.setItem(i, 4, QTableWidgetItem(f"{subtotal:.2f}"))
                
            dlg_layout.addWidget(items_table)
            
            # Totals
            totals_frame = QFrame()
            totals_layout = QFormLayout(totals_frame)
            totals_layout.addRow("Total Amount:", QLabel(f"₹{purchase.total_amount:,.2f}"))
            totals_layout.addRow("Paid Amount:", QLabel(f"₹{purchase.paid_amount:,.2f}"))
            totals_layout.addRow("Balance Payable:", QLabel(f"₹{purchase.balance_payable:,.2f}"))
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
            for item in purchase.items:
                p_code = f"[{item.product.product_code}] " if item.product and item.product.product_code else ""
                pdf_items.append({
                    "name": f"{p_code}{item.product.name} ({item.product.brand} {item.product.model})",
                    "qty": item.qty,
                    "rate": item.rate,
                    "total": item.qty * item.rate
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
                "items": pdf_items,
                "total_amount": purchase.total_amount,
                "paid_amount": purchase.paid_amount,
                "balance": purchase.balance_payable
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
                    "rate": item.rate,
                    "selling_price": item.product.selling_price if item.product else 0.0
                })
                
            self.update_table()
            
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
        self.invoice_input.setEnabled(True)
        
        # Clear fields
        self.bill_items.clear()
        self.update_table()
        self.invoice_input.clear()
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
