import datetime
import os
import pandas as pd
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QPushButton, QCheckBox, 
                             QMessageBox, QFileDialog, QTabWidget, QFrame, QFormLayout,
                             QComboBox, QDateEdit, QDoubleSpinBox, QDialog, QGridLayout,
                             QDialogButtonBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from database import Session
from sqlalchemy.orm import joinedload
from models import Product, Customer, Supplier, BankAccount, SalesMaster, SalesItem, PurchaseMaster, PurchaseItem, ServiceJob, ServicePart, CashTransaction, BankTransaction, Payment, SalesReturnMaster, SalesReturnItem, PurchaseReturnMaster, PurchaseReturnItem

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

        # Tab 2: Inventory Profitability Report
        self.pl_tab = QWidget()
        self.setup_inventory_profit_tab()
        self.tabs.addTab(self.pl_tab, "Inventory Profitability")

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

    def setup_inventory_profit_tab(self):
        from PySide6.QtWidgets import QGridLayout
        layout = QVBoxLayout(self.pl_tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # 1. Filters panel
        filter_frame = QFrame()
        filter_frame.setProperty("class", "CardFrame")
        filter_layout = QVBoxLayout(filter_frame)
        filter_layout.setContentsMargins(15, 15, 15, 15)
        filter_layout.setSpacing(10)

        filter_title = QLabel("<b>Report Search Filters</b>")
        filter_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #6366f1;")
        filter_layout.addWidget(filter_title)

        filters_grid = QHBoxLayout()
        filters_grid.setSpacing(10)

        # Date filter combo
        self.pl_date_filter_combo = QComboBox()
        self.pl_date_filter_combo.addItems(["All Time", "This Month", "This Year", "Custom Range"])
        self.pl_date_filter_combo.currentIndexChanged.connect(self.on_pl_date_filter_changed)
        
        # Custom dates
        self.pl_start_date = QDateEdit()
        self.pl_start_date.setCalendarPopup(True)
        self.pl_start_date.setDisplayFormat("yyyy-MM-dd")
        self.pl_start_date.setDate(datetime.date.today().replace(day=1))
        self.pl_start_date.dateChanged.connect(self.on_pl_custom_date_changed)
        
        self.pl_end_date = QDateEdit()
        self.pl_end_date.setCalendarPopup(True)
        self.pl_end_date.setDisplayFormat("yyyy-MM-dd")
        self.pl_end_date.setDate(datetime.date.today())
        self.pl_end_date.dateChanged.connect(self.on_pl_custom_date_changed)

        self.pl_start_label = QLabel("Start:")
        self.pl_end_label = QLabel("End:")
        
        # Hide custom date pickers initially
        self.pl_start_label.hide()
        self.pl_start_date.hide()
        self.pl_end_label.hide()
        self.pl_end_date.hide()

        # Category
        self.filter_category = QComboBox()
        self.filter_category.currentIndexChanged.connect(self.refresh_data)

        # Product
        self.filter_product = QComboBox()
        self.filter_product.currentIndexChanged.connect(self.refresh_data)

        # Supplier
        self.filter_supplier = QComboBox()
        self.filter_supplier.currentIndexChanged.connect(self.refresh_data)

        # Brand
        self.filter_brand = QComboBox()
        self.filter_brand.currentIndexChanged.connect(self.refresh_data)

        # Stock Status
        self.filter_stock_status = QComboBox()
        self.filter_stock_status.addItems(["All Items", "Sold Items Only", "Unsold Items Only"])
        self.filter_stock_status.currentIndexChanged.connect(self.refresh_data)

        # Interest Rate QDoubleSpinBox
        self.filter_interest_rate = QDoubleSpinBox()
        self.filter_interest_rate.setRange(0.0, 100.0)
        self.filter_interest_rate.setValue(18.0)
        self.filter_interest_rate.setSuffix(" %")
        self.filter_interest_rate.setDecimals(2)
        self.filter_interest_rate.valueChanged.connect(self.refresh_data)

        # Layout filters
        col1 = QVBoxLayout()
        col1.addWidget(QLabel("Date Range:"))
        col1.addWidget(self.pl_date_filter_combo)
        filters_grid.addLayout(col1, 2)

        self.custom_dates_layout = QHBoxLayout()
        self.custom_dates_layout.setSpacing(5)
        
        col_start = QVBoxLayout()
        col_start.addWidget(self.pl_start_label)
        col_start.addWidget(self.pl_start_date)
        
        col_end = QVBoxLayout()
        col_end.addWidget(self.pl_end_label)
        col_end.addWidget(self.pl_end_date)
        
        self.custom_dates_layout.addLayout(col_start)
        self.custom_dates_layout.addLayout(col_end)
        filters_grid.addLayout(self.custom_dates_layout, 2)

        col2 = QVBoxLayout()
        col2.addWidget(QLabel("Category:"))
        col2.addWidget(self.filter_category)
        filters_grid.addLayout(col2, 2)

        col3 = QVBoxLayout()
        col3.addWidget(QLabel("Product:"))
        col3.addWidget(self.filter_product)
        filters_grid.addLayout(col3, 2)

        col4 = QVBoxLayout()
        col4.addWidget(QLabel("Brand:"))
        col4.addWidget(self.filter_brand)
        filters_grid.addLayout(col4, 2)

        col5 = QVBoxLayout()
        col5.addWidget(QLabel("Supplier:"))
        col5.addWidget(self.filter_supplier)
        filters_grid.addLayout(col5, 2)

        col6 = QVBoxLayout()
        col6.addWidget(QLabel("Stock Status:"))
        col6.addWidget(self.filter_stock_status)
        filters_grid.addLayout(col6, 2)

        col7 = QVBoxLayout()
        col7.addWidget(QLabel("Interest Rate (p.a.):"))
        col7.addWidget(self.filter_interest_rate)
        filters_grid.addLayout(col7, 1.5)

        filter_layout.addLayout(filters_grid)
        layout.addWidget(filter_frame)

        # 2. Summary Dashboard & KPI Cards Panel
        summary_panel = QHBoxLayout()
        summary_panel.setSpacing(15)

        # KPI grid frame
        kpis_frame = QFrame()
        kpis_frame.setProperty("class", "CardFrame")
        kpis_grid = QGridLayout(kpis_frame)
        kpis_grid.setContentsMargins(15, 15, 15, 15)
        kpis_grid.setSpacing(12)

        def make_kpi_widget(title_text, val_lbl, color_str="#ffffff"):
            widget = QFrame()
            widget.setStyleSheet(f"background-color: #1e1e38; border: 1px solid #2c2c54; border-radius: 8px; padding: 10px;")
            w_layout = QVBoxLayout(widget)
            w_layout.setContentsMargins(8, 8, 8, 8)
            w_layout.setSpacing(4)
            t_lbl = QLabel(title_text)
            t_lbl.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: bold; text-transform: uppercase;")
            val_lbl.setStyleSheet(f"color: {color_str}; font-size: 16px; font-weight: bold;")
            w_layout.addWidget(t_lbl)
            w_layout.addWidget(val_lbl)
            return widget

        self.kpi_purchase_val = QLabel("₹0.00")
        self.kpi_sales_val = QLabel("₹0.00")
        self.kpi_gross_profit = QLabel("₹0.00")
        self.kpi_interest_cost = QLabel("₹0.00")
        self.kpi_net_profit = QLabel("₹0.00")
        self.kpi_avg_days = QLabel("0 Days")

        kpis_grid.addWidget(make_kpi_widget("Total Purchase Value", self.kpi_purchase_val, "#ffffff"), 0, 0)
        kpis_grid.addWidget(make_kpi_widget("Total Sales Value", self.kpi_sales_val, "#ffffff"), 0, 1)
        kpis_grid.addWidget(make_kpi_widget("Total Gross Profit", self.kpi_gross_profit, "#10b981"), 0, 2)
        kpis_grid.addWidget(make_kpi_widget("Total Interest Cost", self.kpi_interest_cost, "#ef4444"), 1, 0)
        kpis_grid.addWidget(make_kpi_widget("Total Net Profit", self.kpi_net_profit, "#6366f1"), 1, 1)
        kpis_grid.addWidget(make_kpi_widget("Average Days in Stock", self.kpi_avg_days, "#3b82f6"), 1, 2)

        summary_panel.addWidget(kpis_frame, 2)

        # Fast/Slow Moving Panel
        moving_frame = QFrame()
        moving_frame.setProperty("class", "CardFrame")
        moving_layout = QHBoxLayout(moving_frame)
        moving_layout.setContentsMargins(15, 15, 15, 15)
        moving_layout.setSpacing(15)

        fast_col = QVBoxLayout()
        fast_title = QLabel("<b>Fast Moving (Top 3)</b>")
        fast_title.setStyleSheet("color: #10b981; font-weight: bold; font-size: 11px;")
        self.fast_moving_list = QLabel("No sales records.")
        self.fast_moving_list.setStyleSheet("color: #e2e8f0; font-size: 11px; line-height: 1.4;")
        self.fast_moving_list.setWordWrap(True)
        fast_col.addWidget(fast_title)
        fast_col.addWidget(self.fast_moving_list)
        fast_col.addStretch()

        slow_col = QVBoxLayout()
        slow_title = QLabel("<b>Slow Moving (Top 3)</b>")
        slow_title.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 11px;")
        self.slow_moving_list = QLabel("No stock records.")
        self.slow_moving_list.setStyleSheet("color: #e2e8f0; font-size: 11px; line-height: 1.4;")
        self.slow_moving_list.setWordWrap(True)
        slow_col.addWidget(slow_title)
        slow_col.addWidget(self.slow_moving_list)
        slow_col.addStretch()

        moving_layout.addLayout(fast_col, 1)
        moving_layout.addLayout(slow_col, 1)

        summary_panel.addWidget(moving_frame, 1)
        layout.addLayout(summary_panel)

        # 3. Detailed Data Table (PDF Style statement layout)
        table_title = QLabel("<b>Detailed Inventory Holding & Profit Statement</b>")
        table_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #ffffff; margin-top: 5px;")
        layout.addWidget(table_title)

        self.profit_table = QTableWidget()
        self.profit_table.setColumnCount(11)
        self.profit_table.setHorizontalHeaderLabels([
            "Product Code", "Product Name", "Purchase Date", "Sale Date", 
            "Days in Stock", "Qty", "Pur. Price (₹)", "Sale Price (₹)", 
            "Gross Profit (₹)", "Interest Cost (₹)", "Net Profit (₹)"
        ])
        self.profit_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.profit_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.profit_table.verticalHeader().setVisible(False)
        self.profit_table.cellDoubleClicked.connect(self.on_table_cell_double_clicked)
        layout.addWidget(self.profit_table)

        # 4. Action bar for exporting
        action_bar = QHBoxLayout()
        action_bar.setSpacing(15)

        self.btn_export_pdf = QPushButton("Export to PDF Report")
        self.btn_export_pdf.setProperty("class", "btn-action-view")
        self.btn_export_pdf.setStyleSheet("font-size: 13px; padding: 8px 16px;")
        self.btn_export_pdf.clicked.connect(self.export_profitability_pdf)

        self.btn_export_excel = QPushButton("Export to Excel Sheet")
        self.btn_export_excel.setProperty("class", "btn-success")
        self.btn_export_excel.setStyleSheet("font-size: 13px; padding: 8px 16px;")
        self.btn_export_excel.clicked.connect(self.export_profitability_excel)

        self.btn_print_preview = QPushButton("Print Preview Report")
        self.btn_print_preview.setProperty("class", "btn-action-print")
        self.btn_print_preview.setStyleSheet("font-size: 13px; padding: 8px 16px;")
        self.btn_print_preview.clicked.connect(self.export_profitability_pdf)

        action_bar.addWidget(self.btn_export_pdf)
        action_bar.addWidget(self.btn_export_excel)
        action_bar.addWidget(self.btn_print_preview)
        action_bar.addStretch()

        layout.addLayout(action_bar)

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

    def on_table_cell_double_clicked(self, row, column):
        item = self.profit_table.item(row, 0)
        if item:
            product_id = item.data(Qt.UserRole)
            if product_id:
                rate = self.filter_interest_rate.value()
                dlg = ProductDrillDownDialog(product_id, rate, self)
                dlg.exec()

    def populate_filter_dropdowns(self):
        session = Session()
        try:
            # Save current selections
            curr_cat = self.filter_category.currentText()
            curr_prod = self.filter_product.currentText()
            curr_supp = self.filter_supplier.currentText()
            curr_brand = self.filter_brand.currentText()
            
            # Block signals
            self.filter_category.blockSignals(True)
            self.filter_product.blockSignals(True)
            self.filter_supplier.blockSignals(True)
            self.filter_brand.blockSignals(True)
            
            # Populate Categories
            self.filter_category.clear()
            self.filter_category.addItem("-- All Categories --")
            from models import Category
            for c in session.query(Category).all():
                self.filter_category.addItem(c.name)
                
            # Populate Products
            self.filter_product.clear()
            self.filter_product.addItem("-- All Products --")
            for p in session.query(Product).order_by(Product.name.asc()).all():
                self.filter_product.addItem(p.name)
                
            # Populate Suppliers
            self.filter_supplier.clear()
            self.filter_supplier.addItem("-- All Suppliers --")
            for s in session.query(Supplier).order_by(Supplier.name.asc()).all():
                self.filter_supplier.addItem(s.name)
                
            # Populate Brands
            self.filter_brand.clear()
            self.filter_brand.addItem("-- All Brands --")
            brands = session.query(Product.brand).distinct().all()
            for b in brands:
                if b[0]:
                    self.filter_brand.addItem(b[0])
                    
            # Restore selections if valid
            idx = self.filter_category.findText(curr_cat)
            if idx >= 0: self.filter_category.setCurrentIndex(idx)
            
            idx = self.filter_product.findText(curr_prod)
            if idx >= 0: self.filter_product.setCurrentIndex(idx)
            
            idx = self.filter_supplier.findText(curr_supp)
            if idx >= 0: self.filter_supplier.setCurrentIndex(idx)
            
            idx = self.filter_brand.findText(curr_brand)
            if idx >= 0: self.filter_brand.setCurrentIndex(idx)
            
        except Exception as e:
            print(f"Error populating filters: {e}")
        finally:
            self.filter_category.blockSignals(False)
            self.filter_product.blockSignals(False)
            self.filter_supplier.blockSignals(False)
            self.filter_brand.blockSignals(False)
            session.close()

    def export_profitability_pdf(self):
        if not hasattr(self, 'profit_rows') or not self.profit_rows:
            QMessageBox.warning(self, "No Data", "There is no data to export.")
            return
            
        session = Session()
        try:
            from database import Setting
            s_name = session.query(Setting).filter_by(key='shop_name').first()
            s_contact = session.query(Setting).filter_by(key='shop_contact').first()
            s_address = session.query(Setting).filter_by(key='shop_address').first()
            s_gst = session.query(Setting).filter_by(key='shop_gst').first()
            
            shop_name = s_name.value if s_name else "SUN COMPUTERS,"
            shop_contact = s_contact.value if s_contact else "N/A"
            shop_address = s_address.value if s_address else "N/A"
            shop_gst = s_gst.value if s_gst else "N/A"
            
            report_data = {
                "shop_name": shop_name,
                "shop_contact": shop_contact,
                "shop_address": shop_address,
                "shop_gst": shop_gst,
                "date": datetime.date.today().strftime("%Y-%m-%d"),
                "date_range": self.pl_date_range_str,
                "total_purchase_value": self.tot_purchase_val,
                "total_sales_value": self.tot_sales_val,
                "total_gross_profit": self.tot_gross_profit,
                "total_interest_cost": self.tot_interest_cost,
                "total_net_profit": self.tot_net_profit,
                "avg_days": self.avg_days,
                "items": self.profit_rows
            }
            
            os.makedirs("statements", exist_ok=True)
            path = os.path.abspath("statements/inventory_profit_report.pdf")
            from utils.pdf_generator import generate_inventory_profit_pdf
            generate_inventory_profit_pdf(report_data, path)
            
            QMessageBox.information(self, "Success", f"Inventory Profitability Report PDF generated successfully at:\n{path}")
            try:
                os.startfile(path)
            except Exception as e:
                print(f"Could not open PDF: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate PDF: {e}")
        finally:
            session.close()

    def export_profitability_excel(self):
        if not hasattr(self, 'profit_rows') or not self.profit_rows:
            QMessageBox.warning(self, "No Data", "There is no data to export.")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Excel Report", "", "Excel Files (*.xlsx)")
        if file_path:
            try:
                data = []
                for row in self.profit_rows:
                    pdate = row["purchase_date"].strftime("%Y-%m-%d") if isinstance(row["purchase_date"], datetime.date) else str(row["purchase_date"])
                    sdate = row["sale_date"].strftime("%Y-%m-%d") if isinstance(row["sale_date"], datetime.date) else str(row["sale_date"])
                    data.append({
                        "Product Code": row["product_code"] or "N/A",
                        "Product Name": row["product_name"],
                        "Purchase Date": pdate,
                        "Sale Date": sdate,
                        "Days in Stock": row["days"],
                        "Qty": row["qty"],
                        "Purchase Price (INR)": row["purchase_price"],
                        "Sale Price (INR)": row["sale_price"],
                        "Gross Profit (INR)": row["gross_profit"],
                        "Interest Cost (INR)": row["interest_cost"],
                        "Net Profit (INR)": row["net_profit"]
                    })
                
                summary_data = {
                    "Metric": [
                        "Total Purchase Value", "Total Sales Value", "Total Gross Profit", 
                        "Total Interest Cost", "Total Net Profit", "Average Days in Stock"
                    ],
                    "Value": [
                        self.tot_purchase_val, self.tot_sales_val, self.tot_gross_profit, 
                        self.tot_interest_cost, self.tot_net_profit, self.avg_days
                    ]
                }
                
                with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                    pd.DataFrame(data).to_excel(writer, sheet_name="Detailed Profit Analysis", index=False)
                    pd.DataFrame(summary_data).to_excel(writer, sheet_name="Summary Stats", index=False)
                
                QMessageBox.information(self, "Success", "Excel report exported successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export Excel: {e}")

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

            # 3. Populate Profitability Report
            if hasattr(self, 'pl_date_filter_combo'):
                # 3.1 Populate filter dropdowns if they are empty
                if self.filter_category.count() <= 1:
                    self.populate_filter_dropdowns()
                
                # Determine filters
                category_filter = self.filter_category.currentText()
                product_filter = self.filter_product.currentText()
                supplier_filter = self.filter_supplier.currentText()
                brand_filter = self.filter_brand.currentText()
                stock_status_filter = self.filter_stock_status.currentText()
                interest_rate = self.filter_interest_rate.value()

                # Determine date range
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

                # Set date range text for report
                if filter_text == "All Time":
                    self.pl_date_range_str = "All Time"
                elif filter_text == "Custom Range":
                    self.pl_date_range_str = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
                else:
                    self.pl_date_range_str = filter_text

                # Build products list based on category/product/brand filter
                prod_query = session.query(Product)
                if category_filter != "-- All Categories --":
                    prod_query = prod_query.filter(Product.category == category_filter)
                if product_filter != "-- All Products --":
                    prod_query = prod_query.filter(Product.name == product_filter)
                if brand_filter != "-- All Brands --":
                    prod_query = prod_query.filter(Product.brand == brand_filter)
                products = prod_query.all()

                all_analysis_rows = []
                for p in products:
                    # Fetch purchases
                    purchases = session.query(
                        PurchaseItem.qty,
                        PurchaseItem.rate,
                        PurchaseMaster.date,
                        Supplier.name,
                        PurchaseMaster.id.label('purchase_id')
                    ).select_from(PurchaseItem).join(PurchaseMaster).join(Supplier).filter(PurchaseItem.product_id == p.id).order_by(PurchaseMaster.date.asc(), PurchaseItem.id.asc()).all()

                    purchase_returns = session.query(
                        PurchaseReturnItem.qty,
                        PurchaseReturnMaster.purchase_id
                    ).join(PurchaseReturnMaster).filter(PurchaseReturnItem.product_id == p.id).all()

                    pur_ret_map = {}
                    for pr in purchase_returns:
                        pur_ret_map[pr.purchase_id] = pur_ret_map.get(pr.purchase_id, 0) + pr.qty

                    pur_lots = []
                    for pur in purchases:
                        ret_qty = pur_ret_map.get(pur.purchase_id, 0)
                        available_qty = pur.qty
                        if ret_qty > 0:
                            deducted = min(available_qty, ret_qty)
                            available_qty -= deducted
                            pur_ret_map[pur.purchase_id] -= deducted
                        if available_qty > 0:
                            pur_lots.append({
                                "qty": available_qty,
                                "price": pur.rate,
                                "date": pur.date,
                                "supplier": pur.name,
                                "purchase_id": pur.purchase_id
                            })

                    # Fetch sales
                    sales = session.query(
                        SalesItem.qty,
                        SalesItem.rate,
                        SalesItem.discount,
                        SalesMaster.date,
                        SalesMaster.id.label('sales_id')
                    ).select_from(SalesItem).join(SalesMaster).filter(SalesItem.product_id == p.id).order_by(SalesMaster.date.asc(), SalesItem.id.asc()).all()

                    sales_returns = session.query(
                        SalesReturnItem.qty,
                        SalesReturnMaster.sales_id
                    ).join(SalesReturnMaster).filter(SalesReturnItem.product_id == p.id).all()

                    sales_ret_map = {}
                    for sr in sales_returns:
                        sales_ret_map[sr.sales_id] = sales_ret_map.get(sr.sales_id, 0) + sr.qty

                    sale_lots = []
                    for s in sales:
                        ret_qty = sales_ret_map.get(s.sales_id, 0)
                        available_qty = s.qty
                        if ret_qty > 0:
                            deducted = min(available_qty, ret_qty)
                            available_qty -= deducted
                            sales_ret_map[s.sales_id] -= deducted
                        if available_qty > 0:
                            net_rate = s.rate - (s.discount / s.qty) if s.qty > 0 else s.rate
                            sale_lots.append({
                                "qty": available_qty,
                                "price": net_rate,
                                "date": s.date,
                                "sales_id": s.sales_id
                            })

                    # FIFO Matching
                    matched_rows = []
                    pur_idx = 0
                    sale_idx = 0
                    for lot in pur_lots:
                        lot["remaining"] = lot["qty"]
                    for slot in sale_lots:
                        slot["remaining"] = slot["qty"]

                    while sale_idx < len(sale_lots):
                        slot = sale_lots[sale_idx]
                        if slot["remaining"] <= 0:
                            sale_idx += 1
                            continue
                        if pur_idx >= len(pur_lots):
                            qty_to_match = slot["remaining"]
                            matched_rows.append({
                                "product_code": p.product_code, "product_name": p.name, "product_id": p.id,
                                "brand": p.brand, "category": p.category, "purchase_date": slot["date"],
                                "sale_date": slot["date"], "days": 0, "qty": qty_to_match,
                                "purchase_price": p.purchase_price, "sale_price": slot["price"],
                                "supplier": "N/A", "status": "sold"
                            })
                            slot["remaining"] = 0
                            sale_idx += 1
                            continue

                        lot = pur_lots[pur_idx]
                        if lot["remaining"] <= 0:
                            pur_idx += 1
                            continue

                        qty_to_match = min(lot["remaining"], slot["remaining"])
                        days = (slot["date"] - lot["date"]).days
                        matched_rows.append({
                            "product_code": p.product_code, "product_name": p.name, "product_id": p.id,
                            "brand": p.brand, "category": p.category, "purchase_date": lot["date"],
                            "sale_date": slot["date"], "days": max(0, days), "qty": qty_to_match,
                            "purchase_price": lot["price"], "sale_price": slot["price"],
                            "supplier": lot["supplier"], "status": "sold"
                        })
                        lot["remaining"] -= qty_to_match
                        slot["remaining"] -= qty_to_match

                    for lot in pur_lots:
                        if lot["remaining"] > 0:
                            days = (today - lot["date"]).days
                            matched_rows.append({
                                "product_code": p.product_code, "product_name": p.name, "product_id": p.id,
                                "brand": p.brand, "category": p.category, "purchase_date": lot["date"],
                                "sale_date": "Unsold Inventory", "days": max(0, days), "qty": lot["remaining"],
                                "purchase_price": lot["price"], "sale_price": 0.0,
                                "supplier": lot["supplier"], "status": "unsold"
                            })

                    # Perform cost/profit calculations
                    for row in matched_rows:
                        q = row["qty"]
                        pur_price = row["purchase_price"]
                        sale_price = row["sale_price"]
                        d = row["days"]
                        
                        if row["status"] == "sold":
                            gp = (sale_price - pur_price) * q
                        else:
                            gp = 0.0
                            
                        interest = (pur_price * interest_rate * d) / 36500.0 * q
                        net = gp - interest
                        
                        row["gross_profit"] = gp
                        row["interest_cost"] = interest
                        row["net_profit"] = net
                        
                        all_analysis_rows.append(row)

                # Filter the rows based on remaining dropdown and date range filters
                self.profit_rows = []
                for row in all_analysis_rows:
                    if supplier_filter != "-- All Suppliers --" and row["supplier"] != supplier_filter:
                        continue
                    if stock_status_filter == "Sold Items Only" and row["status"] != "sold":
                        continue
                    if stock_status_filter == "Unsold Items Only" and row["status"] != "unsold":
                        continue

                    # Date filters
                    if row["status"] == "sold":
                        sdate = row["sale_date"]
                        if start_date and sdate < start_date:
                            continue
                        if end_date and sdate > end_date:
                            continue
                    else: # unsold
                        pdate = row["purchase_date"]
                        if start_date and pdate < start_date:
                            continue
                        if end_date and pdate > end_date:
                            continue

                    self.profit_rows.append(row)

                # Sort by purchase date descending to show latest purchases first
                self.profit_rows.sort(key=lambda x: x["purchase_date"], reverse=True)

                # Compute Summary KPIs
                self.tot_purchase_val = 0.0
                self.tot_sales_val = 0.0
                self.tot_gross_profit = 0.0
                self.tot_interest_cost = 0.0
                self.tot_net_profit = 0.0
                tot_days = 0
                tot_qty = 0

                for r in self.profit_rows:
                    q = r["qty"]
                    self.tot_purchase_val += r["purchase_price"] * q
                    self.tot_sales_val += r["sale_price"] * q
                    self.tot_gross_profit += r["gross_profit"]
                    self.tot_interest_cost += r["interest_cost"]
                    self.tot_net_profit += r["net_profit"]
                    tot_days += r["days"] * q
                    tot_qty += q

                self.avg_days = tot_days / tot_qty if tot_qty > 0 else 0.0

                # Set KPI labels text
                self.kpi_purchase_val.setText(f"₹{self.tot_purchase_val:,.2f}")
                self.kpi_sales_val.setText(f"₹{self.tot_sales_val:,.2f}")
                self.kpi_gross_profit.setText(f"₹{self.tot_gross_profit:,.2f}")
                self.kpi_interest_cost.setText(f"₹{self.tot_interest_cost:,.2f}")
                self.kpi_net_profit.setText(f"₹{self.tot_net_profit:,.2f}")
                self.kpi_avg_days.setText(f"{self.avg_days:.1f} Days")

                # Compute Fast & Slow Moving top 3
                prod_stats = {}
                for r in self.profit_rows:
                    pid = r["product_id"]
                    if pid not in prod_stats:
                        prod_stats[pid] = {
                            "name": r["product_name"], "code": r["product_code"],
                            "sold_qty": 0, "sold_days": 0.0, "total_qty": 0, "total_days": 0.0
                        }
                    q = r["qty"]
                    d = r["days"]
                    prod_stats[pid]["total_qty"] += q
                    prod_stats[pid]["total_days"] += d * q
                    if r["status"] == "sold":
                        prod_stats[pid]["sold_qty"] += q
                        prod_stats[pid]["sold_days"] += d * q

                fast_list = []
                slow_list = []
                for stats in prod_stats.values():
                    name_desc = f"{stats['name']} [{stats['code']}]"
                    if stats["sold_qty"] > 0:
                        avg_sold = stats["sold_days"] / stats["sold_qty"]
                        fast_list.append((name_desc, avg_sold))
                    
                    avg_total = stats["total_days"] / stats["total_qty"] if stats["total_qty"] > 0 else 0.0
                    slow_list.append((name_desc, avg_total))

                fast_list.sort(key=lambda x: x[1]) # shortest first
                slow_list.sort(key=lambda x: x[1], reverse=True) # longest first

                fast_text = "\n".join([f"• {x[0]} ({x[1]:.1f} d)" for x in fast_list[:3]]) if fast_list else "No sales records."
                slow_text = "\n".join([f"• {x[0]} ({x[1]:.1f} d)" for x in slow_list[:3]]) if slow_list else "No stock records."

                self.fast_moving_list.setText(fast_text)
                self.slow_moving_list.setText(slow_text)

                # Populate main Detailed Table
                self.profit_table.setRowCount(len(self.profit_rows))
                for i, r in enumerate(self.profit_rows):
                    pdate_str = r["purchase_date"].strftime("%Y-%m-%d") if isinstance(r["purchase_date"], datetime.date) else str(r["purchase_date"])
                    sdate_str = r["sale_date"].strftime("%Y-%m-%d") if isinstance(r["sale_date"], datetime.date) else str(r["sale_date"])
                    
                    code_item = QTableWidgetItem(r["product_code"] or "N/A")
                    code_item.setData(Qt.UserRole, r["product_id"])
                    
                    self.profit_table.setItem(i, 0, code_item)
                    self.profit_table.setItem(i, 1, QTableWidgetItem(r["product_name"]))
                    self.profit_table.setItem(i, 2, QTableWidgetItem(pdate_str))
                    
                    sdate_item = QTableWidgetItem(sdate_str)
                    if r["status"] == "unsold":
                        sdate_item.setForeground(QColor("#ef4444"))
                    self.profit_table.setItem(i, 3, sdate_item)
                    
                    self.profit_table.setItem(i, 4, QTableWidgetItem(str(r["days"])))
                    self.profit_table.setItem(i, 5, QTableWidgetItem(str(r["qty"])))
                    self.profit_table.setItem(i, 6, QTableWidgetItem(f"{r['purchase_price']:.2f}"))
                    self.profit_table.setItem(i, 7, QTableWidgetItem(f"{r['sale_price']:.2f}"))
                    self.profit_table.setItem(i, 8, QTableWidgetItem(f"{r['gross_profit']:.2f}"))
                    self.profit_table.setItem(i, 9, QTableWidgetItem(f"{r['interest_cost']:.2f}"))
                    
                    net_item = QTableWidgetItem(f"{r['net_profit']:.2f}")
                    if r["net_profit"] < 0:
                        net_item.setForeground(QColor("#ef4444"))
                    else:
                        net_item.setForeground(QColor("#10b981"))
                    self.profit_table.setItem(i, 10, net_item)

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
            os.path.abspath("ReportSuite.xlsx"), 
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
                        "Product Code": p.product_code or "N/A",
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

                    # Sales Returns
                    sr_masters = session.query(SalesReturnMaster).all()
                    sr_data = [{
                        "Return Number": sr.return_number,
                        "Date": sr.date.strftime("%Y-%m-%d"),
                        "Customer Name": sr.customer.name,
                        "Customer Contact": sr.customer.mobile,
                        "Total Amount (₹)": sr.total_amount,
                        "Refund Paid (₹)": sr.refund_amount,
                        "Balance Adjusted (₹)": sr.balance_deducted,
                        "Ref Invoice": sr.sales.invoice_number if sr.sales else "N/A"
                    } for sr in sr_masters]
                    pd.DataFrame(sr_data).to_excel(writer, sheet_name="Sales Returns", index=False)

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

                    # Purchase Returns
                    pr_masters = session.query(PurchaseReturnMaster).all()
                    pr_data = [{
                        "Return Number": pr.return_number,
                        "Date": pr.date.strftime("%Y-%m-%d"),
                        "Supplier Name": pr.supplier.name,
                        "Supplier Contact": pr.supplier.mobile,
                        "Total Amount (₹)": pr.total_amount,
                        "Refund Received (₹)": pr.refund_received,
                        "Balance Adjusted (₹)": pr.balance_deducted,
                        "Ref Bill": pr.purchase.invoice_number if pr.purchase else "N/A"
                    } for pr in pr_masters]
                    pd.DataFrame(pr_data).to_excel(writer, sheet_name="Purchase Returns", index=False)

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

            # 4. Sales Returns
            returns = session.query(SalesReturnMaster).filter_by(customer_id=cust_id).all()
            for r in returns:
                desc_text = "Sales Return"
                if r.sales_id and r.sales:
                    desc_text += f" against invoice {r.sales.invoice_number}"
                transactions.append({
                    "date": r.date,
                    "ref": r.return_number,
                    "desc": desc_text,
                    "debit": r.refund_amount,
                    "credit": r.total_amount
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

            # 3. Purchase Returns
            returns = session.query(PurchaseReturnMaster).filter_by(supplier_id=supp_id).all()
            for r in returns:
                desc_text = "Purchase Return"
                if r.purchase_id and r.purchase:
                    desc_text += f" against bill {r.purchase.invoice_number}"
                transactions.append({
                    "date": r.date,
                    "ref": r.return_number,
                    "desc": desc_text,
                    "debit": r.total_amount,
                    "credit": r.refund_received
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
                if ref_text.startswith("PR-"):
                    ret = session.query(PurchaseReturnMaster).filter_by(return_number=ref_text).first()
                    if ret and hasattr(main_window, 'purchase_view') and hasattr(main_window.purchase_view, 'return_history_tab'):
                        main_window.purchase_view.return_history_tab.view_details(ret.id)
                        return
                purchase = session.query(PurchaseMaster).filter_by(invoice_number=ref_text).first()
                if purchase and hasattr(main_window, 'purchase_view'):
                    main_window.purchase_view.view_purchase_details(purchase.id)
            else:
                if ref_text.startswith("SR-"):
                    ret = session.query(SalesReturnMaster).filter_by(return_number=ref_text).first()
                    if ret and hasattr(main_window, 'sales_view') and hasattr(main_window.sales_view, 'return_history_tab'):
                        main_window.sales_view.return_history_tab.view_details(ret.id)
                        return
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


class ProductDrillDownDialog(QDialog):
    def __init__(self, product_id, interest_rate, parent=None):
        super().__init__(parent)
        self.product_id = product_id
        self.interest_rate = interest_rate
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Product Profitability & Investment Drill-Down")
        self.resize(950, 650)
        self.setStyleSheet("""
            QDialog {
                background-color: #12121e;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QTableWidget {
                background-color: #1e1e2f;
                gridline-color: #2b2b40;
                color: #ffffff;
                border: 1px solid #2b2b40;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #2b2b40;
                color: #ffffff;
                padding: 6px;
                border: 1px solid #1e1e2f;
                font-weight: bold;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title Label
        self.title_label = QLabel("<b>Product Performance Details</b>")
        self.title_label.setStyleSheet("font-size: 16px; color: #6366f1; font-weight: bold;")
        layout.addWidget(self.title_label)

        # 1. KPI cards layout
        kpi_layout = QGridLayout()
        kpi_layout.setSpacing(12)

        def make_kpi_card(title, value_lbl, text_color="#ffffff"):
            card = QFrame()
            card.setStyleSheet("background-color: #1e1e35; border: 1px solid #2c2c50; border-radius: 8px; padding: 10px;")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(8, 8, 8, 8)
            card_layout.setSpacing(4)
            lbl_title = QLabel(title)
            lbl_title.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: bold; text-transform: uppercase;")
            value_lbl.setStyleSheet(f"color: {text_color}; font-size: 16px; font-weight: bold;")
            card_layout.addWidget(lbl_title)
            card_layout.addWidget(value_lbl)
            return card

        self.kpi_stock = QLabel("0")
        self.kpi_avg_days = QLabel("0 Days")
        self.kpi_profit = QLabel("₹0.00")
        self.kpi_interest = QLabel("₹0.00")
        self.kpi_net = QLabel("₹0.00")

        kpi_layout.addWidget(make_kpi_card("Current Stock", self.kpi_stock, "#ffffff"), 0, 0)
        kpi_layout.addWidget(make_kpi_card("Avg Days in Stock", self.kpi_avg_days, "#3b82f6"), 0, 1)
        kpi_layout.addWidget(make_kpi_card("Total Profit Generated", self.kpi_profit, "#10b981"), 0, 2)
        kpi_layout.addWidget(make_kpi_card("Total Interest Cost", self.kpi_interest, "#ef4444"), 0, 3)
        kpi_layout.addWidget(make_kpi_card("Net Contribution", self.kpi_net, "#6366f1"), 0, 4)

        layout.addLayout(kpi_layout)

        # 2. Tabs for histories
        self.history_tabs = QTabWidget()
        
        # Purchases tab
        self.purchases_tab = QWidget()
        pur_tab_layout = QVBoxLayout(self.purchases_tab)
        pur_tab_layout.setContentsMargins(5, 10, 5, 5)
        self.purchase_table = QTableWidget()
        self.purchase_table.setColumnCount(6)
        self.purchase_table.setHorizontalHeaderLabels(["Invoice #", "Date", "Supplier", "Qty", "Rate (₹)", "Total (₹)"])
        self.purchase_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.purchase_table.verticalHeader().setVisible(False)
        pur_tab_layout.addWidget(self.purchase_table)
        self.history_tabs.addTab(self.purchases_tab, "Purchase Lot History")

        # Sales tab
        self.sales_tab = QWidget()
        sales_tab_layout = QVBoxLayout(self.sales_tab)
        sales_tab_layout.setContentsMargins(5, 10, 5, 5)
        self.sales_table = QTableWidget()
        self.sales_table.setColumnCount(7)
        self.sales_table.setHorizontalHeaderLabels(["Invoice #", "Date", "Customer", "Qty", "Rate (₹)", "Discount (₹)", "Total (₹)"])
        self.sales_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.sales_table.verticalHeader().setVisible(False)
        sales_tab_layout.addWidget(self.sales_table)
        self.history_tabs.addTab(self.sales_tab, "Sales History")

        layout.addWidget(self.history_tabs)

        # Close button
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok)
        btn_box.accepted.connect(self.accept)
        layout.addWidget(btn_box)

        self.load_data()

    def load_data(self):
        import traceback
        session = Session()
        try:
            product = session.query(Product).get(self.product_id)
            if not product:
                self.title_label.setText("Product Not Found")
                return

            self.title_label.setText(f"<b>{product.name} [{product.product_code or 'N/A'}]</b> - Category: {product.category} | Brand: {product.brand}")

            # 1. FIFO calculations for this product to get summary statistics
            purchases = session.query(
                PurchaseItem.qty,
                PurchaseItem.rate,
                PurchaseMaster.date,
                Supplier.name,
                PurchaseMaster.id.label('purchase_id')
            ).select_from(PurchaseItem).join(PurchaseMaster).join(Supplier).filter(PurchaseItem.product_id == product.id).order_by(PurchaseMaster.date.asc(), PurchaseItem.id.asc()).all()

            purchase_returns = session.query(
                PurchaseReturnItem.qty,
                PurchaseReturnMaster.purchase_id
            ).join(PurchaseReturnMaster).filter(PurchaseReturnItem.product_id == product.id).all()

            pur_ret_map = {}
            for pr in purchase_returns:
                pur_ret_map[pr.purchase_id] = pur_ret_map.get(pr.purchase_id, 0) + pr.qty

            pur_lots = []
            for pur in purchases:
                ret_qty = pur_ret_map.get(pur.purchase_id, 0)
                available_qty = pur.qty
                if ret_qty > 0:
                    deducted = min(available_qty, ret_qty)
                    available_qty -= deducted
                    pur_ret_map[pur.purchase_id] -= deducted
                if available_qty > 0:
                    pur_lots.append({
                        "qty": available_qty,
                        "price": pur.rate,
                        "date": pur.date,
                        "supplier": pur.name,
                        "purchase_id": pur.purchase_id
                    })

            sales = session.query(
                SalesItem.qty,
                SalesItem.rate,
                SalesItem.discount,
                SalesMaster.date,
                SalesMaster.id.label('sales_id')
            ).select_from(SalesItem).join(SalesMaster).filter(SalesItem.product_id == product.id).order_by(SalesMaster.date.asc(), SalesItem.id.asc()).all()

            sales_returns = session.query(
                SalesReturnItem.qty,
                SalesReturnMaster.sales_id
            ).join(SalesReturnMaster).filter(SalesReturnItem.product_id == product.id).all()

            sales_ret_map = {}
            for sr in sales_returns:
                sales_ret_map[sr.sales_id] = sales_ret_map.get(sr.sales_id, 0) + sr.qty

            sale_lots = []
            for s in sales:
                ret_qty = sales_ret_map.get(s.sales_id, 0)
                available_qty = s.qty
                if ret_qty > 0:
                    deducted = min(available_qty, ret_qty)
                    available_qty -= deducted
                    sales_ret_map[s.sales_id] -= deducted
                if available_qty > 0:
                    net_rate = s.rate - (s.discount / s.qty) if s.qty > 0 else s.rate
                    sale_lots.append({
                        "qty": available_qty,
                        "price": net_rate,
                        "date": s.date,
                        "sales_id": s.sales_id
                    })

            matched_rows = []
            pur_idx = 0
            sale_idx = 0
            for lot in pur_lots:
                lot["remaining"] = lot["qty"]
            for slot in sale_lots:
                slot["remaining"] = slot["qty"]

            today = datetime.date.today()

            while sale_idx < len(sale_lots):
                slot = sale_lots[sale_idx]
                if slot["remaining"] <= 0:
                    sale_idx += 1
                    continue
                if pur_idx >= len(pur_lots):
                    qty_to_match = slot["remaining"]
                    matched_rows.append({
                        "days": 0, "qty": qty_to_match,
                        "purchase_price": product.purchase_price, "sale_price": slot["price"],
                        "status": "sold"
                    })
                    slot["remaining"] = 0
                    sale_idx += 1
                    continue

                lot = pur_lots[pur_idx]
                if lot["remaining"] <= 0:
                    pur_idx += 1
                    continue

                qty_to_match = min(lot["remaining"], slot["remaining"])
                days = (slot["date"] - lot["date"]).days
                matched_rows.append({
                    "days": max(0, days), "qty": qty_to_match,
                    "purchase_price": lot["price"], "sale_price": slot["price"],
                    "status": "sold"
                })
                lot["remaining"] -= qty_to_match
                slot["remaining"] -= qty_to_match

            for lot in pur_lots:
                if lot["remaining"] > 0:
                    days = (today - lot["date"]).days
                    matched_rows.append({
                        "days": max(0, days), "qty": lot["remaining"],
                        "purchase_price": lot["price"], "sale_price": 0.0,
                        "status": "unsold"
                    })

            tot_purchase_val = 0.0
            tot_sales_val = 0.0
            tot_gross_profit = 0.0
            tot_interest_cost = 0.0
            tot_net_profit = 0.0
            tot_days = 0
            tot_qty = 0

            for r in matched_rows:
                q = r["qty"]
                pur_price = r["purchase_price"]
                sale_price = r["sale_price"]
                d = r["days"]
                
                if r["status"] == "sold":
                    gp = (sale_price - pur_price) * q
                else:
                    gp = 0.0
                    
                interest = (pur_price * self.interest_rate * d) / 36500.0 * q
                net = gp - interest
                
                tot_purchase_val += pur_price * q
                tot_sales_val += sale_price * q
                tot_gross_profit += gp
                tot_interest_cost += interest
                tot_net_profit += net
                tot_days += d * q
                tot_qty += q

            avg_days = tot_days / tot_qty if tot_qty > 0 else 0.0
            current_stock = product.stock_qty

            self.kpi_stock.setText(str(current_stock))
            self.kpi_avg_days.setText(f"{avg_days:.1f} Days")
            self.kpi_profit.setText(f"₹{tot_gross_profit:,.2f}")
            self.kpi_interest.setText(f"₹{tot_interest_cost:,.2f}")
            self.kpi_net.setText(f"₹{tot_net_profit:,.2f}")

            # 2. Populate Purchase Lot History Table
            db_purchases = session.query(
                PurchaseMaster.invoice_number,
                PurchaseMaster.date,
                Supplier.name,
                PurchaseItem.qty,
                PurchaseItem.rate
            ).select_from(PurchaseItem).join(PurchaseMaster).join(Supplier).filter(PurchaseItem.product_id == product.id).order_by(PurchaseMaster.date.desc()).all()

            self.purchase_table.setRowCount(len(db_purchases))
            for i, p_info in enumerate(db_purchases):
                pdate_str = p_info.date.strftime("%Y-%m-%d") if isinstance(p_info.date, datetime.date) else str(p_info.date)
                qty_val = p_info.qty
                rate_val = p_info.rate
                total_val = qty_val * rate_val

                self.purchase_table.setItem(i, 0, QTableWidgetItem(p_info.invoice_number))
                self.purchase_table.setItem(i, 1, QTableWidgetItem(pdate_str))
                self.purchase_table.setItem(i, 2, QTableWidgetItem(p_info.name))
                self.purchase_table.setItem(i, 3, QTableWidgetItem(str(qty_val)))
                self.purchase_table.setItem(i, 4, QTableWidgetItem(f"{rate_val:,.2f}"))
                self.purchase_table.setItem(i, 5, QTableWidgetItem(f"{total_val:,.2f}"))

            # 3. Populate Sales History Table
            db_sales = session.query(
                SalesMaster.invoice_number,
                SalesMaster.date,
                Customer.name,
                SalesItem.qty,
                SalesItem.rate,
                SalesItem.discount
            ).select_from(SalesItem).join(SalesMaster).join(Customer).filter(SalesItem.product_id == product.id).order_by(SalesMaster.date.desc()).all()

            self.sales_table.setRowCount(len(db_sales))
            for i, s_info in enumerate(db_sales):
                sdate_str = s_info.date.strftime("%Y-%m-%d") if isinstance(s_info.date, datetime.date) else str(s_info.date)
                qty_val = s_info.qty
                rate_val = s_info.rate
                discount_val = s_info.discount
                total_val = (qty_val * rate_val) - discount_val

                self.sales_table.setItem(i, 0, QTableWidgetItem(s_info.invoice_number))
                self.sales_table.setItem(i, 1, QTableWidgetItem(sdate_str))
                self.sales_table.setItem(i, 2, QTableWidgetItem(s_info.name))
                self.sales_table.setItem(i, 3, QTableWidgetItem(str(qty_val)))
                self.sales_table.setItem(i, 4, QTableWidgetItem(f"{rate_val:,.2f}"))
                self.sales_table.setItem(i, 5, QTableWidgetItem(f"{discount_val:,.2f}"))
                self.sales_table.setItem(i, 6, QTableWidgetItem(f"{total_val:,.2f}"))

        except Exception as e:
            print(f"Error loading drill-down data: {e}")
            traceback.print_exc()
        finally:
            session.close()

