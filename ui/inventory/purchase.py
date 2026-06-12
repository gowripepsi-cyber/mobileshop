import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, 
                             QDateEdit, QSpinBox, QDoubleSpinBox, QPushButton, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QMessageBox, QFrame, QFormLayout)
from PySide6.QtCore import Qt, QDate
from database import Session
from models import Supplier, Product, BankAccount, PurchaseMaster, PurchaseItem, CashTransaction, BankTransaction, Category

class PurchaseView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bill_items = []  # list of dicts: {"product_id": int, "name": str, "qty": int, "rate": float}
        self.products_cache = {}
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
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
        form_layout.addRow("Supplier *:", self.supplier_combo)
        form_layout.addRow("Payment Mode:", self.pay_mode_combo)
        form_layout.addRow("Select Bank A/c:", self.bank_combo)
        form_layout.addRow("Paid Amount (₹):", self.paid_input)

        left_layout.addLayout(form_layout)
        left_layout.addStretch()

        # Save Button
        self.save_btn = QPushButton("Save Purchase Bill")
        self.save_btn.setProperty("class", "btn-success")
        self.save_btn.setFixedHeight(40)
        self.save_btn.clicked.connect(self.save_purchase)
        left_layout.addWidget(self.save_btn)

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

        entry_bar = QHBoxLayout()
        
        self.category_combo = QComboBox()
        self.category_combo.currentIndexChanged.connect(self.filter_products_by_category)
        entry_bar.addWidget(self.category_combo, 2)
        
        self.product_combo = QComboBox()
        self.product_combo.setPlaceholderText("Select Product")
        self.product_combo.currentIndexChanged.connect(self.update_rate_on_product_change)
        entry_bar.addWidget(self.product_combo, 3)

        self.qty_input = QSpinBox()
        self.qty_input.setRange(1, 1000)
        self.qty_input.setValue(1)
        entry_bar.addWidget(QLabel("Qty:"), 0)
        entry_bar.addWidget(self.qty_input, 1)

        self.rate_input = QDoubleSpinBox()
        self.rate_input.setRange(0.0, 9999999.0)
        self.rate_input.setValue(0.0)
        self.rate_input.setDecimals(2)
        entry_bar.addWidget(QLabel("Rate (₹):"), 0)
        entry_bar.addWidget(self.rate_input, 2)

        self.add_item_btn = QPushButton("Add Item")
        self.add_item_btn.clicked.connect(self.add_item_to_list)
        entry_bar.addWidget(self.add_item_btn, 1)

        right_layout.addLayout(entry_bar)

        # Items Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Product Name", "Qty", "Rate (₹)", "Total (₹)", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
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
            # Load Suppliers
            self.supplier_combo.clear()
            suppliers = session.query(Supplier).all()
            for s in suppliers:
                self.supplier_combo.addItem(s.name, s.id)

            # Load Categories
            self.category_combo.clear()
            self.category_combo.addItem("-- All Categories --")
            categories = session.query(Category).all()
            for c in categories:
                self.category_combo.addItem(c.name)

            # Load Products
            self.products_cache = {}
            products = session.query(Product).all()
            for p in products:
                self.products_cache[p.id] = p
                
            self.filter_products_by_category()

            # Load Bank Accounts
            self.bank_combo.clear()
            banks = session.query(BankAccount).all()
            for b in banks:
                self.bank_combo.addItem(f"{b.bank_name} ({b.account_name})", b.id)

            # Suggest an invoice number
            last_p = session.query(PurchaseMaster).order_by(PurchaseMaster.id.desc()).first()
            if last_p:
                self.invoice_input.setText(f"PUR-{last_p.id + 1001}")
            else:
                self.invoice_input.setText("PUR-1001")

        except Exception as e:
            print(f"Error loading purchase options: {e}")
        finally:
            session.close()

    def toggle_bank_account(self, mode):
        self.bank_combo.setEnabled(mode == "Bank")

    def update_rate_on_product_change(self):
        prod_id = self.product_combo.currentData()
        if prod_id and prod_id in self.products_cache:
            prod = self.products_cache[prod_id]
            self.rate_input.setValue(prod.purchase_price)
        else:
            self.rate_input.setValue(0.0)

    def add_item_to_list(self):
        prod_idx = self.product_combo.currentIndex()
        if prod_idx < 0:
            return

        prod_id = self.product_combo.currentData()
        qty = self.qty_input.value()
        rate = self.rate_input.value()

        p_cache = self.products_cache.get(prod_id)
        prod_text = p_cache.name if p_cache else self.product_combo.currentText()

        # Check if already added
        for item in self.bill_items:
            if item["product_id"] == prod_id:
                item["qty"] += qty
                item["rate"] = rate  # update with latest rate
                self.update_table()
                return

        self.bill_items.append({
            "product_id": prod_id,
            "name": prod_text,
            "qty": qty,
            "rate": rate
        })
        
        self.update_table()

    def delete_item(self, row_idx):
        self.bill_items.pop(row_idx)
        self.update_table()

    def update_table(self):
        self.table.setRowCount(len(self.bill_items))
        for i, item in enumerate(self.bill_items):
            self.table.setItem(i, 0, QTableWidgetItem(item["name"]))
            self.table.setItem(i, 1, QTableWidgetItem(str(item["qty"])))
            self.table.setItem(i, 2, QTableWidgetItem(f"{item['rate']:.2f}"))
            
            subtotal = item["qty"] * item["rate"]
            self.table.setItem(i, 3, QTableWidgetItem(f"{subtotal:.2f}"))

            # Delete button
            del_btn = QPushButton("Delete")
            del_btn.setProperty("class", "btn-danger")
            del_btn.clicked.connect(lambda checked, idx=i: self.delete_item(idx))
            self.table.setCellWidget(i, 4, del_btn)

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
        if not supp_id:
            QMessageBox.warning(self, "Validation Error", "Please select a Supplier.")
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
            # Check invoice number uniqueness
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
            session.commit() # Get purchase ID

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
                prod.stock_qty += item["qty"]
                # Optionally update purchase price to the latest price
                prod.purchase_price = item["rate"]

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
            self.bill_items.clear()
            self.update_table()
            self.invoice_input.clear()
            self.paid_input.setValue(0.0)
            self.qty_input.setValue(1)
            self.rate_input.setValue(0.0)
            self.refresh_data()

        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save purchase bill: {e}")
        finally:
            session.close()
