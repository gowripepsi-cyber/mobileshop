import datetime
import os
import pandas as pd
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QPushButton, QCheckBox, 
                             QMessageBox, QFileDialog, QTabWidget, QFrame, QFormLayout,
                             QComboBox, QDateEdit)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from database import Session
from sqlalchemy.orm import joinedload
from models import Product, Customer, Supplier, BankAccount, SalesMaster, SalesItem, PurchaseMaster, ServiceJob, ServicePart, CashTransaction, BankTransaction, Payment

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

        # Tab 4: Customer Receivables
        self.receivables_tab = QWidget()
        self.setup_receivables_tab()
        self.tabs.addTab(self.receivables_tab, "Customer Receivables")

        # Tab 5: Supplier Payables
        self.payables_tab = QWidget()
        self.setup_payables_tab()
        self.tabs.addTab(self.payables_tab, "Supplier Payables")

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

        # Date filter controls frame/panel
        filter_frame = QFrame()
        filter_frame.setProperty("class", "CardFrame")
        filter_frame.setMaximumWidth(600)
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(15, 10, 15, 10)
        filter_layout.setSpacing(10)

        filter_layout.addWidget(QLabel("Date Filter:"))
        self.pl_date_filter_combo = QComboBox()
        self.pl_date_filter_combo.addItems(["All Time", "This Month", "This Year", "Custom Range"])
        self.pl_date_filter_combo.currentIndexChanged.connect(self.on_pl_date_filter_changed)
        filter_layout.addWidget(self.pl_date_filter_combo, 2)

        self.pl_start_label = QLabel("Start Date:")
        self.pl_start_date = QDateEdit()
        self.pl_start_date.setCalendarPopup(True)
        self.pl_start_date.setDisplayFormat("yyyy-MM-dd")
        self.pl_start_date.setDate(datetime.date.today())
        self.pl_start_date.dateChanged.connect(self.on_pl_custom_date_changed)
        filter_layout.addWidget(self.pl_start_label)
        filter_layout.addWidget(self.pl_start_date, 1.5)

        self.pl_end_label = QLabel("End Date:")
        self.pl_end_date = QDateEdit()
        self.pl_end_date.setCalendarPopup(True)
        self.pl_end_date.setDisplayFormat("yyyy-MM-dd")
        self.pl_end_date.setDate(datetime.date.today())
        self.pl_end_date.dateChanged.connect(self.on_pl_custom_date_changed)
        filter_layout.addWidget(self.pl_end_label)
        filter_layout.addWidget(self.pl_end_date, 1.5)

        # Hide start/end date pickers by default
        self.pl_start_label.hide()
        self.pl_start_date.hide()
        self.pl_end_label.hide()
        self.pl_end_date.hide()

        layout.addWidget(filter_frame, 0, Qt.AlignCenter)

        pl_frame = QFrame()
        pl_frame.setProperty("class", "CardFrame")
        pl_frame.setMaximumWidth(600)
        
        form_layout = QFormLayout(pl_frame)
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setSpacing(15)

        self.pl_title_lbl = QLabel("Income & Expense Statement (P&L)")
        self.pl_title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff; margin-bottom: 15px;")
        form_layout.addRow(self.pl_title_lbl)

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

    def on_pl_date_filter_changed(self, index):
        filter_text = self.pl_date_filter_combo.currentText()
        if filter_text == "Custom Range":
            self.pl_start_label.show()
            self.pl_start_date.show()
            self.pl_end_label.show()
            self.pl_end_date.show()
        else:
            self.pl_start_label.hide()
            self.pl_start_date.hide()
            self.pl_end_label.hide()
            self.pl_end_date.hide()
        
        self.refresh_data()

    def on_pl_custom_date_changed(self, qdate):
        self.refresh_data()

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
            if hasattr(self, 'pl_date_filter_combo'):
                # Determine date range for P&L Statement
                start_date = None
                end_date = None
                
                filter_text = self.pl_date_filter_combo.currentText()
                today = datetime.date.today()
                
                if filter_text == "This Month":
                    start_date = today.replace(day=1)
                    import calendar
                    _, last_day = calendar.monthrange(today.year, today.month)
                    end_date = today.replace(day=last_day)
                elif filter_text == "This Year":
                    start_date = datetime.date(today.year, 1, 1)
                    end_date = datetime.date(today.year, 12, 31)
                elif filter_text == "Custom Range":
                    qstart = self.pl_start_date.date()
                    start_date = datetime.date(qstart.year(), qstart.month(), qstart.day())
                    qend = self.pl_end_date.date()
                    end_date = datetime.date(qend.year(), qend.month(), qend.day())

                # Update card title dynamically
                title_text = "Income & Expense Statement (P&L)"
                if filter_text == "All Time":
                    title_text += " - All Time"
                elif filter_text == "This Month":
                    title_text += f" - {start_date.strftime('%B %Y')}"
                elif filter_text == "This Year":
                    title_text += f" - Year {today.year}"
                elif filter_text == "Custom Range":
                    title_text += f" ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})"
                
                self.pl_title_lbl.setText(title_text)

                # Query database with date filters
                sales_query = session.query(func_sum(SalesMaster.total_amount))
                service_query = session.query(func_sum(ServiceJob.total_amount))
                sales_item_query = session.query(SalesItem).join(SalesMaster)
                service_part_query = session.query(ServicePart).join(ServiceJob).options(joinedload(ServicePart.product))

                if start_date:
                    sales_query = sales_query.filter(SalesMaster.date >= start_date)
                    service_query = service_query.filter(ServiceJob.created_at >= datetime.datetime.combine(start_date, datetime.time.min))
                    sales_item_query = sales_item_query.filter(SalesMaster.date >= start_date)
                    service_part_query = service_part_query.filter(ServiceJob.created_at >= datetime.datetime.combine(start_date, datetime.time.min))

                if end_date:
                    sales_query = sales_query.filter(SalesMaster.date <= end_date)
                    service_query = service_query.filter(ServiceJob.created_at <= datetime.datetime.combine(end_date, datetime.time.max))
                    sales_item_query = sales_item_query.filter(SalesMaster.date <= end_date)
                    service_part_query = service_part_query.filter(ServiceJob.created_at <= datetime.datetime.combine(end_date, datetime.time.max))

                sales_rev = sales_query.scalar() or 0.0
                service_rev = service_query.scalar() or 0.0
                total_rev = sales_rev + service_rev

                # Calculate Cost of Goods Sold (cogs)
                cogs = 0.0
                sales_items = sales_item_query.all()
                for si in sales_items:
                    if si.product:
                        cogs += si.qty * si.product.purchase_price

                # Service Spare Parts Expense
                parts_exp = 0.0
                service_parts = service_part_query.all()
                for sp in service_parts:
                    if sp.product_id and sp.product:
                        parts_exp += sp.qty * sp.product.purchase_price
                    else:
                        parts_exp += sp.qty * sp.cost
                total_exp = cogs + parts_exp
            else:
                sales_rev = session.query(func_sum(SalesMaster.total_amount)).scalar() or 0.0
                service_rev = session.query(func_sum(ServiceJob.total_amount)).scalar() or 0.0
                total_rev = sales_rev + service_rev

                cogs = 0.0
                sales_items = session.query(SalesItem).all()
                for si in sales_items:
                    if si.product:
                        cogs += si.qty * si.product.purchase_price

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

            # 4. Populate Customer Receivables List
            customers = session.query(Customer).filter(Customer.outstanding_balance != 0).all()
            self.receivables_table.setRowCount(len(customers))
            total_receivable = 0.0
            for i, c in enumerate(customers):
                name_item = QTableWidgetItem(c.name)
                name_item.setData(Qt.UserRole, c.id)
                self.receivables_table.setItem(i, 0, name_item)
                self.receivables_table.setItem(i, 1, QTableWidgetItem(c.mobile))
                self.receivables_table.setItem(i, 2, QTableWidgetItem(f"₹{c.outstanding_balance:,.2f}"))
                total_receivable += c.outstanding_balance
            self.receivables_total_lbl.setText(f"Total: ₹{total_receivable:,.2f}")

            # 5. Populate Supplier Payables List
            suppliers = session.query(Supplier).filter(Supplier.outstanding_balance != 0).all()
            self.payables_table.setRowCount(len(suppliers))
            total_payable = 0.0
            for i, s in enumerate(suppliers):
                name_item = QTableWidgetItem(s.name)
                name_item.setData(Qt.UserRole, s.id)
                self.payables_table.setItem(i, 0, name_item)
                self.payables_table.setItem(i, 1, QTableWidgetItem(s.mobile))
                self.payables_table.setItem(i, 2, QTableWidgetItem(f"₹{s.outstanding_balance:,.2f}"))
                total_payable += s.outstanding_balance
            self.payables_total_lbl.setText(f"Total: ₹{total_payable:,.2f}")

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
                    custs = session.query(Customer).filter(Customer.outstanding_balance != 0).all()
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
                    supps = session.query(Supplier).filter(Supplier.outstanding_balance != 0).all()
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

    def setup_receivables_tab(self):
        main_layout = QHBoxLayout(self.receivables_tab)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # Left Column: Party List
        left_frame = QFrame()
        left_frame.setProperty("class", "CardFrame")
        left_frame.setFixedWidth(350)
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(10)
        
        left_layout.addWidget(QLabel("<b>Customer Outstanding Balances</b>"))
        
        self.receivables_table = QTableWidget()
        self.receivables_table.setColumnCount(3)
        self.receivables_table.setHorizontalHeaderLabels(["Customer", "Mobile", "Outstanding"])
        self.receivables_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.receivables_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.receivables_table.verticalHeader().setVisible(False)
        self.receivables_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.receivables_table.setSelectionMode(QTableWidget.SingleSelection)
        self.receivables_table.itemSelectionChanged.connect(self.load_customer_breakup)
        
        left_layout.addWidget(self.receivables_table)

        # Bottom controls for Left Frame: Total Receivable label & View/Print button
        left_bottom = QHBoxLayout()
        self.receivables_total_lbl = QLabel("Total: ₹0.00")
        self.receivables_total_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #f59e0b;")
        left_bottom.addWidget(self.receivables_total_lbl)
        
        left_bottom.addStretch()
        
        self.c_view_statement_btn = QPushButton("View Statement")
        self.c_view_statement_btn.setEnabled(False)
        self.c_view_statement_btn.clicked.connect(self.view_customer_statement)
        self.c_view_statement_btn.setStyleSheet("padding: 5px 10px; font-size: 12px;")
        left_bottom.addWidget(self.c_view_statement_btn)

        self.c_print_all_btn = QPushButton("Print All")
        self.c_print_all_btn.clicked.connect(self.print_all_customer_outstanding)
        self.c_print_all_btn.setStyleSheet("padding: 5px 10px; font-size: 12px;")
        left_bottom.addWidget(self.c_print_all_btn)
        
        left_layout.addLayout(left_bottom)
        main_layout.addWidget(left_frame)

        # Right Column: Detailed Ledger Breakup
        right_frame = QFrame()
        right_frame.setProperty("class", "CardFrame")
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(15, 15, 15, 15)
        right_layout.setSpacing(10)

        self.customer_breakup_lbl = QLabel("<b>Select a customer to view ledger breakup</b>")
        self.customer_breakup_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #6366f1;")
        right_layout.addWidget(self.customer_breakup_lbl)

        self.customer_breakup_table = QTableWidget()
        self.customer_breakup_table.setColumnCount(6)
        self.customer_breakup_table.setHorizontalHeaderLabels([
            "Date", "Ref / Type", "Description", "Debit (+) (₹)", "Credit (-) (₹)", "Balance (₹)"
        ])
        self.customer_breakup_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.customer_breakup_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        
        history_table_vertical_header = self.customer_breakup_table.verticalHeader()
        history_table_vertical_header.setVisible(False)
        history_table_vertical_header.setDefaultSectionSize(40)
        self.customer_breakup_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.customer_breakup_table.setSelectionMode(QTableWidget.NoSelection)
        self.customer_breakup_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.customer_breakup_table.cellClicked.connect(lambda row, col: self.on_breakup_cell_clicked(row, col, is_supplier=False))
        
        right_layout.addWidget(self.customer_breakup_table)

        bottom_layout = QHBoxLayout()
        self.customer_total_outstanding_lbl = QLabel("Net Outstanding: ₹0.00")
        self.customer_total_outstanding_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #f59e0b;")
        bottom_layout.addWidget(self.customer_total_outstanding_lbl)
        
        right_layout.addLayout(bottom_layout)

        main_layout.addWidget(right_frame)

    def setup_payables_tab(self):
        main_layout = QHBoxLayout(self.payables_tab)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # Left Column: Party List
        left_frame = QFrame()
        left_frame.setProperty("class", "CardFrame")
        left_frame.setFixedWidth(350)
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(10)
        
        left_layout.addWidget(QLabel("<b>Supplier Outstanding Balables</b>"))
        
        self.payables_table = QTableWidget()
        self.payables_table.setColumnCount(3)
        self.payables_table.setHorizontalHeaderLabels(["Supplier", "Mobile", "Payable"])
        self.payables_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.payables_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.payables_table.verticalHeader().setVisible(False)
        self.payables_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.payables_table.setSelectionMode(QTableWidget.SingleSelection)
        self.payables_table.itemSelectionChanged.connect(self.load_supplier_breakup)
        
        left_layout.addWidget(self.payables_table)

        # Bottom controls for Left Frame: Total Payable label & View/Print button
        left_bottom = QHBoxLayout()
        self.payables_total_lbl = QLabel("Total: ₹0.00")
        self.payables_total_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #ef4444;")
        left_bottom.addWidget(self.payables_total_lbl)
        
        left_bottom.addStretch()
        
        self.s_view_statement_btn = QPushButton("View Statement")
        self.s_view_statement_btn.setEnabled(False)
        self.s_view_statement_btn.clicked.connect(self.view_supplier_statement)
        self.s_view_statement_btn.setStyleSheet("padding: 5px 10px; font-size: 12px;")
        left_bottom.addWidget(self.s_view_statement_btn)

        self.s_print_all_btn = QPushButton("Print All")
        self.s_print_all_btn.clicked.connect(self.print_all_supplier_outstanding)
        self.s_print_all_btn.setStyleSheet("padding: 5px 10px; font-size: 12px;")
        left_bottom.addWidget(self.s_print_all_btn)
        
        left_layout.addLayout(left_bottom)
        main_layout.addWidget(left_frame)

        # Right Column: Detailed Ledger Breakup
        right_frame = QFrame()
        right_frame.setProperty("class", "CardFrame")
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(15, 15, 15, 15)
        right_layout.setSpacing(10)

        self.supplier_breakup_lbl = QLabel("<b>Select a supplier to view ledger breakup</b>")
        self.supplier_breakup_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #ef4444;")
        right_layout.addWidget(self.supplier_breakup_lbl)

        self.supplier_breakup_table = QTableWidget()
        self.supplier_breakup_table.setColumnCount(6)
        self.supplier_breakup_table.setHorizontalHeaderLabels([
            "Date", "Ref / Type", "Description", "Debit (-) (₹)", "Credit (+) (₹)", "Balance (₹)"
        ])
        self.supplier_breakup_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.supplier_breakup_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        
        supplier_table_vertical_header = self.supplier_breakup_table.verticalHeader()
        supplier_table_vertical_header.setVisible(False)
        supplier_table_vertical_header.setDefaultSectionSize(40)
        self.supplier_breakup_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.supplier_breakup_table.setSelectionMode(QTableWidget.NoSelection)
        self.supplier_breakup_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.supplier_breakup_table.cellClicked.connect(lambda row, col: self.on_breakup_cell_clicked(row, col, is_supplier=True))
        
        right_layout.addWidget(self.supplier_breakup_table)

        bottom_layout = QHBoxLayout()
        self.supplier_total_payable_lbl = QLabel("Net Payable: ₹0.00")
        self.supplier_total_payable_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #ef4444;")
        bottom_layout.addWidget(self.supplier_total_payable_lbl)
        
        right_layout.addLayout(bottom_layout)

        main_layout.addWidget(right_frame)

    def load_customer_breakup(self):
        selected = self.receivables_table.selectedItems()
        if not selected:
            self.customer_breakup_lbl.setText("<b>Select a customer to view ledger breakup</b>")
            self.customer_breakup_table.setRowCount(0)
            self.customer_total_outstanding_lbl.setText("Net Outstanding: ₹0.00")
            self.c_view_statement_btn.setEnabled(False)
            return

        row = selected[0].row()
        cust_id = self.receivables_table.item(row, 0).data(Qt.UserRole)
        cust_name = self.receivables_table.item(row, 0).text()

        self.customer_breakup_lbl.setText(f"<b>Ledger breakup for Customer: {cust_name}</b>")

        session = Session()
        try:
            customer = session.query(Customer).get(cust_id)
            if not customer:
                return

            transactions = []

            # 1. Sales Invoices
            sales = session.query(SalesMaster).filter_by(customer_id=cust_id).all()
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
            payments = session.query(Payment).filter_by(party_type='customer', party_id=cust_id).all()
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

            self.customer_breakup_table.setRowCount(len(transactions))
            running_balance = 0.0
            for i, tx in enumerate(transactions):
                running_balance += tx["debit"] - tx["credit"]
                
                self.customer_breakup_table.setItem(i, 0, QTableWidgetItem(tx["date"].strftime("%Y-%m-%d")))
                ref_item = QTableWidgetItem(tx["ref"])
                if tx["ref"] != "OPENING":
                    font = ref_item.font()
                    font.setUnderline(True)
                    ref_item.setFont(font)
                    ref_item.setForeground(QColor("#6366f1"))
                self.customer_breakup_table.setItem(i, 1, ref_item)
                self.customer_breakup_table.setItem(i, 2, QTableWidgetItem(tx["desc"]))
                
                deb_item = QTableWidgetItem(f"₹{tx['debit']:,.2f}" if tx["debit"] > 0 else "-")
                if tx["debit"] > 0:
                    deb_item.setForeground(Qt.red)
                self.customer_breakup_table.setItem(i, 3, deb_item)

                cred_item = QTableWidgetItem(f"₹{tx['credit']:,.2f}" if tx["credit"] > 0 else "-")
                if tx["credit"] > 0:
                    cred_item.setForeground(Qt.green)
                self.customer_breakup_table.setItem(i, 4, cred_item)

                bal_item = QTableWidgetItem(f"₹{running_balance:,.2f}")
                self.customer_breakup_table.setItem(i, 5, bal_item)

            self.customer_total_outstanding_lbl.setText(f"Net Outstanding: ₹{running_balance:,.2f}")
            self.c_view_statement_btn.setEnabled(True)

        except Exception as e:
            print(f"Error loading customer breakup: {e}")
        finally:
            session.close()

    def load_supplier_breakup(self):
        selected = self.payables_table.selectedItems()
        if not selected:
            self.supplier_breakup_lbl.setText("<b>Select a supplier to view ledger breakup</b>")
            self.supplier_breakup_table.setRowCount(0)
            self.supplier_total_payable_lbl.setText("Net Payable: ₹0.00")
            self.s_view_statement_btn.setEnabled(False)
            return

        row = selected[0].row()
        supp_id = self.payables_table.item(row, 0).data(Qt.UserRole)
        supp_name = self.payables_table.item(row, 0).text()

        self.supplier_breakup_lbl.setText(f"<b>Ledger breakup for Supplier: {supp_name}</b>")

        session = Session()
        try:
            supplier = session.query(Supplier).get(supp_id)
            if not supplier:
                return

            transactions = []

            # 1. Purchase Bills
            purchases = session.query(PurchaseMaster).filter_by(supplier_id=supp_id).all()
            for p in purchases:
                transactions.append({
                    "date": p.date,
                    "ref": p.invoice_number,
                    "desc": "Purchase Bill Billing",
                    "debit": p.paid_amount,
                    "credit": p.total_amount
                })

            # 2. Custom supplier payments (Payment Table)
            payments = session.query(Payment).filter_by(party_type='supplier', party_id=supp_id).all()
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

            self.supplier_breakup_table.setRowCount(len(transactions))
            running_balance = 0.0
            for i, tx in enumerate(transactions):
                running_balance += tx["credit"] - tx["debit"]
                
                self.supplier_breakup_table.setItem(i, 0, QTableWidgetItem(tx["date"].strftime("%Y-%m-%d")))
                ref_item = QTableWidgetItem(tx["ref"])
                if tx["ref"] != "OPENING":
                    font = ref_item.font()
                    font.setUnderline(True)
                    ref_item.setFont(font)
                    ref_item.setForeground(QColor("#6366f1"))
                self.supplier_breakup_table.setItem(i, 1, ref_item)
                self.supplier_breakup_table.setItem(i, 2, QTableWidgetItem(tx["desc"]))
                
                deb_item = QTableWidgetItem(f"₹{tx['debit']:,.2f}" if tx["debit"] > 0 else "-")
                if tx["debit"] > 0:
                    deb_item.setForeground(Qt.green)
                self.supplier_breakup_table.setItem(i, 3, deb_item)

                cred_item = QTableWidgetItem(f"₹{tx['credit']:,.2f}" if tx["credit"] > 0 else "-")
                if tx["credit"] > 0:
                    cred_item.setForeground(Qt.red)
                self.supplier_breakup_table.setItem(i, 4, cred_item)

                bal_item = QTableWidgetItem(f"₹{running_balance:,.2f}")
                self.supplier_breakup_table.setItem(i, 5, bal_item)

            self.supplier_total_payable_lbl.setText(f"Net Payable: ₹{running_balance:,.2f}")
            self.s_view_statement_btn.setEnabled(True)

        except Exception as e:
            print(f"Error loading supplier breakup: {e}")
        finally:
            session.close()

    def on_breakup_cell_clicked(self, row, column, is_supplier=False):
        if column != 1:  # Only reference column (Ref / Type) is clickable
            return

        table = self.supplier_breakup_table if is_supplier else self.customer_breakup_table
        item = table.item(row, column)
        if not item:
            return

        ref_text = item.text().strip()
        if not ref_text or ref_text == "OPENING":
            return

        main_window = self.window()
        session = Session()
        try:
            if is_supplier:
                purchase = session.query(PurchaseMaster).filter_by(invoice_number=ref_text).first()
                if purchase and hasattr(main_window, 'purchase_view'):
                    main_window.purchase_view.view_purchase_details(purchase.id)
            else:
                # 1. Check if it's a sales invoice
                sale = session.query(SalesMaster).filter_by(invoice_number=ref_text).first()
                if sale and hasattr(main_window, 'sales_view'):
                    main_window.sales_view.view_invoice_details(sale.id)
                    return

                # 2. Check if it's a repair job card
                job = session.query(ServiceJob).filter_by(job_number=ref_text).first()
                if job and hasattr(main_window, 'services_view'):
                    main_window.services_view.view_job_details(job.job_number)
                    return
        except Exception as e:
            print(f"Error opening reference details: {e}")
        finally:
            session.close()

    def view_customer_statement(self):
        selected = self.receivables_table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        cust_id = self.receivables_table.item(row, 0).data(Qt.UserRole)
        cust_name = self.receivables_table.item(row, 0).text()
        
        from ui.masters.ledger_dialog import LedgerBreakupDialog
        dlg = LedgerBreakupDialog(party_type='customer', party_id=cust_id, party_name=cust_name, parent=self)
        dlg.exec()

    def view_supplier_statement(self):
        selected = self.payables_table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        supp_id = self.payables_table.item(row, 0).data(Qt.UserRole)
        supp_name = self.payables_table.item(row, 0).text()
        
        from ui.masters.ledger_dialog import LedgerBreakupDialog
        dlg = LedgerBreakupDialog(party_type='supplier', party_id=supp_id, party_name=supp_name, parent=self)
        dlg.exec()

    def print_all_customer_outstanding(self):
        from database import Setting
        session = Session()
        try:
            s_name = session.query(Setting).filter_by(key='shop_name').first().value
            s_contact = session.query(Setting).filter_by(key='shop_contact').first().value
            s_address = session.query(Setting).filter_by(key='shop_address').first().value
            s_gst = session.query(Setting).filter_by(key='shop_gst').first().value

            customers = session.query(Customer).filter(Customer.outstanding_balance != 0).all()
            if not customers:
                QMessageBox.information(self, "No Outstanding", "There are no customer outstanding balances.")
                return

            items = []
            total_amount = 0.0
            for c in customers:
                items.append({
                    "name": c.name,
                    "mobile": c.mobile or "N/A",
                    "balance": c.outstanding_balance
                })
                total_amount += c.outstanding_balance

            report_data = {
                "shop_name": s_name,
                "shop_contact": s_contact,
                "shop_address": s_address,
                "shop_gst": s_gst,
                "date": datetime.date.today().strftime("%Y-%m-%d"),
                "party_type": 'customer',
                "items": items,
                "total_amount": total_amount
            }

            os.makedirs("statements", exist_ok=True)
            file_path = os.path.abspath("statements/all_customer_outstanding.pdf")

            from utils.pdf_generator import generate_outstanding_pdf
            generate_outstanding_pdf(report_data, file_path)

            try:
                os.startfile(file_path)
            except Exception as e:
                print(f"Could not auto-open PDF: {e}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate report: {e}")
        finally:
            session.close()

    def print_all_supplier_outstanding(self):
        from database import Setting
        session = Session()
        try:
            s_name = session.query(Setting).filter_by(key='shop_name').first().value
            s_contact = session.query(Setting).filter_by(key='shop_contact').first().value
            s_address = session.query(Setting).filter_by(key='shop_address').first().value
            s_gst = session.query(Setting).filter_by(key='shop_gst').first().value

            suppliers = session.query(Supplier).filter(Supplier.outstanding_balance != 0).all()
            if not suppliers:
                QMessageBox.information(self, "No Outstanding", "There are no supplier outstanding balances.")
                return

            items = []
            total_amount = 0.0
            for s in suppliers:
                items.append({
                    "name": s.name,
                    "mobile": s.mobile or "N/A",
                    "balance": s.outstanding_balance
                })
                total_amount += s.outstanding_balance

            report_data = {
                "shop_name": s_name,
                "shop_contact": s_contact,
                "shop_address": s_address,
                "shop_gst": s_gst,
                "date": datetime.date.today().strftime("%Y-%m-%d"),
                "party_type": 'supplier',
                "items": items,
                "total_amount": total_amount
            }

            os.makedirs("statements", exist_ok=True)
            file_path = os.path.abspath("statements/all_supplier_outstanding.pdf")

            from utils.pdf_generator import generate_outstanding_pdf
            generate_outstanding_pdf(report_data, file_path)

            try:
                os.startfile(file_path)
            except Exception as e:
                print(f"Could not auto-open PDF: {e}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate report: {e}")
        finally:
            session.close()

# Helper function
def func_sum(column):
    from sqlalchemy import func
    return func.sum(column)
