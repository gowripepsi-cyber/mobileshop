import datetime
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, 
                             QDateEdit, QDoubleSpinBox, QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QMessageBox, QFrame, QFormLayout, QTabWidget, QDialog, QDialogButtonBox)
from PySide6.QtCore import Qt, QDate
from database import Session, Setting
from models import Payment, Customer, Supplier, BankAccount, CashTransaction, BankTransaction
from utils.pdf_generator import generate_payment_pdf

class PaymentsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Tabs for operations
        self.tabs = QTabWidget()
        
        # 1. Customer Collections Tab
        self.cust_tab = QWidget()
        self.setup_cust_tab()
        self.tabs.addTab(self.cust_tab, "Customer Collections")

        # 2. Supplier Payments Tab
        self.supp_tab = QWidget()
        self.setup_supp_tab()
        self.tabs.addTab(self.supp_tab, "Supplier Payments")

        # 3. Transaction History Tab
        self.history_tab = QWidget()
        self.setup_history_tab()
        self.tabs.addTab(self.history_tab, "Payment Ledgers History")

        layout.addWidget(self.tabs)

    def setup_cust_tab(self):
        layout = QHBoxLayout(self.cust_tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)

        # Form Card
        form_frame = QFrame()
        form_frame.setProperty("class", "CardFrame")
        form_frame.setFixedWidth(380)
        form_layout = QFormLayout(form_frame)
        form_layout.setContentsMargins(15, 15, 15, 15)
        form_layout.setSpacing(12)

        lbl = QLabel("Receive Customer Outstanding")
        lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff; margin-bottom: 10px;")
        form_layout.addRow(lbl)

        self.c_customer_combo = QComboBox()
        self.c_customer_combo.currentIndexChanged.connect(self.update_cust_outstanding_lbl)
        self.c_outstanding_lbl = QLabel("Current Outstanding: ₹0.00")
        self.c_outstanding_lbl.setStyleSheet("font-weight: bold; color: #f59e0b;")

        self.c_date = QDateEdit()
        self.c_date.setCalendarPopup(True)
        self.c_date.setDate(QDate.currentDate())

        self.c_amount = QDoubleSpinBox()
        self.c_amount.setRange(0.01, 9999999.0)
        self.c_amount.setDecimals(2)

        self.c_mode = QComboBox()
        self.c_mode.addItems(["Cash", "Bank"])
        self.c_mode.currentTextChanged.connect(self.toggle_c_bank)

        self.c_bank = QComboBox()
        self.c_bank.setEnabled(False)

        self.c_remarks = QLineEdit()
        self.c_remarks.setPlaceholderText("Remarks (optional)")

        form_layout.addRow("Select Customer *:", self.c_customer_combo)
        form_layout.addRow("", self.c_outstanding_lbl)
        form_layout.addRow("Payment Date:", self.c_date)
        form_layout.addRow("Amount Received (₹) *:", self.c_amount)
        form_layout.addRow("Payment Mode:", self.c_mode)
        form_layout.addRow("Select Bank Account:", self.c_bank)
        form_layout.addRow("Remarks:", self.c_remarks)

        self.c_save_btn = QPushButton("Save Collection")
        self.c_save_btn.setProperty("class", "btn-success")
        self.c_save_btn.clicked.connect(self.save_customer_collection)
        form_layout.addRow("", self.c_save_btn)

        layout.addWidget(form_frame)

        # Info Frame
        info_frame = QFrame()
        info_frame.setProperty("class", "CardFrame")
        info_layout = QVBoxLayout(info_frame)
        info_lbl = QLabel("Customer Ledger Helper")
        info_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff;")
        info_layout.addWidget(info_lbl)
        
        info_txt = QLabel(
            "Use this form when customers clear their outstanding balances outside standard Sales Invoices.\n\n"
            "Logging a transaction here will:\n"
            "  1. Reduce the Customer Outstanding balance immediately.\n"
            "  2. Add a positive transaction (+) in the Cash Book or Bank ledger.\n"
            "  3. Keep the cash-in-hand and bank balances accurately synchronized."
        )
        info_txt.setWordWrap(True)
        info_txt.setStyleSheet("color: #94a3b8; line-height: 20px;")
        info_layout.addWidget(info_txt)
        info_layout.addStretch()
        layout.addWidget(info_frame)

    def setup_supp_tab(self):
        layout = QHBoxLayout(self.supp_tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)

        # Form Card
        form_frame = QFrame()
        form_frame.setProperty("class", "CardFrame")
        form_frame.setFixedWidth(380)
        form_layout = QFormLayout(form_frame)
        form_layout.setContentsMargins(15, 15, 15, 15)
        form_layout.setSpacing(12)

        lbl = QLabel("Pay Supplier Outstanding")
        lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff; margin-bottom: 10px;")
        form_layout.addRow(lbl)

        self.s_supplier_combo = QComboBox()
        self.s_supplier_combo.currentIndexChanged.connect(self.update_supp_outstanding_lbl)
        self.s_outstanding_lbl = QLabel("Current Outstanding: ₹0.00")
        self.s_outstanding_lbl.setStyleSheet("font-weight: bold; color: #ef4444;")

        self.s_date = QDateEdit()
        self.s_date.setCalendarPopup(True)
        self.s_date.setDate(QDate.currentDate())

        self.s_amount = QDoubleSpinBox()
        self.s_amount.setRange(0.01, 9999999.0)
        self.s_amount.setDecimals(2)

        self.s_mode = QComboBox()
        self.s_mode.addItems(["Cash", "Bank"])
        self.s_mode.currentTextChanged.connect(self.toggle_s_bank)

        self.s_bank = QComboBox()
        self.s_bank.setEnabled(False)

        self.s_remarks = QLineEdit()
        self.s_remarks.setPlaceholderText("Remarks (optional)")

        form_layout.addRow("Select Supplier *:", self.s_supplier_combo)
        form_layout.addRow("", self.s_outstanding_lbl)
        form_layout.addRow("Payment Date:", self.s_date)
        form_layout.addRow("Amount Paid (₹) *:", self.s_amount)
        form_layout.addRow("Payment Mode:", self.s_mode)
        form_layout.addRow("Select Bank Account:", self.s_bank)
        form_layout.addRow("Remarks:", self.s_remarks)

        self.s_save_btn = QPushButton("Save Payment")
        self.s_save_btn.setProperty("class", "btn-danger")
        self.s_save_btn.clicked.connect(self.save_supplier_payment)
        form_layout.addRow("", self.s_save_btn)

        layout.addWidget(form_frame)

        # Info Frame
        info_frame = QFrame()
        info_frame.setProperty("class", "CardFrame")
        info_layout = QVBoxLayout(info_frame)
        info_lbl = QLabel("Supplier Ledger Helper")
        info_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff;")
        info_layout.addWidget(info_lbl)
        
        info_txt = QLabel(
            "Use this form when you clear your payable accounts with suppliers.\n\n"
            "Logging a transaction here will:\n"
            "  1. Reduce the Supplier Outstanding balance immediately.\n"
            "  2. Add a negative transaction (-) in the Cash Book or Bank ledger.\n"
            "  3. Keep the cash-in-hand and bank balances accurately synchronized."
        )
        info_txt.setWordWrap(True)
        info_txt.setStyleSheet("color: #94a3b8; line-height: 20px;")
        info_layout.addWidget(info_txt)
        info_layout.addStretch()
        layout.addWidget(info_frame)

    def setup_history_tab(self):
        layout = QVBoxLayout(self.history_tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(8)
        self.history_table.setHorizontalHeaderLabels([
            "ID", "Date", "Party Type", "Party Name", "Amount (₹)", "Payment Mode", "Remarks", "Actions"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        
        # Consistent sizing for columns
        self.history_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.history_table.setColumnWidth(4, 110)
        self.history_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self.history_table.setColumnWidth(5, 120)
        
        # Actions column for View, Print, Delete
        self.history_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Fixed)
        self.history_table.setColumnWidth(7, 260)
        
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.verticalHeader().setDefaultSectionSize(54)
        layout.addWidget(self.history_table)

    def toggle_c_bank(self, mode):
        self.c_bank.setEnabled(mode == "Bank")

    def toggle_s_bank(self, mode):
        self.s_bank.setEnabled(mode == "Bank")

    def refresh_data(self):
        session = Session()
        try:
            # 1. Load Customers
            self.c_customer_combo.blockSignals(True)
            self.c_customer_combo.clear()
            self.customers_cache = {}
            customers = session.query(Customer).all()
            for c in customers:
                self.customers_cache[c.id] = c
                self.c_customer_combo.addItem(c.name, c.id)
            self.c_customer_combo.blockSignals(False)
            self.update_cust_outstanding_lbl()

            # 2. Load Suppliers
            self.s_supplier_combo.blockSignals(True)
            self.s_supplier_combo.clear()
            self.suppliers_cache = {}
            suppliers = session.query(Supplier).all()
            for s in suppliers:
                self.suppliers_cache[s.id] = s
                self.s_supplier_combo.addItem(s.name, s.id)
            self.s_supplier_combo.blockSignals(False)
            self.update_supp_outstanding_lbl()

            # 3. Load Banks
            self.c_bank.clear()
            self.s_bank.clear()
            banks = session.query(BankAccount).all()
            for b in banks:
                self.c_bank.addItem(f"{b.bank_name} ({b.account_name})", b.id)
                self.s_bank.addItem(f"{b.bank_name} ({b.account_name})", b.id)

            # 4. Load history
            history = session.query(Payment).order_by(Payment.id.desc()).all()
            self.history_table.setRowCount(len(history))
            for i, p in enumerate(history):
                self.history_table.setItem(i, 0, QTableWidgetItem(str(p.id)))
                self.history_table.setItem(i, 1, QTableWidgetItem(p.date.strftime("%Y-%m-%d")))
                self.history_table.setItem(i, 2, QTableWidgetItem(p.party_type.capitalize()))
                
                # Fetch party name
                name = "-"
                if p.party_type == 'customer':
                    c_obj = session.query(Customer).get(p.party_id)
                    if c_obj: name = c_obj.name
                else:
                    s_obj = session.query(Supplier).get(p.party_id)
                    if s_obj: name = s_obj.name
                self.history_table.setItem(i, 3, QTableWidgetItem(name))

                val_item = QTableWidgetItem(f"₹{p.amount:,.2f}")
                if p.party_type == 'customer':
                    val_item.setForeground(Qt.green)
                else:
                    val_item.setForeground(Qt.red)
                self.history_table.setItem(i, 4, val_item)
                
                self.history_table.setItem(i, 5, QTableWidgetItem(p.payment_mode))
                self.history_table.setItem(i, 6, QTableWidgetItem(p.remarks or ""))
                
                # Action Buttons
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(6, 4, 6, 4)
                actions_layout.setSpacing(8)
                actions_layout.setAlignment(Qt.AlignCenter)
                
                view_btn = QPushButton("View")
                view_btn.setProperty("class", "btn-action-view")
                view_btn.clicked.connect(lambda checked, pid=p.id: self.view_payment_details(pid))
                actions_layout.addWidget(view_btn)
                
                print_btn = QPushButton("Print")
                print_btn.setProperty("class", "btn-action-print")
                print_btn.clicked.connect(lambda checked, pid=p.id: self.print_payment_receipt(pid))
                actions_layout.addWidget(print_btn)
                
                del_btn = QPushButton("Delete")
                del_btn.setProperty("class", "btn-action-delete")
                del_btn.clicked.connect(lambda checked, pid=p.id: self.delete_payment_record(pid))
                actions_layout.addWidget(del_btn)
                
                self.history_table.setCellWidget(i, 7, actions_widget)

        except Exception as e:
            print(f"Error loading payments view data: {e}")
        finally:
            session.close()

    def update_cust_outstanding_lbl(self):
        cust_id = self.c_customer_combo.currentData()
        if cust_id and hasattr(self, 'customers_cache') and cust_id in self.customers_cache:
            cust = self.customers_cache[cust_id]
            # Since the cache is local from loading, query to get latest
            session = Session()
            latest_cust = session.query(Customer).get(cust_id)
            if latest_cust:
                self.c_outstanding_lbl.setText(f"Current Outstanding: ₹{latest_cust.outstanding_balance:,.2f}")
            session.close()
        else:
            self.c_outstanding_lbl.setText("Current Outstanding: ₹0.00")

    def update_supp_outstanding_lbl(self):
        supp_id = self.s_supplier_combo.currentData()
        if supp_id and hasattr(self, 'suppliers_cache') and supp_id in self.suppliers_cache:
            session = Session()
            latest_supp = session.query(Supplier).get(supp_id)
            if latest_supp:
                self.s_outstanding_lbl.setText(f"Current Outstanding: ₹{latest_supp.outstanding_balance:,.2f}")
            session.close()
        else:
            self.s_outstanding_lbl.setText("Current Outstanding: ₹0.00")

    def save_customer_collection(self):
        cust_id = self.c_customer_combo.currentData()
        amount = self.c_amount.value()
        mode = self.c_mode.currentText()
        bank_id = self.c_bank.currentData() if mode == "Bank" else None
        remarks = self.c_remarks.text().strip() or None

        if not cust_id:
            QMessageBox.warning(self, "Validation Error", "Please select a Customer.")
            return

        date_q = self.c_date.date()
        tx_date = datetime.date(date_q.year(), date_q.month(), date_q.day())

        session = Session()
        try:
            # 1. Update Customer outstanding
            cust = session.query(Customer).get(cust_id)
            cust.outstanding_balance -= amount

            # 2. Add Payment record
            payment = Payment(
                date=tx_date, party_type='customer', party_id=cust_id,
                amount=amount, payment_mode=mode, bank_id=bank_id, remarks=remarks
            )
            session.add(payment)
            session.flush() # Generate payment.id

            # 3. Log Cash/Bank Ledger
            desc = f"Collection from customer {cust.name}. Details: {remarks or '-'}"
            if mode == 'Cash':
                tx = CashTransaction(
                    date=tx_date, transaction_type='in', amount=amount,
                    source_type='payment', source_id=payment.id, description=desc
                )
                session.add(tx)
            else:
                tx = BankTransaction(
                    date=tx_date, transaction_type='deposit', account_id=bank_id,
                    amount=amount, source_type='payment', source_id=payment.id, description=desc
                )
                session.add(tx)
                
                # Update bank balance
                bank = session.query(BankAccount).get(bank_id)
                bank.balance += amount

            session.commit()
            QMessageBox.information(self, "Success", f"Received ₹{amount:.2f} from customer {cust.name}.")
            
            # Reset values
            self.c_amount.setValue(0.0)
            self.c_remarks.clear()
            self.refresh_data()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save customer collection: {e}")
        finally:
            session.close()

    def save_supplier_payment(self):
        supp_id = self.s_supplier_combo.currentData()
        amount = self.s_amount.value()
        mode = self.s_mode.currentText()
        bank_id = self.s_bank.currentData() if mode == "Bank" else None
        remarks = self.s_remarks.text().strip() or None

        if not supp_id:
            QMessageBox.warning(self, "Validation Error", "Please select a Supplier.")
            return

        date_q = self.s_date.date()
        tx_date = datetime.date(date_q.year(), date_q.month(), date_q.day())

        session = Session()
        try:
            # Check bank balance if paying from bank
            if mode == "Bank":
                bank = session.query(BankAccount).get(bank_id)
                if bank.balance < amount:
                    QMessageBox.warning(self, "Insufficient Funds", f"Insufficient bank balance in {bank.bank_name}. Available: ₹{bank.balance:.2f}")
                    session.close()
                    return

            # 1. Update Supplier outstanding
            supp = session.query(Supplier).get(supp_id)
            supp.outstanding_balance -= amount

            # 2. Add Payment record
            payment = Payment(
                date=tx_date, party_type='supplier', party_id=supp_id,
                amount=amount, payment_mode=mode, bank_id=bank_id, remarks=remarks
            )
            session.add(payment)
            session.flush() # Generate payment.id

            # 3. Log Cash/Bank Ledger
            desc = f"Payment to supplier {supp.name}. Details: {remarks or '-'}"
            if mode == 'Cash':
                tx = CashTransaction(
                    date=tx_date, transaction_type='out', amount=amount,
                    source_type='payment', source_id=payment.id, description=desc
                )
                session.add(tx)
            else:
                tx = BankTransaction(
                    date=tx_date, transaction_type='withdrawal', account_id=bank_id,
                    amount=amount, source_type='payment', source_id=payment.id, description=desc
                )
                session.add(tx)
                
                # Update bank balance
                bank = session.query(BankAccount).get(bank_id)
                bank.balance -= amount

            session.commit()
            QMessageBox.information(self, "Success", f"Paid ₹{amount:.2f} to supplier {supp.name}.")
            
            # Reset values
            self.s_amount.setValue(0.0)
            self.s_remarks.clear()
            self.refresh_data()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save supplier payment: {e}")
        finally:
            session.close()

    def view_payment_details(self, payment_id):
        session = Session()
        try:
            payment = session.query(Payment).get(payment_id)
            if not payment:
                QMessageBox.warning(self, "Error", "Payment record not found.")
                return

            dialog = QDialog(self)
            title = "Payment Receipt Details" if payment.party_type == 'customer' else "Payment Voucher Details"
            dialog.setWindowTitle(f"{title} - #{payment.id}")
            dialog.setMinimumSize(450, 350)
            
            dlg_layout = QVBoxLayout(dialog)
            
            info_frame = QFrame()
            info_frame.setProperty("class", "CardFrame")
            info_layout = QFormLayout(info_frame)
            
            # Fetch party details
            party_name = "-"
            party_mobile = "-"
            if payment.party_type == 'customer':
                party = session.query(Customer).get(payment.party_id)
                if party:
                    party_name = party.name
                    party_mobile = party.mobile
            else:
                party = session.query(Supplier).get(payment.party_id)
                if party:
                    party_name = party.name
                    party_mobile = party.mobile
                    
            info_layout.addRow("Receipt / Voucher ID:", QLabel(f"#{payment.id}"))
            info_layout.addRow("Date:", QLabel(payment.date.strftime("%Y-%m-%d")))
            info_layout.addRow("Party Type:", QLabel(payment.party_type.capitalize()))
            info_layout.addRow("Party Name:", QLabel(party_name))
            info_layout.addRow("Party Contact:", QLabel(party_mobile))
            info_layout.addRow("Amount Paid (₹):", QLabel(f"₹{payment.amount:,.2f}"))
            info_layout.addRow("Payment Mode:", QLabel(payment.payment_mode))
            
            if payment.payment_mode == 'Bank' and payment.bank_id:
                bank = session.query(BankAccount).get(payment.bank_id)
                if bank:
                    info_layout.addRow("Bank Account:", QLabel(f"{bank.bank_name} ({bank.account_name})"))
                    
            info_layout.addRow("Remarks / Notes:", QLabel(payment.remarks or "-"))
            dlg_layout.addWidget(info_frame)
            
            buttons = QDialogButtonBox(QDialogButtonBox.Ok)
            buttons.accepted.connect(dialog.accept)
            dlg_layout.addWidget(buttons)
            
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load payment details: {e}")
        finally:
            session.close()

    def print_payment_receipt(self, payment_id):
        session = Session()
        try:
            payment = session.query(Payment).get(payment_id)
            if not payment:
                QMessageBox.warning(self, "Error", "Payment record not found.")
                return
                
            # Retrieve Settings details
            s_name = session.query(Setting).filter_by(key='shop_name').first().value
            s_contact = session.query(Setting).filter_by(key='shop_contact').first().value
            s_address = session.query(Setting).filter_by(key='shop_address').first().value
            s_gst = session.query(Setting).filter_by(key='shop_gst').first().value

            # Fetch party details
            party_name = "-"
            party_mobile = "-"
            if payment.party_type == 'customer':
                party = session.query(Customer).get(payment.party_id)
                if party:
                    party_name = party.name
                    party_mobile = party.mobile
            else:
                party = session.query(Supplier).get(payment.party_id)
                if party:
                    party_name = party.name
                    party_mobile = party.mobile

            # Prepare PDF data
            pdf_data = {
                "shop_name": s_name,
                "shop_contact": s_contact,
                "shop_address": s_address,
                "shop_gst": s_gst,
                "payment_id": payment.id,
                "date": payment.date.strftime("%Y-%m-%d"),
                "party_type": payment.party_type,
                "party_name": party_name,
                "party_mobile": party_mobile,
                "amount": payment.amount,
                "payment_mode": payment.payment_mode,
                "remarks": payment.remarks
            }

            os.makedirs("invoices", exist_ok=True)
            path = os.path.abspath(f"invoices/payment_{payment.id}.pdf")
            generate_payment_pdf(pdf_data, path)
            
            QMessageBox.information(self, "Success", f"Payment PDF generated at:\n{path}")
            
            # Auto-open
            try:
                os.startfile(path)
            except Exception as e:
                print(f"Could not auto-open PDF: {e}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to print/generate PDF: {e}")
        finally:
            session.close()

    def delete_payment_record(self, payment_id):
        confirm = QMessageBox.question(
            self, "Confirm Delete", 
            "Are you sure you want to delete this payment record?\nThe party outstanding balance and ledger transactions will be reverted.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return
            
        session = Session()
        try:
            payment = session.query(Payment).get(payment_id)
            if not payment:
                QMessageBox.warning(self, "Error", "Payment record not found.")
                session.close()
                return
                
            # 1. Revert party outstanding balance
            if payment.party_type == 'customer':
                cust = session.query(Customer).get(payment.party_id)
                if cust:
                    cust.outstanding_balance += payment.amount  # add back outstanding since payment is deleted
            else:
                supp = session.query(Supplier).get(payment.party_id)
                if supp:
                    supp.outstanding_balance += payment.amount  # add back outstanding since payment is deleted
                    
            # 2. Revert/delete ledger entries (CashTransaction/BankTransaction)
            # Find by source_id first
            cash_txs = session.query(CashTransaction).filter_by(source_type='payment', source_id=payment.id).all()
            if not cash_txs and payment.payment_mode == 'Cash':
                # Fallback for legacy database entries without source_id
                tx_type = 'in' if payment.party_type == 'customer' else 'out'
                cash_txs = session.query(CashTransaction).filter(
                    CashTransaction.source_type == 'payment',
                    CashTransaction.transaction_type == tx_type,
                    CashTransaction.amount == payment.amount,
                    CashTransaction.date == payment.date
                ).all()
            for tx in cash_txs:
                session.delete(tx)
                
            bank_txs = session.query(BankTransaction).filter_by(source_type='payment', source_id=payment.id).all()
            if not bank_txs and payment.payment_mode == 'Bank':
                # Fallback for legacy database entries without source_id
                tx_type = 'deposit' if payment.party_type == 'customer' else 'withdrawal'
                bank_txs = session.query(BankTransaction).filter(
                    BankTransaction.source_type == 'payment',
                    BankTransaction.transaction_type == tx_type,
                    BankTransaction.amount == payment.amount,
                    BankTransaction.date == payment.date
                ).all()
            for tx in bank_txs:
                # Revert bank account balance
                bank = session.query(BankAccount).get(tx.account_id)
                if bank:
                    if tx.transaction_type == 'deposit':
                        bank.balance -= tx.amount
                    else:
                        bank.balance += tx.amount
                session.delete(tx)
                
            # 3. Delete Payment
            session.delete(payment)
            
            session.commit()
            QMessageBox.information(self, "Success", "Payment record deleted and related accounts reverted successfully.")
            self.refresh_data()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to delete payment record: {e}")
        finally:
            session.close()
