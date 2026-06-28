import datetime
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, 
                             QDateEdit, QDoubleSpinBox, QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QMessageBox, QFrame, QFormLayout, QTabWidget, QDialog, QDialogButtonBox)
from PySide6.QtCore import Qt, QDate
from database import Session, Setting
from sqlalchemy import func
from models import Payment, Customer, Supplier, BankAccount, CashTransaction, BankTransaction, FundTransfer, DirectTransaction
from utils.pdf_generator import generate_payment_pdf
from utils.ui_helpers import enable_quick_add_auto_select

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

        # 4. Fund Transfer Tab
        self.transfer_tab = QWidget()
        self.setup_transfer_tab()
        self.tabs.addTab(self.transfer_tab, "Fund Transfer")

        # 5. Direct Transactions Tab
        self.direct_tab = QWidget()
        self.setup_direct_tab()
        self.tabs.addTab(self.direct_tab, "Direct Transactions")

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
        self.c_customer_combo.setEditable(True)
        self.c_customer_combo.setInsertPolicy(QComboBox.NoInsert)
        enable_quick_add_auto_select(self.c_customer_combo)
        self.c_customer_combo.currentTextChanged.connect(self.check_c_customer_match)
        if self.c_customer_combo.lineEdit():
            self.c_customer_combo.lineEdit().setPlaceholderText("Select or type customer name")
            self.c_customer_combo.lineEdit().textChanged.connect(self.check_c_customer_match)
        self.c_customer_combo.currentIndexChanged.connect(self.update_cust_outstanding_lbl)

        c_cust_layout = QHBoxLayout()
        c_cust_layout.setContentsMargins(0, 0, 0, 0)
        c_cust_layout.setSpacing(6)
        c_cust_layout.addWidget(self.c_customer_combo, 1)

        self.add_c_cust_btn = QPushButton("+")
        self.add_c_cust_btn.setToolTip("Add new customer")
        self.add_c_cust_btn.setProperty("class", "btn-quick-add")
        self.add_c_cust_btn.setFixedWidth(40)
        self.add_c_cust_btn.setStyleSheet("padding: 0px; font-size: 18px; font-weight: bold; text-align: center;")
        self.add_c_cust_btn.setCursor(Qt.PointingHandCursor)
        self.add_c_cust_btn.clicked.connect(self.handle_add_c_customer_click)
        self.add_c_cust_btn.hide()
        c_cust_layout.addWidget(self.add_c_cust_btn)

        self.c_outstanding_lbl = QLabel("Current Outstanding: ₹0.00")
        self.c_outstanding_lbl.setStyleSheet("font-weight: bold; color: #f59e0b;")

        self.c_sales_combo = QComboBox()
        self.c_sales_combo.currentIndexChanged.connect(self.handle_cust_sales_selection)

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

        form_layout.addRow("Select Customer *:", c_cust_layout)
        form_layout.addRow("", self.c_outstanding_lbl)
        form_layout.addRow("Collect Against Invoice:", self.c_sales_combo)
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
        self.s_supplier_combo.setEditable(True)
        self.s_supplier_combo.setInsertPolicy(QComboBox.NoInsert)
        enable_quick_add_auto_select(self.s_supplier_combo)
        self.s_supplier_combo.currentTextChanged.connect(self.check_s_supplier_match)
        if self.s_supplier_combo.lineEdit():
            self.s_supplier_combo.lineEdit().setPlaceholderText("Select or type supplier name")
            self.s_supplier_combo.lineEdit().textChanged.connect(self.check_s_supplier_match)
        self.s_supplier_combo.currentIndexChanged.connect(self.update_supp_outstanding_lbl)

        s_supp_layout = QHBoxLayout()
        s_supp_layout.setContentsMargins(0, 0, 0, 0)
        s_supp_layout.setSpacing(6)
        s_supp_layout.addWidget(self.s_supplier_combo, 1)

        self.add_s_supp_btn = QPushButton("+")
        self.add_s_supp_btn.setToolTip("Add new supplier")
        self.add_s_supp_btn.setProperty("class", "btn-quick-add")
        self.add_s_supp_btn.setFixedWidth(40)
        self.add_s_supp_btn.setStyleSheet("padding: 0px; font-size: 18px; font-weight: bold; text-align: center;")
        self.add_s_supp_btn.setCursor(Qt.PointingHandCursor)
        self.add_s_supp_btn.clicked.connect(self.handle_add_s_supplier_click)
        self.add_s_supp_btn.hide()
        s_supp_layout.addWidget(self.add_s_supp_btn)

        self.s_outstanding_lbl = QLabel("Current Outstanding: ₹0.00")
        self.s_outstanding_lbl.setStyleSheet("font-weight: bold; color: #ef4444;")

        self.s_purchase_combo = QComboBox()
        self.s_purchase_combo.currentIndexChanged.connect(self.handle_supp_purchase_selection)

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

        form_layout.addRow("Select Supplier *:", s_supp_layout)
        form_layout.addRow("", self.s_outstanding_lbl)
        form_layout.addRow("Pay Against Bill:", self.s_purchase_combo)
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
        self.history_table.setColumnWidth(7, 180)
        
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.verticalHeader().setDefaultSectionSize(54)
        layout.addWidget(self.history_table)

        # Lazy loading state
        self.history_offset = 0
        self.has_more_history = True
        self.history_table.verticalScrollBar().valueChanged.connect(self.handle_history_scroll)

    def toggle_c_bank(self, mode):
        self.c_bank.setEnabled(mode == "Bank")

    def toggle_s_bank(self, mode):
        self.s_bank.setEnabled(mode == "Bank")

    def setup_transfer_tab(self):
        layout = QHBoxLayout(self.transfer_tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)

        # Form Card
        form_frame = QFrame()
        form_frame.setProperty("class", "CardFrame")
        form_frame.setFixedWidth(380)
        form_layout = QFormLayout(form_frame)
        form_layout.setContentsMargins(15, 15, 15, 15)
        form_layout.setSpacing(12)

        lbl = QLabel("New Fund Transfer")
        lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff; margin-bottom: 10px;")
        form_layout.addRow(lbl)

        self.t_date = QDateEdit()
        self.t_date.setCalendarPopup(True)
        self.t_date.setDate(QDate.currentDate())

        self.t_from = QComboBox()
        self.t_to = QComboBox()
        
        self.t_from.currentIndexChanged.connect(self.handle_transfer_source_change)

        self.t_amount = QDoubleSpinBox()
        self.t_amount.setRange(0.01, 9999999.0)
        self.t_amount.setDecimals(2)

        self.t_remarks = QLineEdit()
        self.t_remarks.setPlaceholderText("Transfer remarks (optional)")

        form_layout.addRow("Transfer Date:", self.t_date)
        form_layout.addRow("Transfer From *:", self.t_from)
        form_layout.addRow("Transfer To *:", self.t_to)
        form_layout.addRow("Amount (₹) *:", self.t_amount)
        form_layout.addRow("Remarks:", self.t_remarks)

        self.t_save_btn = QPushButton("Execute Transfer")
        self.t_save_btn.setProperty("class", "btn-success")
        self.t_save_btn.clicked.connect(self.save_fund_transfer)
        form_layout.addRow("", self.t_save_btn)

        layout.addWidget(form_frame)

        # Right Card: Transfer History Table
        history_frame = QFrame()
        history_frame.setProperty("class", "CardFrame")
        history_layout = QVBoxLayout(history_frame)
        history_layout.setContentsMargins(15, 15, 15, 15)
        
        history_title = QLabel("Transfer Log")
        history_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff; margin-bottom: 10px;")
        history_layout.addWidget(history_title)

        self.transfer_table = QTableWidget()
        self.transfer_table.setColumnCount(6)
        self.transfer_table.setHorizontalHeaderLabels([
            "ID", "Date", "From", "To", "Amount (₹)", "Actions"
        ])
        self.transfer_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.transfer_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.transfer_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self.transfer_table.setColumnWidth(5, 120)
        self.transfer_table.verticalHeader().setVisible(False)
        self.transfer_table.verticalHeader().setDefaultSectionSize(48)
        history_layout.addWidget(self.transfer_table)

        # Lazy loading state
        self.transfer_offset = 0
        self.has_more_transfers = True
        self.transfer_table.verticalScrollBar().valueChanged.connect(self.handle_transfer_scroll)

        layout.addWidget(history_frame)

    def handle_transfer_source_change(self):
        self.populate_transfer_destinations()

    def populate_transfer_destinations(self):
        self.t_to.blockSignals(True)
        self.t_to.clear()
        
        source_data = self.t_from.currentData()
        if not source_data:
            self.t_to.blockSignals(False)
            return

        if source_data[0] != 'cash':
            self.t_to.addItem("Cash Ledger", ('cash', None))
            
        if hasattr(self, 'banks_list'):
            for b_name, b_id in self.banks_list:
                if source_data[0] == 'bank' and source_data[1] == b_id:
                    continue
                self.t_to.addItem(b_name, ('bank', b_id))
            
        self.t_to.blockSignals(False)

    def save_fund_transfer(self):
        from_data = self.t_from.currentData()
        to_data = self.t_to.currentData()
        amount = self.t_amount.value()
        remarks = self.t_remarks.text().strip() or None
        date_q = self.t_date.date()
        tx_date = datetime.date(date_q.year(), date_q.month(), date_q.day())

        if not from_data or not to_data:
            QMessageBox.warning(self, "Validation Error", "Please select valid Source and Destination accounts.")
            return

        if amount <= 0:
            QMessageBox.warning(self, "Validation Error", "Transfer amount must be greater than zero.")
            return

        session = Session()
        try:
            from_name = ""
            to_name = ""
            
            if from_data[0] == 'bank':
                bank_from = session.query(BankAccount).get(from_data[1])
                if not bank_from:
                    QMessageBox.warning(self, "Error", "Source bank account not found.")
                    session.close()
                    return
                from_name = f"{bank_from.bank_name} ({bank_from.account_name})"
                if bank_from.balance < amount:
                    QMessageBox.warning(self, "Insufficient Funds", f"Insufficient balance in {from_name}.\nAvailable: ₹{bank_from.balance:,.2f}")
                    session.close()
                    return
            else:
                from_name = "Cash Ledger"
                cash_in = session.query(func.sum(CashTransaction.amount)).filter(CashTransaction.transaction_type == 'in').scalar() or 0.0
                cash_out = session.query(func.sum(CashTransaction.amount)).filter(CashTransaction.transaction_type == 'out').scalar() or 0.0
                cash_balance = cash_in - cash_out
                if cash_balance < amount:
                    QMessageBox.warning(self, "Insufficient Funds", f"Insufficient cash in hand.\nAvailable: ₹{cash_balance:,.2f}")
                    session.close()
                    return

            if to_data[0] == 'bank':
                bank_to = session.query(BankAccount).get(to_data[1])
                if not bank_to:
                    QMessageBox.warning(self, "Error", "Destination bank account not found.")
                    session.close()
                    return
                to_name = f"{bank_to.bank_name} ({bank_to.account_name})"
            else:
                to_name = "Cash Ledger"

            transfer = FundTransfer(
                date=tx_date,
                from_type=from_data[0],
                from_account_id=from_data[1] if from_data[0] == 'bank' else None,
                to_type=to_data[0],
                to_account_id=to_data[1] if to_data[0] == 'bank' else None,
                amount=amount,
                remarks=remarks
            )
            session.add(transfer)
            session.flush()

            desc_out = f"Fund Transfer to {to_name}. Remarks: {remarks or '-'}"
            desc_in = f"Fund Transfer from {from_name}. Remarks: {remarks or '-'}"

            if from_data[0] == 'bank':
                tx_out = BankTransaction(
                    date=tx_date, transaction_type='withdrawal', account_id=from_data[1],
                    amount=amount, source_type='transfer', source_id=transfer.id, description=desc_out
                )
                session.add(tx_out)
                bank_from.balance -= amount
            else:
                tx_out = CashTransaction(
                    date=tx_date, transaction_type='out', amount=amount,
                    source_type='transfer', source_id=transfer.id, description=desc_out
                )
                session.add(tx_out)

            if to_data[0] == 'bank':
                tx_in = BankTransaction(
                    date=tx_date, transaction_type='deposit', account_id=to_data[1],
                    amount=amount, source_type='transfer', source_id=transfer.id, description=desc_in
                )
                session.add(tx_in)
                bank_to.balance += amount
            else:
                tx_in = CashTransaction(
                    date=tx_date, transaction_type='in', amount=amount,
                    source_type='transfer', source_id=transfer.id, description=desc_in
                )
                session.add(tx_in)

            session.commit()
            QMessageBox.information(self, "Success", f"Successfully transferred ₹{amount:,.2f} from {from_name} to {to_name}.")
            self.t_amount.setValue(0.0)
            self.t_remarks.clear()
            self.refresh_data()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to execute transfer: {e}")
        finally:
            session.close()

    def delete_fund_transfer_record(self, transfer_id):
        confirm = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete/revert this transfer record?\nThe source and destination balances will be reverted.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        session = Session()
        try:
            transfer = session.query(FundTransfer).get(transfer_id)
            if not transfer:
                QMessageBox.warning(self, "Error", "Transfer record not found.")
                session.close()
                return

            if transfer.to_type == 'bank':
                bank_to = session.query(BankAccount).get(transfer.to_account_id)
                if bank_to:
                    if bank_to.balance < transfer.amount:
                        QMessageBox.warning(self, "Validation Error", f"Cannot delete transfer. Destination bank account {bank_to.bank_name} has insufficient funds to revert this transfer.")
                        session.close()
                        return
                    bank_to.balance -= transfer.amount
            else:
                cash_in = session.query(func.sum(CashTransaction.amount)).filter(CashTransaction.transaction_type == 'in').scalar() or 0.0
                cash_out = session.query(func.sum(CashTransaction.amount)).filter(CashTransaction.transaction_type == 'out').scalar() or 0.0
                cash_balance = cash_in - cash_out
                if cash_balance < transfer.amount:
                    QMessageBox.warning(self, "Validation Error", f"Cannot delete transfer. Cash Ledger has insufficient funds to revert this transfer.")
                    session.close()
                    return

            # Delete the FundTransfer record
            session.delete(transfer)
            session.commit()
            
            QMessageBox.information(self, "Success", "Transfer reverted and deleted successfully.")
            self.refresh_data()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to revert transfer: {e}")
        finally:
            session.close()

    def setup_direct_tab(self):
        layout = QHBoxLayout(self.direct_tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)

        # Form Card
        form_frame = QFrame()
        form_frame.setProperty("class", "CardFrame")
        form_frame.setFixedWidth(380)
        form_layout = QFormLayout(form_frame)
        form_layout.setContentsMargins(15, 15, 15, 15)
        form_layout.setSpacing(12)

        lbl = QLabel("New Direct Inflow/Outflow")
        lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff; margin-bottom: 10px;")
        form_layout.addRow(lbl)

        self.d_date = QDateEdit()
        self.d_date.setCalendarPopup(True)
        self.d_date.setDate(QDate.currentDate())

        self.d_type = QComboBox()
        self.d_type.addItems(["Deposit (Inflow)", "Withdrawal (Outflow)"])

        self.d_account_type = QComboBox()
        self.d_account_type.addItems(["Cash Ledger", "Bank Account"])
        self.d_account_type.currentIndexChanged.connect(self.handle_direct_account_type_change)

        self.d_bank = QComboBox()
        self.d_bank.setEnabled(False)

        self.d_amount = QDoubleSpinBox()
        self.d_amount.setRange(0.01, 9999999.0)
        self.d_amount.setDecimals(2)

        self.d_desc = QLineEdit()
        self.d_desc.setPlaceholderText("Description (e.g. Capital, rent, interest)")

        form_layout.addRow("Transaction Date:", self.d_date)
        form_layout.addRow("Transaction Type *:", self.d_type)
        form_layout.addRow("Account Type *:", self.d_account_type)
        form_layout.addRow("Select Bank:", self.d_bank)
        form_layout.addRow("Amount (₹) *:", self.d_amount)
        form_layout.addRow("Description *:", self.d_desc)

        self.d_save_btn = QPushButton("Save Transaction")
        self.d_save_btn.setProperty("class", "btn-success")
        self.d_save_btn.clicked.connect(self.save_direct_transaction)
        form_layout.addRow("", self.d_save_btn)

        layout.addWidget(form_frame)

        # Right Card: Direct Transactions History Table
        history_frame = QFrame()
        history_frame.setProperty("class", "CardFrame")
        history_layout = QVBoxLayout(history_frame)
        history_layout.setContentsMargins(15, 15, 15, 15)
        
        history_title = QLabel("Direct Transactions Log")
        history_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff; margin-bottom: 10px;")
        history_layout.addWidget(history_title)

        self.direct_table = QTableWidget()
        self.direct_table.setColumnCount(7)
        self.direct_table.setHorizontalHeaderLabels([
            "ID", "Date", "Type", "Account", "Amount (₹)", "Description", "Actions"
        ])
        self.direct_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.direct_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.direct_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Fixed)
        self.direct_table.setColumnWidth(6, 120)
        self.direct_table.verticalHeader().setVisible(False)
        self.direct_table.verticalHeader().setDefaultSectionSize(48)
        history_layout.addWidget(self.direct_table)

        # Lazy loading state
        self.direct_offset = 0
        self.has_more_direct = True
        self.direct_table.verticalScrollBar().valueChanged.connect(self.handle_direct_scroll)

        layout.addWidget(history_frame)

    def handle_direct_account_type_change(self, index):
        self.d_bank.setEnabled(index == 1)

    def save_direct_transaction(self):
        tx_type = "deposit" if "Deposit" in self.d_type.currentText() else "withdrawal"
        account_type = "cash" if "Cash" in self.d_account_type.currentText() else "bank"
        bank_id = self.d_bank.currentData() if account_type == "bank" else None
        amount = self.d_amount.value()
        desc = self.d_desc.text().strip()
        date_q = self.d_date.date()
        tx_date = datetime.date(date_q.year(), date_q.month(), date_q.day())

        if account_type == "bank" and not bank_id:
            QMessageBox.warning(self, "Validation Error", "Please select a valid Bank Account.")
            return

        if amount <= 0:
            QMessageBox.warning(self, "Validation Error", "Amount must be greater than zero.")
            return

        if not desc:
            QMessageBox.warning(self, "Validation Error", "Please enter a description.")
            return

        session = Session()
        try:
            target_name = ""
            if account_type == "bank":
                bank = session.query(BankAccount).get(bank_id)
                if not bank:
                    QMessageBox.warning(self, "Error", "Bank account not found.")
                    session.close()
                    return
                target_name = f"{bank.bank_name} ({bank.account_name})"
                
                if tx_type == "withdrawal" and bank.balance < amount:
                    QMessageBox.warning(self, "Insufficient Funds", f"Insufficient funds in bank account.\nAvailable: ₹{bank.balance:,.2f}")
                    session.close()
                    return
            else:
                target_name = "Cash Ledger"
                if tx_type == "withdrawal":
                    cash_in = session.query(func.sum(CashTransaction.amount)).filter(CashTransaction.transaction_type == 'in').scalar() or 0.0
                    cash_out = session.query(func.sum(CashTransaction.amount)).filter(CashTransaction.transaction_type == 'out').scalar() or 0.0
                    cash_balance = cash_in - cash_out
                    if cash_balance < amount:
                        QMessageBox.warning(self, "Insufficient Funds", f"Insufficient cash in hand.\nAvailable: ₹{cash_balance:,.2f}")
                        session.close()
                        return

            dt = DirectTransaction(
                date=tx_date,
                transaction_type=tx_type,
                account_type=account_type,
                bank_id=bank_id,
                amount=amount,
                description=desc
            )
            session.add(dt)
            session.flush()

            if account_type == "bank":
                db_tx_type = "deposit" if tx_type == "deposit" else "withdrawal"
                tx = BankTransaction(
                    date=tx_date,
                    transaction_type=db_tx_type,
                    account_id=bank_id,
                    amount=amount,
                    source_type='direct',
                    source_id=dt.id,
                    description=f"Direct {tx_type.capitalize()}: {desc}"
                )
                session.add(tx)
                
                if tx_type == "deposit":
                    bank.balance += amount
                else:
                    bank.balance -= amount
            else:
                db_tx_type = "in" if tx_type == "deposit" else "out"
                tx = CashTransaction(
                    date=tx_date,
                    transaction_type=db_tx_type,
                    amount=amount,
                    source_type='direct',
                    source_id=dt.id,
                    description=f"Direct {tx_type.capitalize()}: {desc}"
                )
                session.add(tx)

            session.commit()
            QMessageBox.information(self, "Success", f"Direct {tx_type.capitalize()} of ₹{amount:,.2f} recorded in {target_name} successfully.")
            self.d_amount.setValue(0.0)
            self.d_desc.clear()
            self.refresh_data()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save direct transaction: {e}")
        finally:
            session.close()

    def delete_direct_transaction_record(self, transaction_id):
        confirm = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete/revert this direct transaction?\nThe balances will be reverted.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        session = Session()
        try:
            dt = session.query(DirectTransaction).get(transaction_id)
            if not dt:
                QMessageBox.warning(self, "Error", "Transaction record not found.")
                session.close()
                return

            if dt.transaction_type == 'deposit':
                if dt.account_type == 'bank':
                    bank = session.query(BankAccount).get(dt.bank_id)
                    if bank and bank.balance < dt.amount:
                        QMessageBox.warning(self, "Validation Error", f"Cannot delete transaction. Bank account {bank.bank_name} has insufficient balance to revert this deposit.")
                        session.close()
                        return
                    if bank:
                        bank.balance -= dt.amount
                else:
                    cash_in = session.query(func.sum(CashTransaction.amount)).filter(CashTransaction.transaction_type == 'in').scalar() or 0.0
                    cash_out = session.query(func.sum(CashTransaction.amount)).filter(CashTransaction.transaction_type == 'out').scalar() or 0.0
                    cash_balance = cash_in - cash_out
                    if cash_balance < dt.amount:
                        QMessageBox.warning(self, "Validation Error", f"Cannot delete transaction. Cash Ledger has insufficient balance to revert this deposit.")
                        session.close()
                        return
            else:
                if dt.account_type == 'bank':
                    bank = session.query(BankAccount).get(dt.bank_id)
                    if bank:
                        bank.balance += dt.amount

            cash_txs = session.query(CashTransaction).filter_by(source_type='direct', source_id=dt.id).all()
            for tx in cash_txs:
                session.delete(tx)

            bank_txs = session.query(BankTransaction).filter_by(source_type='direct', source_id=dt.id).all()
            for tx in bank_txs:
                session.delete(tx)

            session.delete(dt)
            session.commit()
            
            QMessageBox.information(self, "Success", "Direct transaction deleted and balances reverted successfully.")
            self.refresh_data()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to revert direct transaction: {e}")
        finally:
            session.close()

    def refresh_data(self):
        session = Session()
        try:
            # 1. Load Customers
            self.c_customer_combo.blockSignals(True)
            self.c_customer_combo.clear()
            self.c_customer_combo.addItem("-- Select Customer --", None)
            self.customers_cache = {}
            customers = session.query(Customer).all()
            for c in customers:
                self.customers_cache[c.id] = c
                self.c_customer_combo.addItem(c.name, c.id)
            self.c_customer_combo.blockSignals(False)
            self.update_cust_outstanding_lbl()
            self.check_c_customer_match()

            # 2. Load Suppliers
            self.s_supplier_combo.blockSignals(True)
            self.s_supplier_combo.clear()
            self.s_supplier_combo.addItem("-- Select Supplier --", None)
            self.suppliers_cache = {}
            suppliers = session.query(Supplier).all()
            for s in suppliers:
                self.suppliers_cache[s.id] = s
                self.s_supplier_combo.addItem(s.name, s.id)
            self.s_supplier_combo.blockSignals(False)
            self.update_supp_outstanding_lbl()
            self.check_s_supplier_match()

            # 3. Load Banks
            self.c_bank.clear()
            self.s_bank.clear()
            self.banks_list = []
            banks = session.query(BankAccount).all()
            for b in banks:
                self.c_bank.addItem(f"{b.bank_name} ({b.account_name})", b.id)
                self.s_bank.addItem(f"{b.bank_name} ({b.account_name})", b.id)
                self.banks_list.append((f"{b.bank_name} ({b.account_name})", b.id))

            # Populate transfer "From" dropdown
            self.t_from.blockSignals(True)
            current_from_data = self.t_from.currentData()
            self.t_from.clear()
            self.t_from.addItem("Cash Ledger", ('cash', None))
            for b_name, b_id in self.banks_list:
                self.t_from.addItem(b_name, ('bank', b_id))
            
            if current_from_data:
                for idx in range(self.t_from.count()):
                    if self.t_from.itemData(idx) == current_from_data:
                        self.t_from.setCurrentIndex(idx)
                        break
            self.t_from.blockSignals(False)
            
            self.populate_transfer_destinations()

            # Populate direct "Bank" dropdown
            self.d_bank.blockSignals(True)
            current_bank_id = self.d_bank.currentData()
            self.d_bank.clear()
            for b_name, b_id in self.banks_list:
                self.d_bank.addItem(b_name, b_id)
            if current_bank_id:
                for idx in range(self.d_bank.count()):
                    if self.d_bank.itemData(idx) == current_bank_id:
                        self.d_bank.setCurrentIndex(idx)
                        break
            self.d_bank.blockSignals(False)

            # 4. Load histories
            self.load_payments_history(reset=True)
            self.load_transfers_history(reset=True)
            self.load_direct_history(reset=True)

        except Exception as e:
            print(f"Error loading payments view data: {e}")
        finally:
            session.close()

    def handle_history_scroll(self, value):
        scrollbar = self.history_table.verticalScrollBar()
        if value == scrollbar.maximum() and scrollbar.maximum() > 0:
            if self.has_more_history:
                self.history_offset += 25
                self.load_payments_history(reset=False)

    def handle_transfer_scroll(self, value):
        scrollbar = self.transfer_table.verticalScrollBar()
        if value == scrollbar.maximum() and scrollbar.maximum() > 0:
            if self.has_more_transfers:
                self.transfer_offset += 25
                self.load_transfers_history(reset=False)

    def handle_direct_scroll(self, value):
        scrollbar = self.direct_table.verticalScrollBar()
        if value == scrollbar.maximum() and scrollbar.maximum() > 0:
            if self.has_more_direct:
                self.direct_offset += 25
                self.load_direct_history(reset=False)

    def load_payments_history(self, reset=True):
        if not isinstance(reset, bool):
            reset = True

        if reset:
            self.history_offset = 0
            self.has_more_history = True
            self.history_table.setRowCount(0)

        session = Session()
        try:
            history = session.query(Payment).order_by(Payment.id.desc()).offset(self.history_offset).limit(25).all()
            if len(history) < 25:
                self.has_more_history = False

            start_row = self.history_table.rowCount()
            self.history_table.setRowCount(start_row + len(history))
            for offset_idx, p in enumerate(history):
                i = start_row + offset_idx
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
                
                remarks_text = p.remarks or ""
                if p.party_type == 'supplier' and p.purchase_id:
                    from models import PurchaseMaster
                    pur = session.query(PurchaseMaster).get(p.purchase_id)
                    if pur:
                        invoice_suffix = f" [Against Bill: {pur.invoice_number}]"
                        if remarks_text:
                            remarks_text = f"{remarks_text} {invoice_suffix}"
                        else:
                            remarks_text = invoice_suffix.strip()
                elif p.party_type == 'customer' and p.sales_id:
                    from models import SalesMaster
                    sal = session.query(SalesMaster).get(p.sales_id)
                    if sal:
                        invoice_suffix = f" [Against Invoice: {sal.invoice_number}]"
                        if remarks_text:
                            remarks_text = f"{remarks_text} {invoice_suffix}"
                        else:
                            remarks_text = invoice_suffix.strip()
                self.history_table.setItem(i, 6, QTableWidgetItem(remarks_text))
                
                # Action Buttons
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(6, 2, 6, 2)
                actions_layout.setSpacing(8)
                actions_layout.setAlignment(Qt.AlignCenter)
                
                view_btn = QPushButton("View")
                view_btn.setProperty("class", "btn-action-view")
                view_btn.clicked.connect(lambda checked, pid=p.id: self.view_payment_details(pid))
                actions_layout.addWidget(view_btn)
                
                del_btn = QPushButton("Delete")
                del_btn.setProperty("class", "btn-action-delete")
                del_btn.clicked.connect(lambda checked, pid=p.id: self.delete_payment_record(pid))
                actions_layout.addWidget(del_btn)
                
                self.history_table.setCellWidget(i, 7, actions_widget)
        except Exception as e:
            print(f"Error loading payments history: {e}")
        finally:
            session.close()

    def load_transfers_history(self, reset=True):
        if not isinstance(reset, bool):
            reset = True

        if reset:
            self.transfer_offset = 0
            self.has_more_transfers = True
            self.transfer_table.setRowCount(0)

        session = Session()
        try:
            transfers = session.query(FundTransfer).order_by(FundTransfer.id.desc()).offset(self.transfer_offset).limit(25).all()
            if len(transfers) < 25:
                self.has_more_transfers = False

            start_row = self.transfer_table.rowCount()
            self.transfer_table.setRowCount(start_row + len(transfers))
            for offset_idx, t in enumerate(transfers):
                i = start_row + offset_idx
                self.transfer_table.setItem(i, 0, QTableWidgetItem(str(t.id)))
                self.transfer_table.setItem(i, 1, QTableWidgetItem(t.date.strftime("%Y-%m-%d")))
                
                if t.from_type == 'bank':
                    from_lbl = f"{t.from_account.bank_name if t.from_account else 'Unknown Bank'}"
                else:
                    from_lbl = "Cash Ledger"
                self.transfer_table.setItem(i, 2, QTableWidgetItem(from_lbl))
                
                if t.to_type == 'bank':
                    to_lbl = f"{t.to_account.bank_name if t.to_account else 'Unknown Bank'}"
                else:
                    to_lbl = "Cash Ledger"
                self.transfer_table.setItem(i, 3, QTableWidgetItem(to_lbl))
                
                self.transfer_table.setItem(i, 4, QTableWidgetItem(f"₹{t.amount:,.2f}"))
                
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(6, 2, 6, 2)
                actions_layout.setSpacing(8)
                actions_layout.setAlignment(Qt.AlignCenter)
                
                del_btn = QPushButton("Delete")
                del_btn.setProperty("class", "btn-action-delete")
                del_btn.clicked.connect(lambda checked, tid=t.id: self.delete_fund_transfer_record(tid))
                actions_layout.addWidget(del_btn)
                
                self.transfer_table.setCellWidget(i, 5, actions_widget)
        except Exception as e:
            print(f"Error loading transfers history: {e}")
        finally:
            session.close()

    def load_direct_history(self, reset=True):
        if not isinstance(reset, bool):
            reset = True

        if reset:
            self.direct_offset = 0
            self.has_more_direct = True
            self.direct_table.setRowCount(0)

        session = Session()
        try:
            direct_txs = session.query(DirectTransaction).order_by(DirectTransaction.id.desc()).offset(self.direct_offset).limit(25).all()
            if len(direct_txs) < 25:
                self.has_more_direct = False

            start_row = self.direct_table.rowCount()
            self.direct_table.setRowCount(start_row + len(direct_txs))
            for offset_idx, t in enumerate(direct_txs):
                i = start_row + offset_idx
                self.direct_table.setItem(i, 0, QTableWidgetItem(str(t.id)))
                self.direct_table.setItem(i, 1, QTableWidgetItem(t.date.strftime("%Y-%m-%d")))
                
                type_item = QTableWidgetItem(t.transaction_type.capitalize())
                if t.transaction_type == 'deposit':
                    type_item.setForeground(Qt.green)
                else:
                    type_item.setForeground(Qt.red)
                self.direct_table.setItem(i, 2, type_item)
                
                if t.account_type == 'bank':
                    acc_lbl = f"Bank: {t.bank_account.bank_name if t.bank_account else 'Unknown Bank'}"
                else:
                    acc_lbl = "Cash Ledger"
                self.direct_table.setItem(i, 3, QTableWidgetItem(acc_lbl))
                
                self.direct_table.setItem(i, 4, QTableWidgetItem(f"₹{t.amount:,.2f}"))
                self.direct_table.setItem(i, 5, QTableWidgetItem(t.description or ""))
                
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(6, 2, 6, 2)
                actions_layout.setSpacing(8)
                actions_layout.setAlignment(Qt.AlignCenter)
                
                del_btn = QPushButton("Delete")
                del_btn.setProperty("class", "btn-action-delete")
                del_btn.clicked.connect(lambda checked, tid=t.id: self.delete_direct_transaction_record(tid))
                actions_layout.addWidget(del_btn)
                
                self.direct_table.setCellWidget(i, 6, actions_widget)
        except Exception as e:
            print(f"Error loading direct history: {e}")
        finally:
            session.close()

    def check_c_customer_match(self):
        text = self.c_customer_combo.currentText().strip()
        if not text or text == "-- Select Customer --":
            self.add_c_cust_btn.hide()
            return
        
        matched = False
        for i in range(self.c_customer_combo.count()):
            item_text = self.c_customer_combo.itemText(i).strip()
            if item_text and item_text != "-- Select Customer --" and item_text.lower() == text.lower():
                matched = True
                if self.c_customer_combo.currentIndex() != i:
                    self.c_customer_combo.blockSignals(True)
                    self.c_customer_combo.setCurrentIndex(i)
                    self.c_customer_combo.blockSignals(False)
                    self.update_cust_outstanding_lbl()
                break
        
        if not matched:
            self.add_c_cust_btn.show()
        else:
            self.add_c_cust_btn.hide()

    def handle_add_c_customer_click(self):
        from ui.masters.customers import CustomerDialog
        typed_text = self.c_customer_combo.currentText().strip()
        if typed_text == "-- Select Customer --":
            typed_text = ""
        dlg = CustomerDialog(initial_name=typed_text, parent=self)
        if dlg.exec() == QDialog.Accepted and hasattr(dlg, 'saved_customer_id'):
            self.refresh_data()
            for idx in range(self.c_customer_combo.count()):
                if self.c_customer_combo.itemData(idx) == dlg.saved_customer_id:
                    self.c_customer_combo.setCurrentIndex(idx)
                    break

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
        self.populate_cust_sales()

    def populate_cust_sales(self):
        cust_id = self.c_customer_combo.currentData()
        self.c_sales_combo.blockSignals(True)
        self.c_sales_combo.clear()
        self.c_sales_combo.addItem("-- Receive Against General Outstanding --", None)
        if cust_id:
            session = Session()
            try:
                from models import SalesMaster
                invoices = session.query(SalesMaster).filter(
                    SalesMaster.customer_id == cust_id,
                    SalesMaster.balance_receivable > 0
                ).order_by(SalesMaster.date.desc()).all()
                for inv in invoices:
                    self.c_sales_combo.addItem(f"{inv.invoice_number} (Bal: ₹{inv.balance_receivable:,.2f})", inv.id)
            except Exception as e:
                print(f"Error loading customer invoices: {e}")
            finally:
                session.close()
        self.c_sales_combo.blockSignals(False)

    def handle_cust_sales_selection(self):
        sales_id = self.c_sales_combo.currentData()
        if sales_id:
            session = Session()
            try:
                from models import SalesMaster
                s = session.query(SalesMaster).get(sales_id)
                if s:
                    self.c_amount.setValue(s.balance_receivable)
            except Exception as e:
                print(f"Error reading sales invoice details: {e}")
            finally:
                session.close()
        else:
            self.c_amount.setValue(0.0)

    def check_s_supplier_match(self):
        text = self.s_supplier_combo.currentText().strip()
        if not text or text == "-- Select Supplier --":
            self.add_s_supp_btn.hide()
            return
        
        matched = False
        for i in range(self.s_supplier_combo.count()):
            item_text = self.s_supplier_combo.itemText(i).strip()
            if item_text and item_text != "-- Select Supplier --" and item_text.lower() == text.lower():
                matched = True
                if self.s_supplier_combo.currentIndex() != i:
                    self.s_supplier_combo.blockSignals(True)
                    self.s_supplier_combo.setCurrentIndex(i)
                    self.s_supplier_combo.blockSignals(False)
                    self.update_supp_outstanding_lbl()
                break
        
        if not matched:
            self.add_s_supp_btn.show()
        else:
            self.add_s_supp_btn.hide()

    def handle_add_s_supplier_click(self):
        from ui.masters.suppliers import SupplierDialog
        typed_text = self.s_supplier_combo.currentText().strip()
        if typed_text == "-- Select Supplier --":
            typed_text = ""
        dlg = SupplierDialog(initial_name=typed_text, parent=self)
        if dlg.exec() == QDialog.Accepted and hasattr(dlg, 'saved_supplier_id'):
            self.refresh_data()
            for idx in range(self.s_supplier_combo.count()):
                if self.s_supplier_combo.itemData(idx) == dlg.saved_supplier_id:
                    self.s_supplier_combo.setCurrentIndex(idx)
                    break

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
        self.populate_supp_purchases()

    def populate_supp_purchases(self):
        supp_id = self.s_supplier_combo.currentData()
        self.s_purchase_combo.blockSignals(True)
        self.s_purchase_combo.clear()
        self.s_purchase_combo.addItem("-- Pay Against General Outstanding --", None)
        if supp_id:
            session = Session()
            try:
                from models import PurchaseMaster
                purchases = session.query(PurchaseMaster).filter(
                    PurchaseMaster.supplier_id == supp_id,
                    PurchaseMaster.balance_payable > 0
                ).order_by(PurchaseMaster.date.desc()).all()
                for p in purchases:
                    self.s_purchase_combo.addItem(f"{p.invoice_number} (Bal: ₹{p.balance_payable:,.2f})", p.id)
            except Exception as e:
                print(f"Error loading supplier purchases: {e}")
            finally:
                session.close()
        self.s_purchase_combo.blockSignals(False)

    def handle_supp_purchase_selection(self):
        purchase_id = self.s_purchase_combo.currentData()
        if purchase_id:
            session = Session()
            try:
                from models import PurchaseMaster
                p = session.query(PurchaseMaster).get(purchase_id)
                if p:
                    self.s_amount.setValue(p.balance_payable)
            except Exception as e:
                print(f"Error reading purchase details: {e}")
            finally:
                session.close()
        else:
            self.s_amount.setValue(0.0)

    def save_customer_collection(self):
        cust_id = self.c_customer_combo.currentData()
        amount = self.c_amount.value()
        mode = self.c_mode.currentText()
        bank_id = self.c_bank.currentData() if mode == "Bank" else None
        remarks = self.c_remarks.text().strip() or None
        sales_id = self.c_sales_combo.currentData()

        if not cust_id:
            QMessageBox.warning(self, "Validation Error", "Please select a Customer.")
            return

        date_q = self.c_date.date()
        tx_date = datetime.date(date_q.year(), date_q.month(), date_q.day())

        session = Session()
        try:
            from models import SalesMaster
            s = None
            if sales_id:
                s = session.query(SalesMaster).get(sales_id)
                if s:
                    if amount > s.balance_receivable + 0.01:
                        QMessageBox.warning(self, "Validation Error", f"Collection amount (₹{amount:,.2f}) cannot exceed the invoice's pending balance (₹{s.balance_receivable:,.2f}).")
                        session.close()
                        return
                    s.balance_receivable -= amount
                    s.paid_amount += amount

            # 1. Update Customer outstanding
            cust = session.query(Customer).get(cust_id)
            cust.outstanding_balance -= amount

            # 2. Add Payment record
            payment = Payment(
                date=tx_date, party_type='customer', party_id=cust_id,
                amount=amount, payment_mode=mode, bank_id=bank_id,
                sales_id=sales_id, remarks=remarks
            )
            session.add(payment)
            session.flush() # Generate payment.id

            # 3. Log Cash/Bank Ledger
            if s:
                desc = f"Collection from customer {cust.name} against invoice {s.invoice_number}. Details: {remarks or '-'}"
            else:
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
            if s:
                QMessageBox.information(self, "Success", f"Received ₹{amount:.2f} from customer {cust.name} against invoice {s.invoice_number}.")
            else:
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
        purchase_id = self.s_purchase_combo.currentData()

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

            from models import PurchaseMaster
            p = None
            if purchase_id:
                p = session.query(PurchaseMaster).get(purchase_id)
                if p:
                    if amount > p.balance_payable + 0.01:
                        QMessageBox.warning(self, "Validation Error", f"Payment amount (₹{amount:,.2f}) cannot exceed the bill's pending balance (₹{p.balance_payable:,.2f}).")
                        session.close()
                        return
                    p.balance_payable -= amount
                    p.paid_amount += amount

            # 1. Update Supplier outstanding
            supp = session.query(Supplier).get(supp_id)
            supp.outstanding_balance -= amount

            # 2. Add Payment record
            payment = Payment(
                date=tx_date, party_type='supplier', party_id=supp_id,
                amount=amount, payment_mode=mode, bank_id=bank_id,
                purchase_id=purchase_id, remarks=remarks
            )
            session.add(payment)
            session.flush() # Generate payment.id

            # 3. Log Cash/Bank Ledger
            if p:
                desc = f"Payment to supplier {supp.name} against bill {p.invoice_number}. Details: {remarks or '-'}"
            else:
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
            if p:
                QMessageBox.information(self, "Success", f"Paid ₹{amount:.2f} to supplier {supp.name} against bill {p.invoice_number}.")
            else:
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
            
            # Bottom Buttons (Print & Close)
            btn_layout = QHBoxLayout()
            btn_layout.addStretch()
            
            btn_text = "Print Receipt" if payment.party_type == 'customer' else "Print Voucher"
            print_btn = QPushButton(btn_text)
            print_btn.clicked.connect(lambda: self.print_payment_receipt(payment_id))
            btn_layout.addWidget(print_btn)
            
            close_btn = QPushButton("Close")
            close_btn.setProperty("class", "btn-secondary")
            close_btn.clicked.connect(dialog.accept)
            btn_layout.addWidget(close_btn)
            
            dlg_layout.addLayout(btn_layout)
            
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
                if payment.sales_id:
                    from models import SalesMaster
                    s = session.query(SalesMaster).get(payment.sales_id)
                    if s:
                        s.balance_receivable += payment.amount
                        s.paid_amount -= payment.amount
            else:
                supp = session.query(Supplier).get(payment.party_id)
                if supp:
                    supp.outstanding_balance += payment.amount  # add back outstanding since payment is deleted
                if payment.purchase_id:
                    from models import PurchaseMaster
                    p = session.query(PurchaseMaster).get(payment.purchase_id)
                    if p:
                        p.balance_payable += payment.amount
                        p.paid_amount -= payment.amount
                    
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
