import datetime
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QTableWidget, QTableWidgetItem, QHeaderView, QPushButton)
from PySide6.QtCore import Qt
from database import Session
from models import Customer, Supplier, SalesMaster, PurchaseMaster, ServiceJob, Payment

class LedgerBreakupDialog(QDialog):
    def __init__(self, party_type, party_id, party_name, parent=None):
        super().__init__(parent)
        self.party_type = party_type  # 'customer' or 'supplier'
        self.party_id = party_id
        self.party_name = party_name
        self.setWindowTitle(f"Ledger Statement - {party_name}")
        self.setMinimumSize(850, 500)
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header Title
        title_lbl = QLabel(f"<b>Transaction History Ledger</b>")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        
        party_lbl = QLabel(f"Party: <b>{self.party_name}</b> ({self.party_type.capitalize()})")
        party_lbl.setStyleSheet("font-size: 13px; color: #94a3b8;")

        header_layout = QHBoxLayout()
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()
        header_layout.addWidget(party_lbl)
        layout.addLayout(header_layout)

        # Table Widget
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        
        if self.party_type == 'customer':
            self.table.setHorizontalHeaderLabels([
                "Date", "Ref / Invoice", "Description", "Debit (+) (₹)", "Credit (-) (₹)", "Balance (₹)"
            ])
        else:
            self.table.setHorizontalHeaderLabels([
                "Date", "Ref / Invoice", "Description", "Debit (-) (₹)", "Credit (+) (₹)", "Balance (₹)"
            ])

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setStyleSheet("QTableWidget { background-color: #1e1e2f; gridline-color: #2e2e3f; }")
        
        layout.addWidget(self.table)

        # Footer Layout with Total Outstanding
        footer_layout = QHBoxLayout()
        
        self.total_lbl = QLabel("Net Balance: ₹0.00")
        self.total_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #f59e0b;")
        footer_layout.addWidget(self.total_lbl)
        
        footer_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.setProperty("class", "btn-secondary")
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.accept)
        footer_layout.addWidget(close_btn)
        
        layout.addLayout(footer_layout)

    def load_data(self):
        session = Session()
        try:
            transactions = []

            if self.party_type == 'customer':
                customer = session.query(Customer).get(self.party_id)
                if not customer:
                    return

                # 1. Sales Invoices
                sales = session.query(SalesMaster).filter_by(customer_id=self.party_id).all()
                for s in sales:
                    transactions.append({
                        "date": s.date,
                        "ref": s.invoice_number,
                        "desc": "Sales Invoice Billing",
                        "debit": s.total_amount,
                        "credit": s.paid_amount
                    })

                # 2. Service Center repair jobs (linked by mobile number)
                jobs = session.query(ServiceJob).filter_by(mobile=customer.mobile).all()
                for j in jobs:
                    j_date = j.created_at.date() if isinstance(j.created_at, datetime.datetime) else j.created_at
                    transactions.append({
                        "date": j_date,
                        "ref": j.job_number,
                        "desc": f"Repair Svc: {j.device_model}",
                        "debit": j.total_amount,
                        "credit": j.paid_amount
                    })

                # 3. Custom payment collections (Payment Table)
                payments = session.query(Payment).filter_by(party_type='customer', party_id=self.party_id).all()
                for p in payments:
                    transactions.append({
                        "date": p.date,
                        "ref": f"Receipt #{p.id}",
                        "desc": p.remarks or "Payment Collection",
                        "debit": 0.0,
                        "credit": p.amount
                    })

                # Sort chronologically by date
                transactions.sort(key=lambda x: x["date"])

                # Add Opening Balance/Untracked Legacy Balance if there's a discrepancy
                total_tx_balance = sum(tx["debit"] - tx["credit"] for tx in transactions)
                opening_balance = customer.outstanding_balance - total_tx_balance
                if abs(opening_balance) > 0.01:
                    earliest_date = transactions[0]["date"] if transactions else datetime.date.today()
                    if isinstance(earliest_date, datetime.datetime):
                        earliest_date = earliest_date.date()
                    transactions.insert(0, {
                        "date": earliest_date,
                        "ref": "OPENING",
                        "desc": "Opening / Legacy Balance",
                        "debit": opening_balance if opening_balance > 0 else 0.0,
                        "credit": -opening_balance if opening_balance < 0 else 0.0
                    })

                self.table.setRowCount(len(transactions))
                running_balance = 0.0
                for i, tx in enumerate(transactions):
                    running_balance += tx["debit"] - tx["credit"]
                    
                    self.table.setItem(i, 0, QTableWidgetItem(tx["date"].strftime("%Y-%m-%d")))
                    self.table.setItem(i, 1, QTableWidgetItem(tx["ref"]))
                    self.table.setItem(i, 2, QTableWidgetItem(tx["desc"]))
                    
                    deb_item = QTableWidgetItem(f"₹{tx['debit']:,.2f}" if tx["debit"] > 0 else "-")
                    if tx["debit"] > 0:
                        deb_item.setForeground(Qt.red)
                    self.table.setItem(i, 3, deb_item)

                    cred_item = QTableWidgetItem(f"₹{tx['credit']:,.2f}" if tx["credit"] > 0 else "-")
                    if tx["credit"] > 0:
                        cred_item.setForeground(Qt.green)
                    self.table.setItem(i, 4, cred_item)

                    bal_item = QTableWidgetItem(f"₹{running_balance:,.2f}")
                    self.table.setItem(i, 5, bal_item)

                self.total_lbl.setText(f"Net Outstanding Balance: ₹{running_balance:,.2f}")
                if running_balance > 0:
                    self.total_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #f59e0b;")
                else:
                    self.total_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #10b981;")

            else:
                supplier = session.query(Supplier).get(self.party_id)
                if not supplier:
                    return

                # 1. Purchase Bills
                purchases = session.query(PurchaseMaster).filter_by(supplier_id=self.party_id).all()
                for p in purchases:
                    transactions.append({
                        "date": p.date,
                        "ref": p.invoice_number,
                        "desc": "Purchase Bill Billing",
                        "debit": p.paid_amount,
                        "credit": p.total_amount
                    })

                # 2. Custom supplier payments (Payment Table)
                payments = session.query(Payment).filter_by(party_type='supplier', party_id=self.party_id).all()
                for p in payments:
                    transactions.append({
                        "date": p.date,
                        "ref": f"Voucher #{p.id}",
                        "desc": p.remarks or "Supplier Payment",
                        "debit": p.amount,
                        "credit": 0.0
                    })

                # Sort chronologically by date
                transactions.sort(key=lambda x: x["date"])

                # Add Opening Balance/Untracked Legacy Balance if there's a discrepancy
                total_tx_balance = sum(tx["credit"] - tx["debit"] for tx in transactions)
                opening_balance = supplier.outstanding_balance - total_tx_balance
                if abs(opening_balance) > 0.01:
                    earliest_date = transactions[0]["date"] if transactions else datetime.date.today()
                    if isinstance(earliest_date, datetime.datetime):
                        earliest_date = earliest_date.date()
                    transactions.insert(0, {
                        "date": earliest_date,
                        "ref": "OPENING",
                        "desc": "Opening / Legacy Balance",
                        "debit": -opening_balance if opening_balance < 0 else 0.0,
                        "credit": opening_balance if opening_balance > 0 else 0.0
                    })

                self.table.setRowCount(len(transactions))
                running_balance = 0.0
                for i, tx in enumerate(transactions):
                    running_balance += tx["credit"] - tx["debit"]
                    
                    self.table.setItem(i, 0, QTableWidgetItem(tx["date"].strftime("%Y-%m-%d")))
                    self.table.setItem(i, 1, QTableWidgetItem(tx["ref"]))
                    self.table.setItem(i, 2, QTableWidgetItem(tx["desc"]))
                    
                    deb_item = QTableWidgetItem(f"₹{tx['debit']:,.2f}" if tx["debit"] > 0 else "-")
                    if tx["debit"] > 0:
                        deb_item.setForeground(Qt.green)
                    self.table.setItem(i, 3, deb_item)

                    cred_item = QTableWidgetItem(f"₹{tx['credit']:,.2f}" if tx["credit"] > 0 else "-")
                    if tx["credit"] > 0:
                        cred_item.setForeground(Qt.red)
                    self.table.setItem(i, 4, cred_item)

                    bal_item = QTableWidgetItem(f"₹{running_balance:,.2f}")
                    self.table.setItem(i, 5, bal_item)

                self.total_lbl.setText(f"Net Payable Balance: ₹{running_balance:,.2f}")
                if running_balance > 0:
                    self.total_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #ef4444;")
                else:
                    self.total_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #10b981;")

        except Exception as e:
            print(f"Error loading ledger breakup dialog: {e}")
        finally:
            session.close()
