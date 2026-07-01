import datetime
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QComboBox, 
                             QDateEdit, QSpinBox, QDoubleSpinBox, QPushButton, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QMessageBox, QFrame, QFormLayout, 
                             QDialog, QDialogButtonBox)
from PySide6.QtCore import Qt, QDate
from database import Session, Setting
from models import Customer, Product, BankAccount, SalesMaster, SalesItem, CashTransaction, BankTransaction, Category, SalesReturnMaster, SalesReturnItem
from utils.pdf_generator import generate_sales_return_pdf
from utils.ui_helpers import enable_quick_add_auto_select

class SalesReturnEntryWidget(QWidget):
    def __init__(self, parent=None, history_widget=None):
        super().__init__(parent)
        self.history_widget = history_widget
        self.return_items = []  # list of dicts: {"product_id": int, "name": str, "qty": int, "rate": float}
        self.products_cache = {}
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(20)

        # Left Column: Return Parameters
        left_panel = QFrame()
        left_panel.setProperty("class", "CardFrame")
        left_panel.setFixedWidth(360)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(15, 15, 15, 15)
        left_layout.setSpacing(15)

        title_lbl = QLabel("Sales Return Details")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff;")
        left_layout.addWidget(title_lbl)

        form_layout = QFormLayout()
        
        self.return_no_input = QLineEdit()
        self.return_no_input.setPlaceholderText("e.g. SR-1001")
        
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())
        
        self.customer_combo = QComboBox()
        self.customer_combo.setEditable(True)
        self.customer_combo.setInsertPolicy(QComboBox.NoInsert)
        enable_quick_add_auto_select(self.customer_combo)
        self.customer_combo.currentTextChanged.connect(self.check_customer_match)
        if self.customer_combo.lineEdit():
            self.customer_combo.lineEdit().setPlaceholderText("Select or type customer name")
            self.customer_combo.lineEdit().textChanged.connect(self.check_customer_match)
        self.customer_combo.currentIndexChanged.connect(self.load_customer_invoices)

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
        
        self.invoice_combo = QComboBox()
        
        self.pay_mode_combo = QComboBox()
        self.pay_mode_combo.addItems(["Cash", "Bank"])
        self.pay_mode_combo.currentTextChanged.connect(self.toggle_bank_account)
        
        self.bank_combo = QComboBox()
        self.bank_combo.setEnabled(False)
        
        self.refund_input = QDoubleSpinBox()
        self.refund_input.setRange(0, 9999999)
        self.refund_input.setValue(0.0)
        self.refund_input.setDecimals(2)
        self.refund_input.valueChanged.connect(self.update_summary)

        self.bal_deducted_input = QDoubleSpinBox()
        self.bal_deducted_input.setRange(0, 9999999)
        self.bal_deducted_input.setValue(0.0)
        self.bal_deducted_input.setDecimals(2)
        self.bal_deducted_input.setEnabled(False) # Read-only, auto-calculated

        form_layout.addRow("Return Number *:", self.return_no_input)
        form_layout.addRow("Return Date:", self.date_input)
        form_layout.addRow("Customer *:", cust_layout)
        form_layout.addRow("Ref Sales Invoice:", self.invoice_combo)
        form_layout.addRow("Refund Mode:", self.pay_mode_combo)
        form_layout.addRow("Select Bank A/c:", self.bank_combo)
        form_layout.addRow("Refund Paid (₹):", self.refund_input)
        form_layout.addRow("Outstanding Adj (₹):", self.bal_deducted_input)

        left_layout.addLayout(form_layout)
        left_layout.addStretch()

        self.save_btn = QPushButton("Save & Print Return Note")
        self.save_btn.setProperty("class", "btn-success")
        self.save_btn.setFixedHeight(40)
        self.save_btn.clicked.connect(self.save_sales_return)
        left_layout.addWidget(self.save_btn)

        main_layout.addWidget(left_panel)

        # Right Column: Product Line Items & Table
        right_panel = QFrame()
        right_panel.setProperty("class", "CardFrame")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(15, 15, 15, 15)
        right_layout.setSpacing(15)

        entry_title = QLabel("Add Returned Products")
        entry_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        right_layout.addWidget(entry_title)

        grid_layout = QGridLayout()
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setHorizontalSpacing(15)
        grid_layout.setVerticalSpacing(10)
        
        # Column Stretches:
        # Col 0, 2, 4 are labels -> stretch 0
        # Col 1 is Code & Qty -> stretch 0 (width limited by product_code_input fixed width)
        # Col 3 is Category & Rate -> stretch 2
        # Col 5 is Product & Button -> stretch 4
        grid_layout.setColumnStretch(0, 0)
        grid_layout.setColumnStretch(1, 0)
        grid_layout.setColumnStretch(2, 0)
        grid_layout.setColumnStretch(3, 2)
        grid_layout.setColumnStretch(4, 0)
        grid_layout.setColumnStretch(5, 4)
        
        self.product_code_input = QLineEdit()
        self.product_code_input.setPlaceholderText("Code")
        self.product_code_input.setFixedWidth(120)
        self.product_code_input.returnPressed.connect(self.handle_product_code_entry)
        self.product_code_input._skip_enter_nav = True
        grid_layout.addWidget(QLabel("Code:"), 0, 0)
        grid_layout.addWidget(self.product_code_input, 0, 1)
        
        self.category_combo = QComboBox()
        self.category_combo.currentIndexChanged.connect(self.filter_products_by_category)
        self.category_combo.hide()
        
        self.product_combo = QComboBox()
        self.product_combo.setPlaceholderText("Select Product")
        self.product_combo.currentIndexChanged.connect(self.update_rate_on_product_change)
        grid_layout.addWidget(QLabel("Product:"), 0, 2)
        grid_layout.addWidget(self.product_combo, 0, 3, 1, 3)

        self.qty_input = QSpinBox()
        self.qty_input.setRange(1, 1000)
        self.qty_input.setValue(1)
        grid_layout.addWidget(QLabel("Qty:"), 1, 0)
        grid_layout.addWidget(self.qty_input, 1, 1)

        self.rate_input = QDoubleSpinBox()
        self.rate_input.setRange(0.0, 9999999.0)
        self.rate_input.setValue(0.0)
        self.rate_input.setDecimals(2)
        grid_layout.addWidget(QLabel("Rate (₹):"), 1, 2)
        grid_layout.addWidget(self.rate_input, 1, 3)

        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.addStretch()
        self.add_item_btn = QPushButton("Add Item")
        self.add_item_btn.clicked.connect(self.add_item_to_list)
        btn_layout.addWidget(self.add_item_btn)

        grid_layout.addLayout(btn_layout, 1, 5)

        right_layout.addLayout(grid_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Product Code", "Product Name", "Qty", "Rate (₹)", "Total (₹)", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self.table.setColumnWidth(5, 110)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(54)
        right_layout.addWidget(self.table)

        # Totals Summary Bar
        summary_bar = QHBoxLayout()
        self.total_lbl = QLabel("Total Return Value: ₹0.00")
        self.total_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #dc2626;")
        self.adj_lbl = QLabel("Outstanding Adj: ₹0.00")
        self.adj_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #f59e0b;")
        
        summary_bar.addWidget(self.total_lbl)
        summary_bar.addWidget(self.adj_lbl)
        right_layout.addLayout(summary_bar)

        main_layout.addWidget(right_panel, 2)

    def toggle_bank_account(self, mode):
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
                    self.customer_combo.blockSignals(True)
                    self.customer_combo.setCurrentIndex(i)
                    self.customer_combo.blockSignals(False)
                    self.load_customer_invoices()
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

            # Auto-suggest Return Number
            last_sr = session.query(SalesReturnMaster).order_by(SalesReturnMaster.id.desc()).first()
            if last_sr:
                self.return_no_input.setText(f"SR-{last_sr.id + 1001}")
            else:
                self.return_no_input.setText("SR-1001")

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
                return

        self.return_items.append({
            "product_id": prod_id,
            "product_code": p_cache.product_code if p_cache.product_code else "-",
            "name": p_cache.name,
            "qty": qty,
            "rate": rate
        })
        
        self.update_table()

    def delete_item(self, row_idx):
        self.return_items.pop(row_idx)
        self.update_table()

    def update_table(self):
        self.table.setRowCount(len(self.return_items))
        for i, item in enumerate(self.return_items):
            self.table.setItem(i, 0, QTableWidgetItem(item.get("product_code", "-")))
            self.table.setItem(i, 1, QTableWidgetItem(item["name"]))
            self.table.setItem(i, 2, QTableWidgetItem(str(item["qty"])))
            self.table.setItem(i, 3, QTableWidgetItem(f"{item['rate']:.2f}"))
            
            subtotal = item["qty"] * item["rate"]
            self.table.setItem(i, 4, QTableWidgetItem(f"{subtotal:.2f}"))

            btn_container = QWidget()
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(4, 4, 4, 4)
            btn_layout.setSpacing(0)
            btn_layout.setAlignment(Qt.AlignCenter)

            del_btn = QPushButton("Delete")
            del_btn.setProperty("class", "btn-action-delete")
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

        self.total_lbl.setText(f"Total Return Value: ₹{total:,.2f}")
        self.adj_lbl.setText(f"Outstanding Adj: ₹{adj:,.2f}")

    def save_sales_return(self):
        return_no = self.return_no_input.text().strip()
        cust_id = self.customer_combo.currentData()
        
        if not return_no:
            QMessageBox.warning(self, "Validation Error", "Please enter Return Number.")
            return
        if not cust_id:
            QMessageBox.warning(self, "Validation Error", "Please select a Customer.")
            return
        if not self.return_items:
            QMessageBox.warning(self, "Validation Error", "Please add at least one item to the return.")
            return

        total = sum(item["qty"] * item["rate"] for item in self.return_items)
        refund = self.refund_input.value()
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
                QMessageBox.warning(self, "Duplicate Return", f"Return number {return_no} already exists.")
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
                    p_code = f"[{prod.product_code}] " if prod.product_code else ""
                    p_name = f"{p_code}{prod.name} ({prod.brand} {prod.model})"
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
                self.table.setItem(i, 3, QTableWidgetItem(f"₹{r.total_amount:,.2f}"))
                self.table.setItem(i, 4, QTableWidgetItem(f"₹{r.refund_amount:,.2f}"))
                self.table.setItem(i, 5, QTableWidgetItem(f"₹{r.balance_deducted:,.2f}"))

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
            items_table.setHorizontalHeaderLabels(["Product Code", "Product Name", "Qty", "Rate (₹)", "Total (₹)"])
            items_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            items_table.verticalHeader().setVisible(False)
            
            items = session.query(SalesReturnItem).filter_by(sales_return_id=return_id).all()
            items_table.setRowCount(len(items))
            for i, item in enumerate(items):
                p_code = item.product.product_code if item.product and item.product.product_code else "-"
                disp_name = f"{item.product.name} ({item.product.brand} {item.product.model})" if item.product else f"Product ID: {item.product_id}"
                items_table.setItem(i, 0, QTableWidgetItem(p_code))
                items_table.setItem(i, 1, QTableWidgetItem(disp_name))
                items_table.setItem(i, 2, QTableWidgetItem(str(item.qty)))
                items_table.setItem(i, 3, QTableWidgetItem(f"{item.rate:.2f}"))
                items_table.setItem(i, 4, QTableWidgetItem(f"{(item.qty * item.rate):.2f}"))
            dlg_layout.addWidget(items_table)

            totals_frame = QFrame()
            totals_layout = QFormLayout(totals_frame)
            totals_layout.addRow("Total Return Amount:", QLabel(f"₹{ret.total_amount:,.2f}"))
            totals_layout.addRow("Refund Paid:", QLabel(f"₹{ret.refund_amount:,.2f}"))
            totals_layout.addRow("Outstanding Adjusted:", QLabel(f"₹{ret.balance_deducted:,.2f}"))
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
                    p_code = f"[{item.product.product_code}] " if item.product.product_code else ""
                    p_name = f"{p_code}{item.product.name} ({item.product.brand} {item.product.model})"
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
