import datetime
import os
import subprocess
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, 
                             QDateEdit, QSpinBox, QDoubleSpinBox, QPushButton, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QMessageBox, QFrame, QFormLayout, QFileDialog)
from PySide6.QtCore import Qt, QDate
from database import Session, Setting
from models import Customer, Product, BankAccount, SalesMaster, SalesItem, CashTransaction, BankTransaction, Category
from utils.pdf_generator import generate_sales_pdf

class SalesView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.invoice_items = []  # list of dicts: {"product_id": int, "name": str, "qty": int, "rate": float, "discount": float}
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
        form_layout.addRow("Customer *:", self.customer_combo)
        form_layout.addRow("Payment Mode:", self.pay_mode_combo)
        form_layout.addRow("Select Bank A/c:", self.bank_combo)
        form_layout.addRow("Paid Amount (₹):", self.paid_input)

        left_layout.addLayout(form_layout)
        left_layout.addStretch()

        # Save Button
        self.save_btn = QPushButton("Save & Print Invoice")
        self.save_btn.setProperty("class", "btn-success")
        self.save_btn.setFixedHeight(40)
        self.save_btn.clicked.connect(self.save_sales_invoice)
        left_layout.addWidget(self.save_btn)

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

        self.discount_input = QDoubleSpinBox()
        self.discount_input.setRange(0.0, 999999.0)
        self.discount_input.setValue(0.0)
        self.discount_input.setDecimals(2)
        entry_bar.addWidget(QLabel("Disc (₹):"), 0)
        entry_bar.addWidget(self.discount_input, 1.5)

        self.add_item_btn = QPushButton("Add Item")
        self.add_item_btn.clicked.connect(self.add_item_to_list)
        entry_bar.addWidget(self.add_item_btn, 1)

        right_layout.addLayout(entry_bar)

        # Items Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Product Name", "Qty", "Rate (₹)", "Discount (₹)", "Total (₹)", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
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

    def refresh_data(self):
        session = Session()
        try:
            # Load Customers
            self.customer_combo.clear()
            customers = session.query(Customer).all()
            for c in customers:
                self.customer_combo.addItem(c.name, c.id)

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
            last_s = session.query(SalesMaster).order_by(SalesMaster.id.desc()).first()
            if last_s:
                self.invoice_input.setText(f"INV-{last_s.id + 1001}")
            else:
                self.invoice_input.setText("INV-1001")

        except Exception as e:
            print(f"Error loading sales options: {e}")
        finally:
            session.close()

    def update_rate_on_product_change(self):
        prod_id = self.product_combo.currentData()
        if prod_id and hasattr(self, 'products_cache') and prod_id in self.products_cache:
            prod = self.products_cache[prod_id]
            self.rate_input.setValue(prod.selling_price)
        else:
            self.rate_input.setValue(0.0)

    def toggle_bank_account(self, mode):
        self.bank_combo.setEnabled(mode == "Bank")

    def add_item_to_list(self):
        prod_idx = self.product_combo.currentIndex()
        if prod_idx < 0:
            return

        prod_id = self.product_combo.currentData()
        prod_text = self.product_combo.currentText()
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

        if (current_added_qty + qty) > p_cache.stock_qty:
            QMessageBox.warning(
                self, 
                "Stock Alert", 
                f"Insufficient stock for {p_cache.name}!\nAvailable: {p_cache.stock_qty}\nRequested: {current_added_qty + qty}"
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
            self.table.setItem(i, 0, QTableWidgetItem(item["name"]))
            self.table.setItem(i, 1, QTableWidgetItem(str(item["qty"])))
            self.table.setItem(i, 2, QTableWidgetItem(f"{item['rate']:.2f}"))
            self.table.setItem(i, 3, QTableWidgetItem(f"{item['discount']:.2f}"))
            
            subtotal = (item["qty"] * item["rate"]) - item["discount"]
            if subtotal < 0:
                subtotal = 0.0
            self.table.setItem(i, 4, QTableWidgetItem(f"{subtotal:.2f}"))

            # Delete button
            del_btn = QPushButton("Delete")
            del_btn.setProperty("class", "btn-danger")
            del_btn.clicked.connect(lambda checked, idx=i: self.delete_item(idx))
            self.table.setCellWidget(i, 5, del_btn)

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
        if not cust_id:
            QMessageBox.warning(self, "Validation Error", "Please select a Customer.")
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
            session.commit() # Get sale ID

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
                
                pdf_items.append({
                    "name": f"{prod.name} ({prod.brand} {prod.model})",
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

            # Reset page
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
