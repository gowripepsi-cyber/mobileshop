import datetime
import os
import pandas as pd
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QPushButton, QCheckBox, 
                             QMessageBox, QFileDialog, QTabWidget, QFrame, QFormLayout)
from PySide6.QtCore import Qt
from database import Session
from sqlalchemy.orm import joinedload
from models import Product, Customer, Supplier, BankAccount, SalesMaster, SalesItem, PurchaseMaster, ServiceJob, ServicePart, CashTransaction, BankTransaction

class ReportsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self.tabs = QTabWidget()

        # Tab 1: Ledgers
        self.ledgers_tab = QWidget()
        self.setup_ledgers_tab()
        self.tabs.addTab(self.ledgers_tab, "Cash & Bank Ledgers")

        # Tab 2: Profit & Loss
        self.pl_tab = QWidget()
        self.setup_pl_tab()
        self.tabs.addTab(self.pl_tab, "Profit & Loss Statement")

        # Tab 3: Exports
        self.exports_tab = QWidget()
        self.setup_exports_tab()
        self.tabs.addTab(self.exports_tab, "Export Data Reports")

        layout.addWidget(self.tabs)

    def setup_ledgers_tab(self):
        layout = QHBoxLayout(self.ledgers_tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Left Column: Cash Book
        cash_frame = QFrame()
        cash_frame.setProperty("class", "CardFrame")
        cash_layout = QVBoxLayout(cash_frame)
        cash_layout.addWidget(QLabel("<b>Cash Book Ledger</b>"))
        
        self.cash_table = QTableWidget()
        self.cash_table.setColumnCount(3)
        self.cash_table.setHorizontalHeaderLabels(["Date", "Desc / Type", "Amount (₹)"])
        self.cash_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.cash_table.verticalHeader().setVisible(False)
        cash_layout.addWidget(self.cash_table)
        
        self.cash_balance_lbl = QLabel("Cash in Hand: ₹0.00")
        self.cash_balance_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #10b981;")
        cash_layout.addWidget(self.cash_balance_lbl)

        layout.addWidget(cash_frame)

        # Right Column: Bank Book
        bank_frame = QFrame()
        bank_frame.setProperty("class", "CardFrame")
        bank_layout = QVBoxLayout(bank_frame)
        bank_layout.addWidget(QLabel("<b>Bank Book Ledger</b>"))
        
        self.bank_table = QTableWidget()
        self.bank_table.setColumnCount(4)
        self.bank_table.setHorizontalHeaderLabels(["Date", "Bank Name", "Desc / Type", "Amount (₹)"])
        self.bank_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.bank_table.verticalHeader().setVisible(False)
        bank_layout.addWidget(self.bank_table)

        self.bank_balance_lbl = QLabel("Total Bank Balances: ₹0.00")
        self.bank_balance_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #3b82f6;")
        bank_layout.addWidget(self.bank_balance_lbl)

        layout.addWidget(bank_frame)

    def setup_pl_tab(self):
        layout = QVBoxLayout(self.pl_tab)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        pl_frame = QFrame()
        pl_frame.setProperty("class", "CardFrame")
        pl_frame.setMaximumWidth(600)
        
        form_layout = QFormLayout(pl_frame)
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setSpacing(15)

        title = QLabel("Income & Expense Statement (P&L)")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff; margin-bottom: 15px;")
        form_layout.addRow(title)

        # Revenue rows
        self.sales_rev_lbl = QLabel("₹0.00")
        self.service_rev_lbl = QLabel("₹0.00")
        self.total_rev_lbl = QLabel("₹0.00")
        self.total_rev_lbl.setStyleSheet("font-weight: bold; color: #6366f1;")

        # Expenses rows
        self.cogs_lbl = QLabel("₹0.00")  # Cost of Goods Sold
        self.parts_exp_lbl = QLabel("₹0.00")  # Spare parts expense
        self.total_exp_lbl = QLabel("₹0.00")
        self.total_exp_lbl.setStyleSheet("font-weight: bold; color: #ef4444;")

        # Net Profit
        self.net_profit_lbl = QLabel("₹0.00")
        self.net_profit_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #10b981;")

        form_layout.addRow("Sales Invoice Revenue (+):", self.sales_rev_lbl)
        form_layout.addRow("Service Center Revenue (+):", self.service_rev_lbl)
        form_layout.addRow("<b>Total Gross Revenue:</b>", self.total_rev_lbl)
        form_layout.addRow(QLabel(""), QLabel("")) # Spacer row
        form_layout.addRow("Cost of Mobile Inventory Sold (-):", self.cogs_lbl)
        form_layout.addRow("Cost of Service Spares Used (-):", self.parts_exp_lbl)
        form_layout.addRow("<b>Total Operating Costs:</b>", self.total_exp_lbl)
        form_layout.addRow(QFrame()) # Line divider
        form_layout.addRow("<b>NET PROFIT ESTIMATE (₹):</b>", self.net_profit_lbl)

        layout.addWidget(pl_frame, 0, Qt.AlignCenter)
        layout.addStretch()

    def setup_exports_tab(self):
        layout = QVBoxLayout(self.exports_tab)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        export_frame = QFrame()
        export_frame.setProperty("class", "CardFrame")
        export_frame.setMaximumWidth(500)
        export_layout = QVBoxLayout(export_frame)
        export_layout.setContentsMargins(20, 20, 20, 20)
        export_layout.setSpacing(15)

        title = QLabel("Select Reports to Export to Excel")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff; margin-bottom: 10px;")
        export_layout.addWidget(title)

        self.chk_stock = QCheckBox("Current Stock Ledger")
        self.chk_sales = QCheckBox("Sales Invoice Registry")
        self.chk_purchases = QCheckBox("Purchase Ledger Registry")
        self.chk_services = QCheckBox("Repairs & Job Cards Status List")
        self.chk_receivables = QCheckBox("Customer Receivables (Outstanding)")
        self.chk_payables = QCheckBox("Supplier Payables (Outstanding)")

        # Set checked by default
        for chk in [self.chk_stock, self.chk_sales, self.chk_purchases, self.chk_services, self.chk_receivables, self.chk_payables]:
            chk.setChecked(True)
            export_layout.addWidget(chk)

        export_layout.addSpacing(10)

        self.export_btn = QPushButton("Export Selected to Excel Sheet")
        self.export_btn.setProperty("class", "btn-success")
        self.export_btn.setFixedHeight(40)
        self.export_btn.clicked.connect(self.run_excel_export)
        export_layout.addWidget(self.export_btn)

        layout.addWidget(export_frame, 0, Qt.AlignCenter)
        layout.addStretch()

    def refresh_data(self):
        session = Session()
        try:
            # 1. Populate Cash Ledger
            cash_tx = session.query(CashTransaction).order_by(CashTransaction.date.desc()).all()
            self.cash_table.setRowCount(len(cash_tx))
            total_cash_in = 0.0
            total_cash_out = 0.0
            for i, tx in enumerate(cash_tx):
                self.cash_table.setItem(i, 0, QTableWidgetItem(tx.date.strftime("%Y-%m-%d")))
                self.cash_table.setItem(i, 1, QTableWidgetItem(tx.description))
                
                prefix = "+" if tx.transaction_type == 'in' else "-"
                amt_item = QTableWidgetItem(f"{prefix} ₹{tx.amount:,.2f}")
                if tx.transaction_type == 'in':
                    amt_item.setForeground(Qt.green)
                    total_cash_in += tx.amount
                else:
                    amt_item.setForeground(Qt.red)
                    total_cash_out += tx.amount
                self.cash_table.setItem(i, 2, amt_item)
            
            cash_balance = total_cash_in - total_cash_out
            self.cash_balance_lbl.setText(f"Cash in Hand: ₹{cash_balance:,.2f}")

            # 2. Populate Bank Ledger
            bank_tx = session.query(BankTransaction).order_by(BankTransaction.date.desc()).all()
            self.bank_table.setRowCount(len(bank_tx))
            for i, tx in enumerate(bank_tx):
                self.bank_table.setItem(i, 0, QTableWidgetItem(tx.date.strftime("%Y-%m-%d")))
                self.bank_table.setItem(i, 1, QTableWidgetItem(tx.bank_account.bank_name if tx.bank_account else "Unknown Bank"))
                self.bank_table.setItem(i, 2, QTableWidgetItem(tx.description))
                
                prefix = "+" if tx.transaction_type == 'deposit' else "-"
                amt_item = QTableWidgetItem(f"{prefix} ₹{tx.amount:,.2f}")
                if tx.transaction_type == 'deposit':
                    amt_item.setForeground(Qt.green)
                else:
                    amt_item.setForeground(Qt.red)
                self.bank_table.setItem(i, 3, amt_item)

            banks = session.query(BankAccount).all()
            total_bank_balance = sum(b.balance for b in banks)
            self.bank_balance_lbl.setText(f"Total Bank Balances: ₹{total_bank_balance:,.2f}")

            # 3. Populate P&L Statement
            sales_rev = session.query(func_sum(SalesMaster.total_amount)).scalar() or 0.0
            service_rev = session.query(func_sum(ServiceJob.total_amount)).scalar() or 0.0
            total_rev = sales_rev + service_rev

            # Calculate Cost of Goods Sold (cogs)
            # COGS = Sum of SalesItem.qty * Product.purchase_price
            cogs = 0.0
            sales_items = session.query(SalesItem).all()
            for si in sales_items:
                if si.product:
                    cogs += si.qty * si.product.purchase_price

            # Service Spare Parts Expense
            parts_exp = 0.0
            service_parts = session.query(ServicePart).options(joinedload(ServicePart.product)).all()
            for sp in service_parts:
                if sp.product_id and sp.product:
                    parts_exp += sp.qty * sp.product.purchase_price
                else:
                    parts_exp += sp.qty * sp.cost
            total_exp = cogs + parts_exp

            net_profit = total_rev - total_exp

            self.sales_rev_lbl.setText(f"₹{sales_rev:,.2f}")
            self.service_rev_lbl.setText(f"₹{service_rev:,.2f}")
            self.total_rev_lbl.setText(f"₹{total_rev:,.2f}")
            
            self.cogs_lbl.setText(f"₹{cogs:,.2f}")
            self.parts_exp_lbl.setText(f"₹{parts_exp:,.2f}")
            self.total_exp_lbl.setText(f"₹{total_exp:,.2f}")
            
            self.net_profit_lbl.setText(f"₹{net_profit:,.2f}")
            if net_profit >= 0:
                self.net_profit_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #10b981;")
            else:
                self.net_profit_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #ef4444;")

        except Exception as e:
            print(f"Error loading reports: {e}")
        finally:
            session.close()

    def run_excel_export(self):
        # Prompt for file save path
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Excel Report Suite", 
            os.path.abspath("MobileShop_ReportSuite.xlsx"), 
            "Excel Files (*.xlsx)"
        )
        if not file_path:
            return

        session = Session()
        try:
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                # 1. Stock
                if self.chk_stock.isChecked():
                    prods = session.query(Product).all()
                    data = [{
                        "Product ID": p.id,
                        "Product Name": p.name,
                        "Brand": p.brand,
                        "Model": p.model,
                        "IMEI Number": p.imei or "N/A",
                        "Purchase Price (₹)": p.purchase_price,
                        "Selling Price (₹)": p.selling_price,
                        "Stock Qty": p.stock_qty,
                        "Total Value (₹)": p.stock_qty * p.purchase_price
                    } for p in prods]
                    pd.DataFrame(data).to_excel(writer, sheet_name="Current Stock", index=False)

                # 2. Sales
                if self.chk_sales.isChecked():
                    sales = session.query(SalesMaster).all()
                    data = [{
                        "Invoice Number": s.invoice_number,
                        "Date": s.date.strftime("%Y-%m-%d"),
                        "Customer Name": s.customer.name,
                        "Customer Contact": s.customer.mobile,
                        "Total Amount (₹)": s.total_amount,
                        "Paid Amount (₹)": s.paid_amount,
                        "Balance Outstanding (₹)": s.balance_receivable
                    } for s in sales]
                    pd.DataFrame(data).to_excel(writer, sheet_name="Sales Registry", index=False)

                # 3. Purchases
                if self.chk_purchases.isChecked():
                    purchases = session.query(PurchaseMaster).all()
                    data = [{
                        "Invoice Number": p.invoice_number,
                        "Date": p.date.strftime("%Y-%m-%d"),
                        "Supplier Name": p.supplier.name,
                        "Supplier Contact": p.supplier.mobile,
                        "Total Amount (₹)": p.total_amount,
                        "Paid Amount (₹)": p.paid_amount,
                        "Balance Outstanding (₹)": p.balance_payable
                    } for p in purchases]
                    pd.DataFrame(data).to_excel(writer, sheet_name="Purchase Registry", index=False)

                # 4. Services
                if self.chk_services.isChecked():
                    jobs = session.query(ServiceJob).all()
                    data = [{
                        "Job Card #": j.job_number,
                        "Date Logged": j.created_at.strftime("%Y-%m-%d %H:%M"),
                        "Customer Name": j.customer_name,
                        "Contact Mobile": j.mobile,
                        "Device Model": j.device_model,
                        "IMEI/Serial": j.imei,
                        "Assigned Tech": j.technician or "-",
                        "Repair Status": j.status,
                        "Service Cost (₹)": j.service_charge,
                        "Total Billing (₹)": j.total_amount,
                        "Amount Paid (₹)": j.paid_amount,
                        "Remaining Balance (₹)": j.balance
                    } for j in jobs]
                    pd.DataFrame(data).to_excel(writer, sheet_name="Repair Jobs", index=False)

                # 5. Customer Outstanding
                if self.chk_receivables.isChecked():
                    custs = session.query(Customer).filter(Customer.outstanding_balance > 0).all()
                    data = [{
                        "Customer ID": c.id,
                        "Customer Name": c.name,
                        "Contact Number": c.mobile,
                        "Billing Address": c.address or "-",
                        "GSTIN": c.gst or "-",
                        "Receivables Balance (₹)": c.outstanding_balance
                    } for c in custs]
                    pd.DataFrame(data).to_excel(writer, sheet_name="Customer Receivables", index=False)

                # 6. Supplier Outstanding
                if self.chk_payables.isChecked():
                    supps = session.query(Supplier).filter(Supplier.outstanding_balance > 0).all()
                    data = [{
                        "Supplier ID": s.id,
                        "Supplier Name": s.name,
                        "Contact Number": s.mobile,
                        "Billing Address": s.address or "-",
                        "Payables Balance (₹)": s.outstanding_balance
                    } for s in supps]
                    pd.DataFrame(data).to_excel(writer, sheet_name="Supplier Payables", index=False)

            QMessageBox.information(self, "Success", f"Data exported successfully to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export data to Excel: {e}")
        finally:
            session.close()

# Helper function
def func_sum(column):
    from sqlalchemy import func
    return func.sum(column)
